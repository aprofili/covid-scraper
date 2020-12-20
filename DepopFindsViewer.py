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

class Entry:
    categoryDict = {43 : 'T-Shirt', 47 : 'Outerwear', 18 : 'Accessories', 29:'Music'}

    def __init__(self, href = "", tablerow=""):

        self.href = tablerow[0]
        self.size = tablerow[1]
        self.price = tablerow[2]
        self.shipping = tablerow[3]
        self.description = tablerow[4]
        self.category = tablerow[5]
        self.dateUpdated = tablerow[6]
        self.pictures = []
        cursor.execute("SELECT picture FROM todaysfindspictures WHERE href LIKE %s;", self.href)
        for row in cursor.fetchall():
            self.pictures.append(row[0])






    def __eq__(self, other):
        return isinstance(other, Entry) and self.description == other.description and self.dateUpdated == other.dateUpdated

    def __repr__(self):
        return self.href








class TodaysFinds(QWidget):
    def __init__(self, pageIndex):
        super().__init__()
        # initialize window



        self.setWindowTitle("Today's Finds")
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        self.hbox = QHBoxLayout()
        self.pageIndex = pageIndex
        self.nextPageButton = QPushButton("Next Page")
        if self.pageIndex >= pageCount - 1:
            self.nextPageButton.setDisabled(True)
        self.prevPageButton = QPushButton("Previous Page")
        if self.pageIndex < 1:
            self.prevPageButton.setDisabled(True)

        self.grid = QGridLayout()

        todaysFinds = []
        cursor.execute("SELECT * FROM todaysfinds LIMIT %s OFFSET %s;", (pageSize, pageSize * self.pageIndex))
        for row in cursor.fetchall():
            todaysFinds.append(Entry(tablerow=row))

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

        self.nextPageButton.clicked.connect(self.nextpage)
        self.prevPageButton.clicked.connect(self.prevpage)



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

    def nextpage(self):
        self.pageIndex += 1
        self.nextWindow = TodaysFinds(self.pageIndex)
        self.nextWindow.show()
        self.hide()
        self.deleteLater()

    def prevpage(self):
        self.pageIndex -= 1
        self.nextWindow = TodaysFinds(self.pageIndex)
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
        if entry.shipping != None:
            if float(entry.shipping):
                vbox.addWidget(QLabel('${0} (${2} Shipped)'.format(entry.price, entry.shipping, round(float(entry.price) + float(entry.shipping), 2))))
            else:
                vbox.addWidget(QLabel('${2}'.format(entry.price, entry.shipping, round(float(entry.price) + float(entry.shipping), 2))))
            if entry.size != "N/A":
                vbox.addWidget(QLabel(entry.size))
        self.setLayout(vbox)
        self.setMinimumSize(200, 350)
        self.setMaximumSize(200, 350)

    def nextpic(self):
        if len(self.entry.pictures) > 1:
            self.picIndex += 1
            self.picIndex %= len(self.entry.pictures)
            picData = urllib.request.urlopen(self.entry.pictures[self.picIndex], timeout=15).read()
            self.picLabel.setMaximumSize(200, 200)
            self.picLabel.setScaledContents(True)
            picPixmap = QPixmap()
            picPixmap.loadFromData(picData)
            self.picLabel.setPixmap(picPixmap)




if __name__ == "__main__":

    connection = pymysql.connect(host = "localhost", user = "root", password = "", db = "depopscraper", charset = "utf8mb4", cursorclass = pymysql.cursors.Cursor)
    cursor = connection.cursor()

    pageSize = 200
    cursor.execute("SELECT COUNT(*) FROM todaysfinds;")
    todaysFindsCount = cursor.fetchall()[0][0]
    pageCount = todaysFindsCount // pageSize + 1 * (todaysFindsCount % pageSize > 0)

    # todaysFinds = []
    # cursor.execute("SELECT * FROM todaysfinds LIMIT %s;", pageSize)
    # for row in cursor.fetchall():
    #     todaysFinds.append(Entry(tablerow=row))

    app = QApplication(sys.argv)

    window = TodaysFinds(pageIndex=0)
    window.show()

    sys.exit(app.exec_())
