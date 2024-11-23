from PyQt6 import QtWidgets, QtCore, QtGui, uic
import os

class TabBar(QtWidgets.QTabBar):
    def __init__(self, tabwidget):
        super().__init__()
        self.tabWidget = tabwidget
        self.savedStates = []
        self.setObjectName("tabBar")
        self.setMovable(True)
        self.setTabsClosable(True)

    def setTabSaved(self, tab, saved):
        if not tab in [i.get("tab") for i in self.savedStates]:
            self.savedStates.append({"tab": tab, "saved": saved})
        else:
            next((i for i in self.savedStates if i.get("tab") == tab), {})["saved"] = saved
        self.updateTabStyle(next((i for i in self.savedStates if i.get("tab") == tab), {}))

    def updateTabStyle(self, info):
        if info.get("tab"):
            idx = self.tabWidget.indexOf(info.get('tab'))
            if idx != -1:
                if info.get("saved"):
                    self.setStyleSheet(f"QTabBar::tab:selected {{ border-bottom: 2px solid white; }} QTabBar::tab:nth-child({idx+1}) {{ background-color: white; }}")
                else:
                    self.setStyleSheet(f"QTabBar::tab:selected {{ border-bottom: 2px solid yellow; }} QTabBar::tab:nth-child({idx+1}) {{ background-color: yellow; }}")

class TabWidget (QtWidgets.QTabWidget):
    def __init__ (self, MainWindow=None, parent=None):
        super(TabWidget, self).__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.closeTab)
        self.MainWindow = MainWindow
        self.moveRange = None
        self.setObjectName("tabWidget")
        self.setMovable(True)
        self.tabbar = TabBar(self)
        self.setTabBar(self.tabbar)
        self.currentChanged.connect(self.onCurrentChanged)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.cmRequest)

    def cmRequest(self, pos):
        self.MainWindow.tabBarContextMenu.exec(self.mapToGlobal(pos))

    def onCurrentChanged(self, index):
        current_tab = self.currentWidget()
        self.tabbar.updateTabStyle({"tab": current_tab, "saved": self.isSaved(current_tab)})

    def isSaved(self, tab):
        return any(i.get("tab") == tab and i.get("saved") for i in self.tabbar.savedStates)

    def setMovable(self, movable):
        if movable == self.isMovable():
            return
        QtWidgets.QTabWidget.setMovable(self, movable)
        if movable:
            self.tabBar().installEventFilter(self)
        else:
            self.tabBar().removeEventFilter(self)

    def eventFilter(self, source, event):
        if source == self.tabBar():
            if event.type() == QtCore.QEvent.MouseButtonPress and event.buttons() == QtCore.Qt.MouseButton.LeftButton:
                QtCore.QTimer.singleShot(0, self.setMoveRange)
            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                self.moveRange = None
            elif event.type() == QtCore.QEvent.MouseMove and self.moveRange is not None:
                if event.x() < self.moveRange[0] or event.x() > self.tabBar().width() - self.moveRange[1]:
                    return True
        return QtWidgets.QTabWidget.eventFilter(self, source, event)

    def setMoveRange(self):
        tabRect = self.tabBar().tabRect(self.currentIndex())
        pos = self.tabBar().mapFromGlobal(QtGui.QCursor.pos())
        self.moveRange = pos.x() - tabRect.left(), tabRect.right() - pos.x()

    def closeTab(self, currentIndex):
        if currentIndex >= 0:
            self.setCurrentIndex(currentIndex)
            tab = self.currentWidget()
            if not self.isSaved(tab):
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("VarTexter2 - Exiting")
                dlg.setText("File is unsaved. Do you want to save it?")
                dlg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No | QtWidgets.QMessageBox.StandardButton.Cancel)

                yesButton = dlg.button(QtWidgets.QMessageBox.StandardButton.Yes)
                yesButton.setObjectName("tabSaveYes")
                noButton = dlg.button(QtWidgets.QMessageBox.StandardButton.No)
                noButton.setObjectName("tabSaveNo")
                cancelButton = dlg.button(QtWidgets.QMessageBox.StandardButton.Cancel)
                cancelButton.setObjectName("tabSaveCancel")

                dlg.setDefaultButton(cancelButton)
                
                # dlg.setStyleSheet("QtWidgets.QMessageBox { background-color: black; } QLabel { color: white; }")
                
                result = dlg.exec()

                if result == QtWidgets.QMessageBox.StandardButton.Yes:
                    self.MainWindow.api.activeWindow.runCommand({"command": "SaveFileCommand", "args": [tab.file]})
                    self.MainWindow.api.activeWindow.signals.tabClosed.emit(self.MainWindow.api.activeWindow.activeView)
                    self.MainWindow.api.activeWindow.views.remove(self.MainWindow.api.activeWindow.activeView)
                    tab.deleteLater()
                    self.removeTab(currentIndex)
                elif result == QtWidgets.QMessageBox.StandardButton.No:
                    self.MainWindow.api.activeWindow.signals.tabClosed.emit(self.MainWindow.api.activeWindow.activeView)
                    self.MainWindow.api.activeWindow.views.remove(self.MainWindow.api.activeWindow.activeView)
                    tab.deleteLater()
                    self.removeTab(currentIndex)
                elif result == QtWidgets.QMessageBox.StandardButton.Cancel:
                    pass
            else:
                self.MainWindow.api.activeWindow.signals.tabClosed.emit(self.MainWindow.api.activeWindow.activeView)
                self.MainWindow.api.activeWindow.views.remove(self.MainWindow.api.activeWindow.activeView)
                tab.deleteLater()
                self.removeTab(currentIndex)

class Ui_MainWindow(object):
    def __init__(self, MainWindow, argv=[], api=None):
        super().__init__()
        self.MainWindow = MainWindow
        self.api = api

    def setupUi(self):
        self.MainWindow.setFocus()
        uic.loadUi(os.path.join(self.api.uiDir, "main.vt-ui"), self.MainWindow)

        # Exporting required classes

        self.translator = QtCore.QTranslator()
        self.horizontalLayout = self.MainWindow.horizontalLayout
        self.treeView = self.MainWindow.treeView
        self.centralwidget = self.MainWindow.centralwidget
        self.statusbar = self.MainWindow.statusbar
        self.encodingLabel = self.MainWindow.encodingLabel

        ###################

        self.treeSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.horizontalLayout.addWidget(self.treeSplitter)

        self.tabWidget = TabWidget(parent=self.centralwidget, MainWindow=self.MainWindow)
        self.treeSplitter.addWidget(self.tabWidget)

        self.MainWindow.setCentralWidget(self.centralwidget)

        self.encodingLabel.hide()
        self.treeView.hide()

        self.treeView.doubleClicked.connect(self.api.activeWindow.signals.onDoubleClicked)
        self.tabWidget.currentChanged.connect(self.api.activeWindow.signals.tabChngd)