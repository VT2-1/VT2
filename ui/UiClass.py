from PyQt6 import QtWidgets, QtCore, uic
from addit import *

class Ui_MainWindow(object):
    def __init__(self, MainWindow, argv=[], api=None):
        super().__init__()
        self.MainWindow = MainWindow
        self.api = api

    def setupUi(self):
        self.MainWindow.setFocus()
        uic.loadUi("ui/main.vt-ui", self.MainWindow)

        self.translator = QtCore.QTranslator()
        self.horizontalLayout = self.MainWindow.horizontalLayout
        self.treeView = self.MainWindow.treeView
        self.centralwidget = self.MainWindow.centralwidget
        self.statusbar = self.MainWindow.statusbar
        self.encodingLabel = self.MainWindow.encodingLabel

        self.treeSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.horizontalLayout.addWidget(self.treeSplitter)

        self.tabWidget = TabWidget(parent=self.centralwidget, MainWindow=self.MainWindow)
        self.treeSplitter.addWidget(self.treeView)
        self.treeSplitter.addWidget(self.tabWidget)

        self.MainWindow.setCentralWidget(self.centralwidget)

        self.statusbar.addPermanentWidget(self.encodingLabel)

        self.treeView.doubleClicked.connect(self.api.activeWindow.signals.onDoubleClicked)
        self.tabWidget.currentChanged.connect(self.api.activeWindow.signals.tabChngd)