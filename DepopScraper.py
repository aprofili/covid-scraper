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

class Entry:
    
    def __init__(self, href = "", tablerow = ""):
        self.href = href
        self.size = "N/A"
        self.price = 0
        self.shipping = 0
        self.pictures = []
        self.description = "Description not found"
        self.category = "Category not found"
        self.dateUpdated = "Date not found"

        if tablerow == "":
            markAsSeen = 1

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

            if 'props' in jsondict and 'initialReduxState' in jsondict['props'] and 'product' in jsondict['props']['initialReduxState'] and 'product' in jsondict['props']['initialReduxState']['product']:
                jsondict = jsondict['props']['initialReduxState']['product']['product']
            else:
                print("Unknown json format for href " + href)
                print("json script is as follows")
                pprint(jsondict)
                return

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
                if jsondict['categoryId'] in Entry.categoryDict.keys():
                    self.category = Entry.categoryDict[jsondict['categoryId']]
                else:
                    self.category = "Not in Dict: " + str(jsondict['categoryId'])
                    print(self.category)
                    print(self.href)
                    print("\n\n\n\n")
                    markAsSeen = 0
            elif 'categories' in jsondict:
                if jsondict['categories'][0] in Entry.categoryDict.keys():
                    self.category = Entry.categoryDict[jsondict['categories'][0]]
                else:
                    self.category = "Not in Dict: " + str(jsondict['categories'][0])
                    print(self.category)
                    print(self.href)
                    print("\n\n\n\n")
            if self.category == "Category not found":
                markAsSeen = 0

            if 'dateUpdated' in jsondict:
                self.dateUpdated = jsondict['dateUpdated']
            elif 'date_updated' in jsondict:
                self.dateUpdated = jsondict['date_updated']

            if markAsSeen:
                cursor.execute("INSERT INTO seen VALUES (%s);", (self.href))

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

    # def __eq__(self, other):
    #         return isinstance(other, Entry) and self.description == other.description and self.dateUpdated == other.dateUpdated

    def __repr__(self):
        return ('Category: {0}\n Description: {1}\n Size: {2}\n href: {3}\n Price: {4}'.format(self.category, self.description, self.size, self.href, self.price))

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

    def search(self):
        self.searchButton.setText("Parsing search terms...")
        app.processEvents()

        searchTerms = []
        with open("search_terms.txt", "r") as terms:
            for line in terms:
                if line and (line.strip() not in searchTerms):
                    searchTerms.append(line.strip())

        options = webdriver.ChromeOptions()
        options.add_argument('headless')

        driver = webdriver.Chrome("/home/adam/Documents/Projects/Files/chromedriver", options=options)
        hrefs = set()
        numSearchTerms = len(searchTerms)
        currentNum = 0
        for term in searchTerms:
            currentNum += 1
            self.searchButton.setText('Searching for "{0}"... ({1}/{2})'.format(term, currentNum, numSearchTerms))
            app.processEvents()
            try:
                driver.get('https://www.depop.com/search/?q=' + term)
                time.sleep(3)
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

                soup = BeautifulSoup(driver.page_source, "html.parser")
            except Exception as e:
                print(e)

            for a in soup.find_all('a'):
                if a.has_attr('class'):
                    if 'bVpHsn' in a['class']:
                        hrefs.add(a['href'])

        driver.close()

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


        todaysFinds = []
        numNewEntries = len(newEntries)
        for (i, entry) in enumerate(newEntries):
            if numNewEntries >= 10:
                if i % (numNewEntries // 10) == 0:
                    if i / (numNewEntries // 10) * 10 <= 100:
                        self.searchButton.setText("Finding Criteria Matches: {0}%".format(i / (numNewEntries // 10) * 10))
                        app.processEvents()

            success = 0
            if 'T-Shirt' in entry.category:
                if entry.size == "XL" or (entry.price + entry.shipping <= 10 and (entry.size == "XXL" or entry.size == "L")):
                    todaysFinds.append(entry)
                    success = 1
            elif 'Outerwear' in entry.category:
                if entry.size == "XL" or entry.size == "L":
                    todaysFinds.append(entry)
                    success = 1
            elif "Accessory" in entry.category:
                if "flag" in entry.description.lower() or "hat" in entry.description.lower() or "cap" in entry.description.lower() or "snapback" in entry.description.lower():
                    todaysFinds.append(entry)
                    success = 1
            elif 'Music' in entry.category:
                if "vinyl" in entry.description.lower():
                    todaysFinds.append(entry)
                    success = 1
            elif 'Tank' in entry.category:
                if entry.size == "L":
                    todaysFinds.append(entry)
                    success = 1
            if entry.price > 65 or entry.price <= 1:
                success = 0
            if success:
                cursor.execute("INSERT INTO todaysfinds VALUES (%s, %s, %s, %s, %s, %s, %s);", (entry.href, entry.size, entry.price, entry.shipping, entry.description, entry.category, entry.dateUpdated))
                cursor.executemany("INSERT INTO todaysfindspictures VALUES (%s, %s);", [(entry.href, i) for i in entry.pictures])
            # else:
            #     print(entry)
            #     print("\n\n\n\n")


        connection.commit()

        self.searchButton.setText("Today's new finds: {0}. Search again?".format(len(todaysFinds)))
        app.processEvents()

    def viewer(self):
        pageSize = 200
        cursor.execute("SELECT COUNT(*) FROM todaysfinds;")
        todaysFindsCount = cursor.fetchall()[0][0]
        pageCount = todaysFindsCount // pageSize + 1 * (todaysFindsCount % pageSize > 0)
        self.nextWindow = TodaysFinds(pageIndex=0, pageCount=pageCount, pageSize=pageSize, viewerButton=self.viewerButton)
        self.nextWindow.show()
        self.hide()
        self.deleteLater()

    def clear(self):
        cursor.execute("DELETE FROM todaysfindspictures;")
        cursor.execute("DELETE FROM todaysfinds;")
        connection.commit()
        self.message = QMessageBox()
        self.message.setText("Listings successfully marked as seen.")
        self.message.show()

    def filter(self):
        self.nextWindow = FilterCategories()
        self.nextWindow.show()
        self.hide()
        self.deleteLater()

class FilterCategories(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Select Filter Categories")

        self.vbox = QVBoxLayout()

        self.category_list_widget = QListWidget()
        self.category_list_widget.setSelectionMode(QAbstractItemView.MultiSelection)

        clicked_categories = []
        try:
            with open('sizes_categories.txt', 'r') as file:
                for category_id in json.loads(file.read()).keys():
                    clicked_categories.append(int(category_id))
        except:
            error = 1

        categories = []
        sub_categories = []
        with open('categories.txt') as file:
            for line in file:
                if "        " in line:
                    # sub_categories.append(re.search(r"(.*) \d", line.strip()).group(1))
                    continue
                elif "    " in line:
                    temp_list_item = QListWidgetItem()
                    temp_list_item.setText(outer_category + " > " + re.search(r"(.*) \d", line.strip()).group(1))
                    temp_category_ids = []
                    temp_size_ids = ""

                    temp_category_ids.append(int(re.search(r"(\d+)", line.strip()).group(1)))
                    if re.search(r".* \(.*\)", line.strip()) is not None:
                        temp_category_ids += range(int(re.search(r"\((\d+)-(\d+)\)", line.strip()).group(1)),
                                                   int(re.search(r"\((\d+)-(\d+)\)", line.strip()).group(2)) + 1)
                    if re.search(r".* \[.*\]", line.strip()) is not None:
                        for i in re.search(r"\[(.*)\]", line.strip()).group(1).split(','):
                            temp_category_ids.append(int(i))
                    if re.search(r".* \{.*\}", line.strip()) is not None:
                        temp_size_ids = re.search(r"\{(.*)\}", line.strip()).group(1)

                    clicked = 0
                    for category_id in temp_category_ids:
                        if category_id in clicked_categories:
                            clicked = 1

                    temp_list_item.setData(1, temp_category_ids)
                    temp_list_item.setData(3, temp_size_ids)
                    self.category_list_widget.addItem(temp_list_item)
                    if clicked:
                        temp_list_item.setSelected(True)
                else:
                    # categories.append(line.strip() + "--")
                    outer_category = line.strip()
        self.category_list_widget.addItems(categories)

        self.nextButton = QPushButton("Next")
        self.nextButton.clicked.connect(self.next)

        self.vbox.addWidget(self.category_list_widget)
        self.vbox.addWidget(self.nextButton)
        self.setLayout(self.vbox)


    def next(self):
        self.nextWindow = FilterSizes(self.category_list_widget.selectedItems())
        self.nextWindow.show()
        self.hide()

class FilterSizes(QWidget):
    def __init__(self, selected_items):
        super().__init__()

        self.selected_items = selected_items

        self.setWindowTitle("Select Filter Categories")

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

        try:
            with open('sizes_categories.txt', 'r') as file:
                self.filter_dict = json.loads(file.read())
        except:
            self.filter_dict = {}

        self.vbox = QVBoxLayout()

        self.hbox_list = []

        for i in selected_items:
            if i.data(3):
                temp_sizes = []
                row_hbox = QHBoxLayout()
                row_hbox.addWidget(FilterSizesEntry(i))
                row_list_widget = QListWidget()
                row_list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
                for j in i.data(3):
                    temp_sizes += size_dict[int(j)]
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

    def next(self):
        self.nextWindow = FilterPriceKeyword(self.selected_items, self.hbox_list)
        self.nextWindow.show()
        self.hide()

class FilterSizesEntry(QLabel):
    def __init__(self, list_widget_item):
        super().__init__(list_widget_item.text())
        self.category_ids = list_widget_item.data(1)
        self.sizes = list_widget_item.data(3)

class FilterPriceKeyword(QWidget):
    def __init__(self, selected_items, hbox_list):
        super().__init__()

        self.selected_items = selected_items
        self.hbox_list = hbox_list

        self.setWindowTitle("Select Filter Categories")

        self.vbox = QVBoxLayout()

        self.grid = QGridLayout()

        row_index = 0
        for hbox in self.hbox_list:
            for size in hbox.itemAt(1).widget().selectedItems():
                self.grid.addWidget(hbox.itemAt(0).widget(), row_index, 0)
                self.grid.addWidget(QLabel(size.text()), row_index, 1)
                temp_start_price = QLineEdit()
                temp_end_price = QLineEdit()
                temp_keyword = QLineEdit()
                self.grid.addWidget(temp_start_price, row_index, 2)
                self.grid.addWidget(temp_end_price, row_index, 3)
                self.grid.addWidget(temp_keyword, row_index, 4)
                row_index += 1

        self.nextButton = QPushButton("Next")
        self.nextButton.clicked.connect(self.next)

        self.scroll_area = QScrollArea()
        self.scroll_area.setLayout(self.grid)
        self.vbox.addWidget(self.scroll_area)
        self.vbox.addWidget(self.nextButton)
        self.setLayout(self.vbox)

    def next(self):
        filter_dict = {}
        for hbox in self.hbox_list:
            for category_id in hbox.itemAt(0).widget().category_ids:
                filter_dict[category_id] = {}
                for size in hbox.itemAt(1).widget().selectedItems():
                    filter_dict[category_id][size.text()] = (0, -1, [])
        for item in self.selected_items:
            if not item.data(3):
                for category_id in item.data(1):
                    filter_dict[category_id] = {'N/A': (0, -1, [])}
        with open('sizes_categories.txt', 'w') as file:
            print(json.dumps(filter_dict), file=file)
        self.nextWindow = FilterSearchTerms()
        self.nextWindow.show()
        self.hide()
        self.deleteLater()

class FilterSearchTerms(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Select Filter Search Terms")

        self.vbox = QVBoxLayout()
        self.text_edit = QPlainTextEdit()

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

    def next(self):
        with open('search_terms.txt', 'w') as file:
            print(self.text_edit.toPlainText(), end='', file=file)
        self.nextWindow = Home()
        self.nextWindow.show()
        self.hide()
        self.deleteLater()

class TodaysFinds(QWidget):
    def __init__(self, pageIndex, pageCount, pageSize, viewerButton):
        super().__init__()

        self.viewerButton = viewerButton

        self.viewerButton.setText("Grabbing listings...")
        app.processEvents()



        self.setWindowTitle("Today's Finds")
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        self.hbox = QHBoxLayout()
        self.pageIndex = pageIndex
        self.pageCount = pageCount
        self.pageSize = pageSize
        self.nextPageButton = QPushButton("Next Page")
        if self.pageIndex >= pageCount - 1:
            self.nextPageButton.setDisabled(True)
        self.prevPageButton = QPushButton("Previous Page")
        if self.pageIndex < 1:
            self.prevPageButton.setDisabled(True)
        self.homeButton = QPushButton("Back to Home")

        self.grid = QGridLayout()

        todaysFinds = []
        cursor.execute("SELECT * FROM todaysfinds LIMIT %s OFFSET %s;", (self.pageSize, self.pageSize * self.pageIndex))
        for row in cursor.fetchall():
            todaysFinds.append(Entry(tablerow=row))

        index = 0
        numTodaysFinds = len(todaysFinds)
        for (i, entry) in enumerate(todaysFinds):
            if numTodaysFinds >= 10:
                if i % (numTodaysFinds // 10) == 0:
                    if i / (numTodaysFinds // 10) * 10 <= 100:
                        self.viewerButton.setText("Creating Visual Grid Entries: {0}%".format(i / (numTodaysFinds // 10) * 10))
                        app.processEvents()
            self.grid.addWidget(GridEntry(entry), index / 4, index % 4)
            index += 1

        self.nextPageButton.clicked.connect(self.nextpage)
        self.prevPageButton.clicked.connect(self.prevpage)
        self.homeButton.clicked.connect(self.backhome)




        # finalizing layout with header and scroll area around the grid
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

    def nextpage(self):
        self.pageIndex += 1
        self.nextWindow = TodaysFinds(self.pageIndex, self.pageCount, self.pageSize, self.nextPageButton)
        self.nextWindow.show()
        self.hide()
        self.deleteLater()

    def prevpage(self):
        self.pageIndex -= 1
        self.nextWindow = TodaysFinds(self.pageIndex, self.pageCount, self.pageSize, self.prevPageButton)
        self.nextWindow.show()
        self.hide()
        self.deleteLater()

    def backhome(self):
        self.nextWindow = Home()
        self.nextWindow.show()
        self.hide()
        self.deleteLater()



class GridEntry(QWidget):
    def __init__(self, entry):
        super().__init__()
        # print("setting grid entry variables")
        vbox = QVBoxLayout()
        self.picLabel = QLabel('picture')
        self.picLabel.setMinimumSize(200, 200)
        self.picIndex = 0
        self.entry = entry
        # print("about to try loading picture")
        try:
            # print("trying to load picture")
            picData = urllib.request.urlopen(entry.pictures[0], timeout=15).read()
            self.picLabel.setMaximumSize(200, 200)
            self.picLabel.setScaledContents(True)
            picPixmap = QPixmap()
            picPixmap.loadFromData(picData)
            self.picLabel.setPixmap(picPixmap)
            # print("successfully loaded picture")
        except Exception as e:
            print(e)

        button = QPushButton("Next Picture")
        button.clicked.connect(self.nextpic)

        # print("finishing grid entry")

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

    app = QApplication(sys.argv)

    window = Home()
    window.show()

    sys.exit(app.exec_())


