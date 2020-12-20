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

class Entry:
    categoryDict = {43 : 'T-Shirt', 47 : 'Outerwear', 18 : 'Accessories', 29:'Music'}
    def __init__(self, href = ""):# , jsonIn = ""):
        # if not jsonIn:
            # pprint(url)
            # initial request
        response = requests.get('https://www.depop.com' + href)
        time.sleep(0.1)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        for script in soup.find_all('script'):
            try:
                if script['id'] == "__NEXT_DATA__":
                    scriptjson = script
                    scriptjson = str(scriptjson).split('>')[1].split('<')[0]
                    scriptdict = json.loads(scriptjson)
                    break
            except:
                continue


        try:
            product = scriptdict['props']['initialReduxState']['product']['product']
            # pprint(product)
            try:
                self.size = product['sizes'][0]['name']['en']
            except:
                self.size = "N/A"
            try:
                self.price = product['price']['discounted_price_amount']
            except:
                self.price = product['price']['price_amount']
            self.shipping = product['price']['national_shipping_cost']
            self.pictures = []
            for i in product['pictures']:
                self.pictures.append(i[5]['url'])
            self.description = product['description']
            self.categories = product['categories']
            if len(self.categories) == 1:
                try:
                    self.category = Entry.categoryDict[self.categories[0]]
                except:
                    self.category = "Not in Dict: " + str(self.categories[0])
            self.dateUpdated = product['date_updated']
            self.href = href

            self.toFileDict = {}
            self.toFileDict['size'] = self.size
            self.toFileDict['price'] = self.price
            self.toFileDict['shipping'] = self.shipping
            self.toFileDict['pictures'] = self.pictures
            self.toFileDict['description'] = self.description
            self.toFileDict['categories'] = self.categories
            self.toFileDict['category'] = self.category
            self.toFileDict['dateUpdated'] = self.dateUpdated
            self.toFileDict['href'] = self.href
            self.toFileStr = json.dumps(self.toFileDict)

        except:
            # self.toFileDict = {}
            # self.toFileDict['href'] = href
            # self.toFileStr = json.dumps(self.toFileDict)
            self.href = href

        # else:
            # self.toFileStr = jsonIn
            # self.toFileDict = json.loads(jsonIn)
            # if self.size:
            #     self.size = self.toFileDict['size']
            #     self.price = self.toFileDict['price']
            #     self.shipping = self.toFileDict['shipping']
            #     self.pictures = self.toFileDict['pictures']
            #     self.description = self.toFileDict['description']
            #     self.categories = self.toFileDict['categories']
            #     self.category = self.toFileDict['category']
            #     self.dateUpdated = self.toFileDict['dateUpdated']
            # self.href = self.toFileDict['href']






    def __eq__(self, other):
            return isinstance(other, Entry) and self.description == other.description and self.dateUpdated == other.dateUpdated

    def __repr__(self):
        return self.href








