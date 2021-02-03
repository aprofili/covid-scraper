import requests
from bs4 import BeautifulSoup
import json
from pprint import pprint
from selenium import webdriver
import time
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from functools import partial
import urllib.request
import pymysql
import re
import sys
import os
import subprocess
import traceback
from Queue import Queue
from threading import Thread

def loadviewer(pageIndex, pageCount, pageSize, first=False):
    if first:
        pageSize = 50
        cursor.execute("SELECT COUNT(*) FROM todaysfinds;")
        todaysFindsCount = cursor.fetchall()[0][0]
        pageCount = todaysFindsCount // pageSize + 1 * (todaysFindsCount % pageSize > 0)
        return TodaysFinds(pageIndex=0, pageCount=pageCount, pageSize=pageSize)
    else:
        TodaysFinds(pageIndex + 1, pageCount, pageSize)

# holds the information of a single listing, including pictures, price, etc.
class Entry:
    # takes in an href if creating, or a tablerow if recovering
    def __init__(self, href = "", tablerow = ""):
        # setting default data
        self.href = href
        self.size = "N/A"
        self.price = 0
        self.shipping = 0
        self.pictures = []
        self.description = "Description not found"
        self.category = "Category not found"
        self.dateUpdated = "Date not found"

        # if creating, do these
        if tablerow == "":
            markAsSeen = 1

            # gets html code if possible
            try:
                response = requests.get('https://www.depop.com' + href, timeout=15)
                if response.ok:
                    html = response.text
                    soup = BeautifulSoup(html, "html.parser")
                else:
                    print("Error 404 for href " + href)
                    return
            except Exception as e:
                print(e)

            # finds json representation of the listing if available
            success = 0
            for i in soup.find_all('script'):
                if i.has_attr('id') and i['id'] == "__NEXT_DATA__":
                    jsondict = i
                    jsondict = str(jsondict).split('>')[1].split('<')[0]
                    jsondict = json.loads(jsondict)
                    success = 1
                    break
            if not success:
                print("Couldn't find json script for href " + href)
                return

            # from takes json into useable form
            if 'props' in jsondict and 'initialReduxState' in jsondict['props'] and 'product' in jsondict['props']['initialReduxState'] and 'product' in jsondict['props']['initialReduxState']['product']:
                jsondict = jsondict['props']['initialReduxState']['product']['product']
            else:
                print("Unknown json format for href " + href)
                print("json script is as follows")
                pprint(jsondict)
                return

            # from json dictionary, retrieves important info
            if 'sizes' in jsondict and 'name' in jsondict['sizes'][0]:
                self.size = jsondict['sizes'][0]['name']

            if 'price' in jsondict:
                if 'discountedPriceAmount' in jsondict['price'] and jsondict['price']['discountedPriceAmount'] != None:
                    self.price = float(jsondict['price']['discountedPriceAmount'])
                elif 'discounted_price_amount' in jsondict['price'] and jsondict['price']['discounted_price_amount'] != None:
                    self.price = float(jsondict['price']['discounted_price_amount'])
                elif 'priceAmount' in jsondict['price'] and jsondict['price']['priceAmount'] != None:
                    self.price = float(jsondict['price']['priceAmount'])
                elif 'price_amount' in jsondict['price'] and jsondict['price']['price_amount'] != None:
                    self.price = float(jsondict['price']['price_amount'])

            if 'price' in jsondict:
                if 'nationalShippingCost' in jsondict['price'] and jsondict['price']['nationalShippingCost'] != None:
                    self.shipping = float(jsondict['price']['nationalShippingCost'])
                elif 'national_shipping_cost' in jsondict['price'] and jsondict['price']['national_shipping_cost'] != None:
                    self.shipping = float(jsondict['price']['national_shipping_cost'])

            if 'pictures' in jsondict:
                for i in jsondict['pictures']:
                    if len(i) >= 4:
                        self.pictures.append(i[5]['url'])
                    elif len(i) >= 1:
                        self.pictures.append(i[0]['url'])

            if 'description' in jsondict:
                self.description = (jsondict['description'] + "                                                  ")[:50]

            if 'categoryId' in jsondict:
                self.category = int(jsondict['categoryId'])
            elif 'categories' in jsondict:
                    self.category = int(jsondict['categories'][0])
            if self.category == "Category not found":
                markAsSeen = 0

            if 'dateUpdated' in jsondict:
                self.dateUpdated = jsondict['dateUpdated']
            elif 'date_updated' in jsondict:
                self.dateUpdated = jsondict['date_updated']

            # if no important errors, mark the listing as seen in SQL database
            if markAsSeen:
                cursor.execute("INSERT INTO seen VALUES (%s);", (self.href))

        # recovers listing from SQL stored data
        elif tablerow != "":
            self.href = tablerow[0]
            self.size = tablerow[1]
            self.price = float(tablerow[2])
            self.shipping = float(tablerow[3])
            self.description = tablerow[4]
            self.category = tablerow[5]
            self.dateUpdated = tablerow[6]
            self.pictures = []
            cursor.execute("SELECT picture FROM todaysfindspictures WHERE href LIKE %s;", self.href)
            for row in cursor.fetchall():
                self.pictures.append(row[0])

    # to print the entry for debugging
    def __repr__(self):
        return ('Category: {0}\n Description: {1}\n Size: {2}\n href: {3}\n Price: {4}'.format(self.category, self.description, self.size, self.href, self.price))