class TodaysFinds(QWidget):
    def __init__(self):
        super().__init__()
        # initialize window
        self.setWindowTitle("Today's Finds")
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        # creating the default widgets/layouts
        self.grid = QGridLayout()
        # self.button = ["Back (Home)", "Update"]
        # self.hbox = QHBoxLayout()

        # for i in range(len(self.button)):
        #     self.button[i] = QPushButton(self.button[i])

        # setting column titles to the grid
        # self.grid.addWidget(QLabel("Username"), 0, 0)
        # self.grid.addWidget(QLabel("Name"), 0, 1)
        # self.grid.addWidget(QLabel("Phone Number"), 0, 2)
        # self.grid.addWidget(QLabel("Assigned Sites"), 0, 3, Qt.AlignCenter)

        # mapping buttons to respective functions
        # self.button[0].clicked.connect(self.goTo3)
        # self.button[1].clicked.connect(self.updateButton)

        # creating a row using the necessary data from each sitetester
        index = 0
        numTodaysFinds = len(todaysFinds)
        for (i, entry) in enumerate(todaysFinds):
            if numTodaysFinds >= 10:
                if i % (numTodaysFinds // 10) == 0:
                    if i / (numTodaysFinds // 10) * 10 <= 100:
                        print("Creating Visual Grid Entries: {0}%".format(i / (numTodaysFinds // 10) * 10))
            self.grid.addWidget(GridEntry(entry), index / 4, index % 4)
            index += 1


        # making an hbox for the two bottom buttons
        # self.hbox.addWidget(self.button[0])
        # self.hbox.addWidget(self.button[1])

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
        self.scrollArea.setMinimumWidth(200 * 4 + 3 * 12 + 16)#self.gridWidget.width() + 16)
        self.scrollArea.setMinimumHeight(700)
        self.vbox.addWidget(self.scrollArea)
        # self.vbox.addLayout(self.hbox)



class GridEntry(QWidget):
    def __init__(self, entry):
        super().__init__()
        vbox = QVBoxLayout()
        self.picLabel = QLabel('picture')
        self.picLabel.setMinimumSize(200, 200)
        self.picIndex = 0
        self.entry = entry
        try:
            picData = urllib.request.urlopen(entry.pictures[0]).read()
            self.picLabel.setMaximumSize(200, 200)
            self.picLabel.setScaledContents(True)
            picPixmap = QPixmap()
            picPixmap.loadFromData(picData)
            self.picLabel.setPixmap(picPixmap)
        except Exception as e:
            print(e)

        button = QPushButton("Next Picture")
        button.clicked.connect(self.nextpic)

        descLabel = QLabel('<a href="{0}">{1}</a>'.format('https://www.depop.com' + entry.href, entry.description[:50] + "..."))
        descLabel.setTextFormat(Qt.RichText)
        descLabel.setTextInteractionFlags(Qt.TextBrowserInteraction)
        descLabel.setOpenExternalLinks(True)
        descLabel.setWordWrap(True)
        vbox.addWidget(self.picLabel)
        vbox.addWidget(button)
        vbox.addWidget(descLabel)
        if entry.shipping != None:
            if float(entry.shipping):
                vbox.addWidget(QLabel('${0} (${2} Shipped)'.format(entry.price, entry.shipping, round(float(entry.price) + float(entry.shipping), 2))))
            else:
                vbox.addWidget(QLabel('${2}'.format(entry.price, entry.shipping, round(float(entry.price) + float(entry.shipping), 2))))
            if entry.size != "N/A":
                vbox.addWidget(QLabel(entry.size))
        # else:
        #     try:
        #         print(entry)
        #         print(entry.shipping)
        #         print(entry.size)
        #     except:
        #         error = 1
        self.setLayout(vbox)
        self.setMinimumSize(200, 350)
        self.setMaximumSize(200, 350)

    def nextpic(self):
        if len(self.entry.pictures) > 1:
            self.picIndex += 1
            self.picIndex %= len(self.entry.pictures)
            picData = urllib.request.urlopen(self.entry.pictures[self.picIndex]).read()
            self.picLabel.setMaximumSize(200, 200)
            self.picLabel.setScaledContents(True)
            picPixmap = QPixmap()
            picPixmap.loadFromData(picData)
            self.picLabel.setPixmap(picPixmap)



if __name__ == "__main__":
    #for debugging:
    # with open("Seen.txt", 'w'):
    #     test = 1

    hrefs = set()
    with open("Seen.txt", "r") as seen:
        for line in seen:
            if line:
                # lineDict = json.loads(line)
                # urlSet.add(lineDict['url'])
                hrefs.add(line.strip())
    # pprint(hrefsSeen)

    # searchTerms = set()
    # with open("SearchTerms.txt", "r") as terms:
    #     for line in terms:
    #         if line:
    #             searchTerms.add(line.strip())


    with open("Seen.txt", "a") as seen:
        # options = webdriver.ChromeOptions()
        # options.add_argument('headless')
        #
        # driver = webdriver.Chrome("/home/adam/Documents/Projects/Files/chromedriver", options=options)
        # hrefs = set()
        # numSearchTerms = len(searchTerms)
        # currentNum = 0
        # for term in searchTerms:
        #     currentNum += 1
        #     print('Searching for "{0}"... ({1}/{2})'.format(term, currentNum, numSearchTerms))
        #     driver.get('https://www.depop.com/search/?q=' + term)
        #     time.sleep(3)
        #     scroll = 0
        #     count = 0
        #     while count < 10:
        #         driver.execute_script('scroll(0, 1000000);')
        #         newScroll = driver.execute_script('return document.body.scrollHeight;')
        #         # print(newScroll)
        #         if newScroll == scroll:
        #             count += 1
        #         scroll = newScroll
        #         time.sleep(0.4)
        #
        #     html = driver.page_source
        #
        #     soup = BeautifulSoup(html, "html.parser")
        #
        #     for a in soup.find_all('a'):
        #         try:
        #             if 'bVpHsn' in a['class']:
        #                 # if 'product' in a['href']:
        #                 hrefs.add(a['href'])
        #         except:
        #             continue
        # driver.close()
        #
        newEntries = []
        numHrefs = len(hrefs)
        # pprint(hrefs)
        for (i, href) in enumerate(hrefs):
            if numHrefs >= 10:
                if i % (numHrefs // 10) == 0:
                    if i / (numHrefs // 10) * 10 <= 100:
                        print("Creating Entries: {0}%".format(i / (numHrefs // 10) * 10))
            # if href not in hrefsSeen:
            newEntries.append(Entry(href=href))

        # for url in urlSet:
        #     if url[21:] not in hrefs:
        #         for line in seen:
        #             if


        todaysFinds = []
        # print("about to find todays finds")
        numNewEntries = len(newEntries)
        for (i, entry) in enumerate(newEntries):
            if numNewEntries >= 10:
                if i % (numNewEntries // 10) == 0:
                    if i / (numNewEntries // 10) * 10 <= 100:
                        print("Finding Criteria Matches: {0}%".format(i / (numNewEntries // 10) * 10))
            # print(entry.href, file=seen)
            # print("set seen file")
            try:
                # print("trying")
                # print(entry.category)
                # print(entry.size)
                if float(entry.price) > 65 or float(entry.price) < 2:
                    continue
                if entry.category == "T-Shirt":
                    if entry.size == "XL" or entry.size == "L":
                        todaysFinds.append(entry)
                        # print(entry, file=finds)
                elif entry.category == "Outerwear":
                    if entry.size == "XL" or entry.size == "L":
                        todaysFinds.append(entry)
                        # print(entry, file=finds)
                elif entry.category == "Accessories":
                    if "flag" in entry.description.lower() or "hat" in entry.description.lower():
                        todaysFinds.append(entry)
                        # print(entry, file=finds)
                elif entry.category == 'Music':
                    if "vinyl" in entry.description.lower():
                        todaysFinds.append(entry)
                        # print(entry, file=finds)
            except:
                error = 1
        # print(todaysFinds)

    app = QApplication(sys.argv)

    window = TodaysFinds()
    window.show()

    sys.exit(app.exec_())