# home page with main functions/page links
class Home(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Depop Scraper")
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        self.viewerButton = QPushButton("View Listings")
        self.searchButton = QPushButton("Search Depop")
        self.filterButton = QPushButton("Filter Listings")
        self.clearButton = QPushButton("Mark Listings as Seen")

        self.grid = QGridLayout()

        self.viewerButton.clicked.connect(self.viewer)
        self.searchButton.clicked.connect(self.search)
        self.filterButton.clicked.connect(self.filter)
        self.clearButton.clicked.connect(self.clear)

        self.header = QLabel("Depop Scraper")
        self.header.setFont(QFont('Arial', 25))
        self.header.setAlignment(Qt.AlignCenter)
        self.vbox.addWidget(self.header)
        self.vbox.addLayout(self.grid)
        self.grid.addWidget(self.searchButton, 0, 0)
        self.grid.addWidget(self.viewerButton, 0, 1)
        self.grid.addWidget(self.filterButton, 1, 0)
        self.grid.addWidget(self.clearButton, 1, 1)
        self.setMinimumSize(600, 200)


        self.thread_pool = QThreadPool()
        worker = Worker(loadviewer, 0, 0, 0, first=True)
        worker.signals.progress.connect(self.catchloadprogress)
        worker.signals.result.connect(self.catchload)
        self.thread_pool.start(worker)

    # uses stored search terms and criteria to find unseen listings
    def search(self):
        self.searchButton.setText("Parsing search terms...")
        app.processEvents()

        # retrieves search terms
        searchTerms = []
        with open("search_terms.txt", "r") as terms:
            for line in terms:
                if line and (line.strip() not in searchTerms):
                    searchTerms.append(line.strip())

        # opens web driver
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        driver = webdriver.Chrome("/home/adam/Documents/Projects/Files/chromedriver", options=options)
        hrefs = set()
        numSearchTerms = len(searchTerms)
        currentNum = 0

        # searches each search term
        for term in searchTerms:
            currentNum += 1
            self.searchButton.setText('Searching for "{0}"... ({1}/{2})'.format(term, currentNum, numSearchTerms))
            app.processEvents()
            try:
                driver.get('https://www.depop.com/search/?q=' + term)
                time.sleep(3)

                # scrolls all the way to the bottom of the page, loading every listing
                scroll = 0
                count = 0
                while count < 100:
                    driver.execute_script('scroll(0, 1000000);')
                    newScroll = driver.execute_script('return document.body.scrollHeight;')
                    if newScroll == scroll:
                        count += 1
                    else:
                        count = 0
                    scroll = newScroll
                    time.sleep(0.01)

                # exports html
                soup = BeautifulSoup(driver.page_source, "html.parser")
            except Exception as e:
                print(e)

            # finds each href (url chunk) from the loaded listings
            for a in soup.find_all('a'):
                if a.has_attr('class'):
                    if 'bVpHsn' in a['class']:
                        hrefs.add(a['href'])

        driver.close()

        # passes each href into an Entry object then adds it to a list
        newEntries = []
        numHrefs = len(hrefs)
        for (i, href) in enumerate(hrefs):
            if numHrefs >= 10:
                if i % (numHrefs // 10) == 0:
                    if i / (numHrefs // 10) * 10 <= 100:
                        self.searchButton.setText("Creating Entries: {0}%".format(i / (numHrefs // 10) * 10))
                        app.processEvents()
            cursor.execute("SELECT COUNT(*) FROM seen WHERE href LIKE %s;", href)
            if not int(cursor.fetchall()[0][0]):
                # firstTime = time.process_time()
                newEntries.append(Entry(href=href))
                # secondTime = time.process_time()
                # if (firstTime - secondTime) < 0.02:
                #     time.sleep(0.02 - (firstTime - secondTime))

        # loads filter json made on the filter screens
        with open('sizes_categories.txt', 'r') as file:
            filter_dict = json.loads(file.read())

        # iterates through the listings for filter criteria matches
        todaysFinds = []
        numNewEntries = len(newEntries)
        for (i, entry) in enumerate(newEntries):
            if numNewEntries >= 10:
                if i % (numNewEntries // 10) == 0:
                    if i / (numNewEntries // 10) * 10 <= 100:
                        self.searchButton.setText("Finding Criteria Matches: {0}%".format(i / (numNewEntries // 10) * 10))
                        app.processEvents()

            success = 0
            if str(entry.category) in filter_dict:
                if entry.size in filter_dict[str(entry.category)]:
                    success2 = 0
                    for term in filter_dict[str(entry.category)][entry.size][2]:
                        if term in entry.description:
                            success2 = 1
                    if success2 or len(filter_dict[str(entry.category)][entry.size][2]) == 0:
                        if not filter_dict[str(entry.category)][entry.size][0] or (entry.price + entry.shipping) >= int(filter_dict[str(entry.category)][entry.size][0]):
                            if not filter_dict[str(entry.category)][entry.size][1] or (entry.price + entry.shipping) <= int(filter_dict[str(entry.category)][entry.size][1]):
                                todaysFinds.append(entry)
                                success = 1

            # if matches criteria, listing temporarily goes to an SQL database for viewing
            if success:
                cursor.execute("INSERT INTO todaysfinds VALUES (%s, %s, %s, %s, %s, %s, %s);", (entry.href, entry.size, entry.price, entry.shipping, entry.description, entry.category, entry.dateUpdated))
                cursor.executemany("INSERT INTO todaysfindspictures VALUES (%s, %s);", [(entry.href, i) for i in entry.pictures])

        connection.commit()

        self.searchButton.setText("Today's new finds: {0}. Search again?".format(len(todaysFinds)))
        app.processEvents()

    # views matched listings that haven't been cleared yet
    def viewer(self):
        self.nextWindow.show()
        # QThreadPool.globalInstance().start(LoadNextPage(self.nextWindow))
        # self.nextWindow.loadnext()
        self.hide()
        # self.deleteLater()

        self.nextWindow.thread_pool = QThreadPool()
        worker = Worker(loadviewer, self.nextWindow.pageIndex, self.nextWindow.pageCount, self.nextWindow.pageSize)
        worker.signals.progress.connect(self.nextWindow.catchloadprogress)
        worker.signals.result.connect(self.nextWindow.catchload)
        self.nextWindow.thread_pool.start(worker)

    # clears listings that have already been looked through
    def clear(self):
        cursor.execute("DELETE FROM todaysfindspictures;")
        cursor.execute("DELETE FROM todaysfinds;")
        connection.commit()
        self.message = QMessageBox()
        self.message.setText("Listings successfully marked as seen.")
        self.message.show()

    # changes the filter settings
    def filter(self):
        self.nextWindow = FilterCategories()
        self.nextWindow.show()
        self.hide()
        self.deleteLater()

    def catchload(self, s):
        self.nextWindow = s
        # background_thread_pool.releaseThread()

    def catchloadprogress(self, s):
        if not s:
            self.viewerButton.setText("Loading...")
        elif s:
            self.viewerButton.setText("View Listings")

# page to set which categories to filter for
class FilterCategories(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Select Filter Categories")

        self.vbox = QVBoxLayout()

        self.category_list_widget = QListWidget()
        self.category_list_widget.setSelectionMode(QAbstractItemView.MultiSelection)

        # retrieves the category ids that are currently in the filter
        clicked_categories = []
        try:
            with open('sizes_categories.txt', 'r') as file:
                for category_id in json.loads(file.read()).keys():
                    clicked_categories.append(int(category_id))
        except:
            error = 1

        # parses the current category list file, creating widget list items for each
        categories = []
        # note: code for sub_categories is half-there, but not quite finished
        sub_categories = []
        with open('categories.txt') as file:
            for line in file:
                # for subcategories
                if "        " in line:
                    # sub_categories.append(re.search(r"(.*) \d", line.strip()).group(1))
                    continue

                # for categories
                elif "    " in line:
                    # creates a list item to choose from
                    temp_list_item = QListWidgetItem()
                    temp_list_item.setText(outer_category + " > " + re.search(r"(.*) \d", line.strip()).group(1))
                    temp_category_ids = []
                    temp_size_ids = ""

                    # retrieves the category ids that fall under that list item to hold within the listing
                    temp_category_ids.append(int(re.search(r"(\d+)", line.strip()).group(1)))
                    if re.search(r".* \(.*\)", line.strip()) is not None:
                        temp_category_ids += range(int(re.search(r"\((\d+)-(\d+)\)", line.strip()).group(1)),
                                                   int(re.search(r"\((\d+)-(\d+)\)", line.strip()).group(2)) + 1)
                    if re.search(r".* \[.*\]", line.strip()) is not None:
                        for i in re.search(r"\[(.*)\]", line.strip()).group(1).split(','):
                            temp_category_ids.append(int(i))
                    if re.search(r".* \{.*\}", line.strip()) is not None:
                        temp_size_ids = re.search(r"\{(.*)\}", line.strip()).group(1)

                    # attaches the category ids and size list identifiers to the listing, then adds it to the widget
                    temp_list_item.setData(1, temp_category_ids)
                    temp_list_item.setData(3, temp_size_ids)
                    self.category_list_widget.addItem(temp_list_item)

                    # if any of the ids within the category were previously filtered, they are automatically clicked
                    for category_id in temp_category_ids:
                        if category_id in clicked_categories:
                            temp_list_item.setSelected(True)

                # for supercategories (menswear/womenswear)
                else:
                    # categories.append(line.strip() + "--")
                    outer_category = line.strip()
        self.category_list_widget.addItems(categories)

        self.nextButton = QPushButton("Next")
        self.nextButton.clicked.connect(self.next)

        self.vbox.addWidget(self.category_list_widget)
        self.vbox.addWidget(self.nextButton)
        self.setLayout(self.vbox)

    # goes to the next page to filter sizes for each of the chosen categories
    def next(self):
        self.nextWindow = FilterSizes(self.category_list_widget.selectedItems())
        self.nextWindow.show()
        self.hide()

# page to set what sizes to filter for, split by each category
class FilterSizes(QWidget):
    def __init__(self, selected_items):
        super().__init__()

        self.selected_items = selected_items

        self.setWindowTitle("Select Filter Categories")

        # lists to encompass all of depop's horrible mess of a sizing system, to be later applied only on items that can have that size
        sizes1 = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'XXXXL']
        sizes2 = ['Other', 'One size']
        sizes3 = [str(i) + '"' for i in list(range(26, 43)) + [44, 46]]
        sizes4 = ['US ' + str(round(7 + 0.5 * i, 2)) for i in range(17)]
        sizes5 = ['00'] + [str(i) for i in list(range(13)) + list(range(14, 32, 2))]
        sizes6 = ['US ' + str(round(5 + 0.5 * i, 2)) for i in range(19)]
        sizes7 = [str(i) for i in list(range(13)) + list(range(14, 26, 2))]
        sizes8 = [str(i) + '"' for i in list(range(23, 41)) + list(range(42, 52, 2))]
        sizes9 = [str(i) for i in list(range(13)) + list(range(14, 34, 2))]
        sizes0 = [str(i) for i in range(13)] + ['28D'] + [str(i) + str(j) for i in range(32, 36, 2) for j in ['A', 'B', 'C', 'D', 'DD', 'E']] + [str(i) + str(j) for i in range(36, 40, 2) for j in ['A', 'B', 'C', 'D', 'DD', 'E', 'F', 'G']] + [i + ' cup' for i in ['A', 'B', 'C', 'D', 'DD']]
        size_dict = {1: sizes1, 2: sizes2, 3: sizes3, 4: sizes4, 5: sizes5, 6: sizes6, 7: sizes7, 8: sizes8, 9: sizes9, 0: sizes0}

        # if a previous filter has been used, loads it in
        try:
            with open('sizes_categories.txt', 'r') as file:
                self.filter_dict = json.loads(file.read())
        except:
            self.filter_dict = {}

        self.vbox = QVBoxLayout()

        self.hbox_list = []

        # iterates through the categories selected on the last screen
        for i in selected_items:
            # steps if there are size options for this category
            if i.data(3):
                # creates a row with applicable information
                temp_sizes = []
                row_hbox = QHBoxLayout()
                row_hbox.addWidget(FilterSizesEntry(i))
                row_list_widget = QListWidget()
                row_list_widget.setSelectionMode(QAbstractItemView.MultiSelection)

                # converts the size identifiers to a list of sizes for the category
                for j in i.data(3):
                    temp_sizes += size_dict[int(j)]
                # creates a list widget for each possible size, clicks the ones from the previous filter
                for j in temp_sizes:
                    temp_list_widget_item = QListWidgetItem(j)
                    row_list_widget.addItem(temp_list_widget_item)
                    for k in i.data(1):
                        if str(k) in self.filter_dict:
                            if j in self.filter_dict[str(k)]:
                                temp_list_widget_item.setSelected(True)

                row_hbox.addWidget(row_list_widget)
                self.vbox.addLayout(row_hbox)
                self.hbox_list.append(row_hbox)

        self.nextButton = QPushButton("Next")
        self.nextButton.clicked.connect(self.next)

        self.vbox.addWidget(self.nextButton)
        self.setLayout(self.vbox)

    # moves on to the next screen to set price ranges and keywords
    def next(self):
        self.nextWindow = FilterPriceKeyword(self.selected_items, self.hbox_list)
        self.nextWindow.show()
        self.hide()

# a QLabel with additional data fields to hold a category's ids and size identifiers
class FilterSizesEntry(QLabel):
    def __init__(self, input):
        # if instantiated from a QList Widget
        if isinstance(input, QListWidgetItem):
            super().__init__(input.text())
            self.category_ids = input.data(1)
            self.sizes = input.data(3)
        # if cloning another existing FilterSizesEntry
        elif isinstance(input, FilterSizesEntry):
            super().__init__(input.text())
            self.category_ids = input.category_ids
            self.sizes = input.sizes

# page to set price ranges and required keywords for each chosen size of each chosen category
class FilterPriceKeyword(QWidget):
    def __init__(self, selected_items, hbox_list):
        super().__init__()

        self.selected_items = selected_items
        self.hbox_list = hbox_list

        self.setWindowTitle("Select Filter Categories")

        self.vbox = QVBoxLayout()

        # creates the grid and header
        self.grid = QGridLayout()
        self.grid.addWidget(QLabel("Category"), 0, 0)
        self.grid.addWidget(QLabel("Size"), 0, 1)
        self.grid.addWidget(QLabel("Minimum Price"), 0, 2)
        self.grid.addWidget(QLabel("Maximum Price"), 0, 3)
        self.grid.addWidget(QLabel("Search Terms"), 0, 4)

        # yet again loads the last saved filter
        try:
            with open('sizes_categories.txt', 'r') as file:
                filter_dict = json.loads(file.read())
        except:
            filter_dict = {}

        # for each category and size, creates a row in the grid with relevant line edits
        row_index = 1
        # iterates through each row of the size screen
        for hbox in self.hbox_list:
            # iterates through each selected size for that given row
            for size in hbox.itemAt(1).widget().selectedItems():
                self.grid.addWidget(FilterSizesEntry(hbox.itemAt(0).widget()), row_index, 0)
                self.grid.addWidget(QLabel(size.text()), row_index, 1)
                temp_start_price = QLineEdit()
                temp_end_price = QLineEdit()
                temp_keyword = QLineEdit()
                self.grid.addWidget(temp_start_price, row_index, 2)
                self.grid.addWidget(temp_end_price, row_index, 3)
                self.grid.addWidget(temp_keyword, row_index, 4)

                # fills line edits with values from last saved filter
                for category_id in self.grid.itemAtPosition(row_index, 0).widget().category_ids:
                    if str(category_id) in filter_dict:
                        if size.text() in filter_dict[str(category_id)]:
                            temp_start_price.setText(filter_dict[str(category_id)][size.text()][0])
                            temp_end_price.setText(filter_dict[str(category_id)][size.text()][1])
                            temp_keyword.setText(filter_dict[str(category_id)][size.text()][2])
                row_index += 1
        # for items without size options that weren't previously included, creates similar rows
        for item in selected_items:
            if not item.data(3):
                self.grid.addWidget(FilterSizesEntry(item), row_index, 0)
                self.grid.addWidget(QLabel('N/A'), row_index, 1)
                temp_start_price = QLineEdit()
                temp_end_price = QLineEdit()
                temp_keyword = QLineEdit()
                self.grid.addWidget(temp_start_price, row_index, 2)
                self.grid.addWidget(temp_end_price, row_index, 3)
                self.grid.addWidget(temp_keyword, row_index, 4)
                for category_id in item.data(1):
                    if str(category_id) in filter_dict:
                        if 'N/A' in filter_dict[str(category_id)]:
                            temp_start_price.setText(filter_dict[str(category_id)]['N/A'][0])
                            temp_end_price.setText(filter_dict[str(category_id)]['N/A'][1])
                            temp_keyword.setText(filter_dict[str(category_id)]['N/A'][2])
                row_index += 1

        self.nextButton = QPushButton("Next")
        self.nextButton.clicked.connect(self.next)

        self.grid_widget = QWidget()
        self.grid_widget.setLayout(self.grid)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.grid_widget)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setMinimumWidth(self.grid_widget.width() + 16)
        self.vbox.addWidget(self.scroll_area)
        self.vbox.addWidget(self.nextButton)
        self.setLayout(self.vbox)

    # creates and saves a json representation of the filter, then moves to the next screen for search terms
    def next(self):
        # creates dictionary in format {category: {size: (min_price, max_price, search_terms) } }
        filter_dict = {}
        for row_index in range(1, self.grid.rowCount()):
            temp_category_ids = self.grid.itemAtPosition(row_index, 0).widget().category_ids
            temp_size = self.grid.itemAtPosition(row_index, 1).widget().text()
            temp_min_price = self.grid.itemAtPosition(row_index, 2).widget().text()
            temp_max_price = self.grid.itemAtPosition(row_index, 3).widget().text()
            temp_keywords = self.grid.itemAtPosition(row_index, 4).widget().text()
            for category_id in temp_category_ids:
                if category_id not in filter_dict:
                    filter_dict[int(category_id)] = {}
                filter_dict[int(category_id)][temp_size] = (temp_min_price, temp_max_price, temp_keywords)
        # writes it to a file in json
        with open('sizes_categories.txt', 'w') as file:
            print(json.dumps(filter_dict), file=file)
        self.nextWindow = FilterSearchTerms()
        self.nextWindow.show()
        self.hide()
        self.deleteLater()

# page to set the search terms to look through
class FilterSearchTerms(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Select Filter Search Terms")

        self.vbox = QVBoxLayout()
        self.text_edit = QPlainTextEdit()

        # opens search terms from most recent filter, puts them into the box if found
        try:
            with open('search_terms.txt', 'r') as file:
                self.text_edit.setPlainText(file.read())
        except:
            error = 1

        self.nextButton = QPushButton("Finish")
        self.nextButton.clicked.connect(self.next)

        self.vbox.addWidget(self.nextButton)
        self.vbox.addWidget(self.text_edit)
        self.setLayout(self.vbox)

    # saves the search terms and returns home
    def next(self):
        with open('search_terms.txt', 'w') as file:
            print(self.text_edit.toPlainText(), end='', file=file)
        self.nextWindow = Home()
        self.nextWindow.show()
        self.hide()
        self.deleteLater()

# page to view unseen listings that matched search criteria
class TodaysFinds(QWidget):
    def __init__(self, pageIndex, pageCount, pageSize):
        super().__init__()

        # self.viewerButton = viewerButton

        # writes progress updates on the button that linked to this page
        # self.viewerButton.setText("Grabbing listings...")
        # app.processEvents()



        self.setWindowTitle("Today's Finds")
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        self.hbox = QHBoxLayout()
        self.pageIndex = pageIndex
        self.pageCount = pageCount
        self.pageSize = pageSize
        self.nextPageButton = QPushButton("Next Page")

        # ensures you can't click the button for an adjacent page that doesn't exist
        if self.pageIndex >= pageCount - 1:
            self.nextPageButton.setDisabled(True)
        self.prevPageButton = QPushButton("Previous Page")
        if self.pageIndex < 1:
            self.prevPageButton.setDisabled(True)
        self.homeButton = QPushButton("Back to Home")

        self.grid = QGridLayout()

        # gets the SQL-stored listing information and restores the Entry objects
        todaysFinds = []
        cursor.execute("SELECT * FROM todaysfinds LIMIT %s OFFSET %s;", (self.pageSize, self.pageSize * self.pageIndex))
        for row in cursor.fetchall():
            todaysFinds.append(Entry(tablerow=row))

        # creates a GridEntry object using the information from each entry
        index = 0
        numTodaysFinds = len(todaysFinds)
        for (i, entry) in enumerate(todaysFinds):
            if numTodaysFinds >= 10:
                if i % (numTodaysFinds // 10) == 0:
                    if i / (numTodaysFinds // 10) * 10 <= 100:
                        # self.viewerButton.setText("Creating Visual Grid Entries: {0}%".format(i / (numTodaysFinds // 10) * 10))
                        # app.processEvents()
                        okay = 1
            self.grid.addWidget(GridEntry(entry), index / 4, index % 4)
            index += 1
            # potential future code to save cpu while loading pages in the background
            # if slow_load:
            #     time.sleep(0.2)

        self.nextPageButton.clicked.connect(self.nextpage)
        self.prevPageButton.clicked.connect(self.prevpage)
        self.homeButton.clicked.connect(self.backhome)

        self.header = QLabel("Today's Finds")
        self.header.setFont(QFont('Arial', 25))
        self.header.setAlignment(Qt.AlignCenter)
        self.vbox.addWidget(self.header)
        self.scrollArea = QScrollArea()
        self.gridWidget = QWidget()
        self.gridWidget.setLayout(self.grid)
        self.scrollArea.setWidget(self.gridWidget)
        self.scrollArea.setWidgetResizable(False)
        self.scrollArea.setMinimumWidth(200 * 4 + 3 * 12 + 16) #self.gridWidget.width() + 16)
        self.scrollArea.setMinimumHeight(700)
        self.vbox.addWidget(self.scrollArea)
        self.hbox.addWidget(self.prevPageButton)
        self.hbox.addWidget(self.nextPageButton)
        self.vbox.addLayout(self.hbox)
        self.vbox.addWidget(self.homeButton)

    # moves to the next page, which should already be loaded, and starts loading the page after that (hopefully)
    def nextpage(self):
        self.pageIndex += 1
        self.nextWindow.show()
        # QThreadPool.globalInstance().start(LoadNextPage(self.nextWindow))
        # background_thread_pool.start(LoadNextPage(self.nextWindow))
        self.hide()
        # self.deleteLater()

        self.nextWindow.thread_pool = QThreadPool()
        worker = Worker(loadviewer, self.nextWindow.pageIndex, self.nextWindow.pageCount, self.nextWindow.pageSize)
        worker.signals.progress.connect(self.nextWindow.catchloadprogress)
        worker.signals.result.connect(self.nextWindow.catchload)
        self.nextWindow.thread_pool.start(worker)

    # loads the previous page and moves to it
    def prevpage(self):
        self.pageIndex -= 1
        self.nextWindow = TodaysFinds(self.pageIndex, self.pageCount, self.pageSize, self.prevPageButton)
        self.nextWindow.show()
        self.hide()
        self.deleteLater()

    # moves back to the homepage
    def backhome(self):
        self.nextWindow = Home()
        self.nextWindow.show()
        self.hide()
        self.deleteLater()

    def catchload(self, s):
        self.nextWindow = s

    def catchloadprogress(self, s):
        if not s:
            self.nextPageButton.setText("Loading...")
        elif s:
            self.nextPageButton.setText("View Listings")

class LoadNextPage(QRunnable):
    def __init__(self, current_page):
        super().__init__()
        self.current_page = current_page

    def run(self):
        self.current_page.loadnext()

class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            self.signals.progress.emit(0)
            result = self.fn(
                *self.args, **self.kwargs
            )
            self.signals.progress.emit(1)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    '''
    finished = pyqtSignal()  # QtCore.Signal
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)



# custom widget to show a listing with its price, description, link, and pictures you can scroll through
class GridEntry(QWidget):
    def __init__(self, entry):
        super().__init__()
        vbox = QVBoxLayout()
        self.picLabel = QLabel('picture')
        self.picLabel.setMinimumSize(200, 200)
        self.picIndex = 0
        self.entry = entry
        # loads first picture
        try:
            picData = urllib.request.urlopen(entry.pictures[0], timeout=15).read()
            self.picLabel.setMaximumSize(200, 200)
            self.picLabel.setScaledContents(True)
            picPixmap = QPixmap()
            picPixmap.loadFromData(picData)
            self.picLabel.setPixmap(picPixmap)
        except Exception as e:
            print(e)

        button = QPushButton("Next Picture")
        button.clicked.connect(self.nextpic)

        # creates hyperlinked url
        descLabel = QLabel('<a href="{0}">{1}</a>'.format('https://www.depop.com' + entry.href, entry.description + "..."))
        descLabel.setTextFormat(Qt.RichText)
        descLabel.setTextInteractionFlags(Qt.TextBrowserInteraction)
        descLabel.setOpenExternalLinks(True)
        descLabel.setWordWrap(True)
        vbox.addWidget(self.picLabel)
        vbox.addWidget(button)
        vbox.addWidget(descLabel)
        # if entry.shipping != None:
        #     if entry.shipping:
        #         vbox.addWidget(QLabel('${0} (${2} Shipped)'.format(round(entry.price, 2), round(entry.shipping, 2), round(entry.price + entry.shipping, 2))))
        #     else:
        #         vbox.addWidget(QLabel('${2}'.format(round(entry.price, 2), round(entry.shipping, 2), round(entry.price + entry.shipping, 2))))
        vbox.addWidget(QLabel('${2}'.format(round(entry.price, 2), round(entry.shipping, 2), round(entry.price + entry.shipping, 2))))
        if entry.size != "N/A":
            vbox.addWidget(QLabel(entry.size))
        self.setLayout(vbox)
        self.setMinimumSize(200, 350)
        self.setMaximumSize(200, 350)

    def nextpic(self):
        if len(self.entry.pictures) > 1:
            self.picIndex += 1
            self.picIndex %= len(self.entry.pictures)
            try:
                picData = urllib.request.urlopen(self.entry.pictures[self.picIndex], timeout=15).read()
                self.picLabel.setMaximumSize(200, 200)
                self.picLabel.setScaledContents(True)
                picPixmap = QPixmap()
                picPixmap.loadFromData(picData)
                self.picLabel.setPixmap(picPixmap)
            except Exception as e:
                print(e)

if __name__ == "__main__":

    connection = pymysql.connect(host = "localhost", user = "root", password = "", db = "depopscraper", charset = "utf8mb4", cursorclass = pymysql.cursors.Cursor)
    cursor = connection.cursor()

    background_thread_pool = QThreadPool()

    app = QApplication(sys.argv)

    window = Home()
    window.show()

    sys.exit(app.exec_())


