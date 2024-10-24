import sys, os, importlib
from PyQt6 import QtWidgets, QtCore, QtGui
import platform

class MyAPI:
    def __init__(self):
        self.app = QtWidgets.QApplication.instance()
        print(self.app)
        self.windows = []
        self.activeWindow = None

    class Window:
        def __init__(self, api, views=None, activeView=None, qmwclass: QtWidgets.QMainWindow=None):
            self.__api = api
            self.__mw = qmwclass
            self.signals = self.__mw
            self.views = views or []
            self.activeView = activeView

            self.__api.windows.append(self)

        def newFile(self):
            self.__mw.addTab()
            tab = self.__mw.tabWidget.currentWidget()
        
        def openFiles(self, files):
            self.__mw.pl.executeCommand({"command": "openFile", "args": files})
        
        def saveFile(self, view=False):
            self.__mw.pl.executeCommand({"command": "saveFile"})
        
        def activeView(self):
            return self.activeView
        
        def views(self):
            return self.views
        
        def focus(self, view):
            self.activeView = view
        
        def runCommand(self, command):
            self.__mw.pl.executeCommand(command)
        
        def showQuickPanel(self, items, on_select, on_highlight=None, flags=0, selected_index=-1):
            print(f"Showing quick panel with items: {items}")
        
        def showInputPanel(self, prompt, initial_text, on_done, on_change=None, on_cancel=None):
            print(f"Showing input panel with prompt: {prompt} and initial text: {initial_text}")
        
        def getCommand(self, name):
            return self.__mw.pl.regCommands.get(name)

        def getTheme(self):
            return self.__mw.themeFile

        def setTheme(self, theme):
            themePath = os.path.join(self.__mw.themesDir, theme)
            if os.path.isfile(themePath):
                self.__mw.setStyleSheet(open(themePath, "r+").read())

        def getLog(self):
            return self.__mw.logger.log

        def setLogMsg(self, msg):
            self.__mw.logger.log += f"\n{msg}"

        def getTreeModel(self):
            return self.model

        def getModelElement(self, i):
            return self.model.filePath(i)

        def setTreeWidgetDir(self, dir):
            self.model = QtGui.QFileSystemModel()
            self.model.setRootPath(dir)
            self.__mw.treeView.setModel(self.model)
            self.__mw.treeView.setRootIndex(self.model.index(dir))
            return self.model

        def setTheme(self, theme):
            themePath = os.path.join(self.__mw.themesDir, theme)
            if os.path.isfile(themePath):
                self.__mw.setStyleSheet(open(themePath, "r+").read())

        def updateMenu(self, menu, data):
            menuClass = self.__mw.pl.findMenu(self.__mw.menuBar(), menu)
            if menu:
                self.__mw.pl.clearMenu(self.__mw.menuBar(), menu)
                self.__mw.pl.parseMenu(data, menuClass)

    class View:
        def __init__(self, api, window, qwclass=None, text="", syntaxFile=None, file_name=None, read_only=False):
            self.__api = api
            self.window = window
            self.__tab = qwclass
            self.__tabWidget = self.__tab.parentWidget().parentWidget()
            self.text = text
            self.syntaxFile = syntaxFile
            self.file_name = file_name
            self.read_only = read_only
            self.tab_title = None
            self.tab_encoding = None
        
        def tabIndex(self):
            return self.__tab.currentIndex()

        def window(self):
            return self.window

        def getTitle(self):
            return self.__tabWidget.tabText(self.__tabWidget.indexOf(self.__tab))

        def setTitle(self, text):
            return self.__tabWidget.setText(self.__tabWidget.indexOf(self.__tab), text)

        def getText(self):
            text = self.__tab.textEdit.toPlainText()
            return text

        def getHtml(self):
            text = self.__tab.textEdit.toHtml()
            return text

        def setText(self, text):
            self.__tab.textEdit.setText(text)
            return text

        def getFile(self):
            return self.__tab.file

        def setFile(self, file):
            self.__tab.file = file
            return self.__tab.file

        def getCanSave(self):
            return self.__tab.canSave

        def setCanSave(self, b: bool):
            self.__tab.canSave = b
            return b

        def getCanEdit(self):
            return self.__tab.canEdit

        def setReadOnly(self, b: bool):
            self.__tab.canEdit = b
            self.__tab.textEdit.setReadOnly(b)
            self.__tab.textEdit.setDisabled(b)
            return b

        def getEncoding(self):
            return self.__tab.encoding

        def setEncoding(self, enc):
            self.__tab.encoding = enc
            return enc

        def getSaved(self):
            return self.__window.tabWidget.isSaved(self.__tab)

        def setSaved(self, b: bool):
            self.__window.tabWidget.tabBar().setSaved(self.__tab or self.__window.tabWidget.currentWidget(), b)
            return b

        def size(self):
            return len(self.__tab.textEdit.toPlainText())

        def substr(self, region):
            return self.__tab.textEdit.toPlainText()[region.begin():region.end()]

        def sel(self):
            pass

        def insert(self, point, string):
            t = self.__tab.textEdit.toPlainText()
            lines = self.text.splitlines()
            line_index = point.x
            char_index = point.y
            
            point = sum(len(lines[i]) + 1 for i in range(line_index)) + char_index
            self.__tab.textEdit.setPlainText(t[:point] + string + t[point:])
        
        def erase(self, region):
            t = self.__tab.textEdit.toPlainText()
            self.__tab.textEdit.setPlainText(t[:region.begin()] + t[region.end():])
        
        def replace(self, region, string):
            t = self.__tab.textEdit.toPlainText()
            self.__tab.textEdit.setPlainText(t[:region.begin()] + string + t[region.end():])

        def find(self, pattern, start_point, flags=0):
            pass

        def findAll(self, pattern, flags=0):
            pass

        def setSyntaxFile(self, syntaxFilePath):
            self.syntaxFile = syntaxFilePath

        def settings(self):
            pass

        def fileName(self):
            return self.fileName

        def isDirty(self):
            return self.__window.tabWidget.isSaved(self.__tab)

        def isReadOnly(self):
            return self.read_only

        def getTextSelection(self):
            return self.__tab.textEdit.textCursor().selectedText()

        def getTextCursor(self):
            return self.__tab.textEdit.textCursor()

        def setTextSelection(self, s, e):
            cursor = self.__tab.textEdit.textCursor()
            cursor.setPosition(s)
            cursor.setPosition(e, QtGui.QTextCursor.MoveMode.KeepAnchor)
            self.__tab.textEdit.setTextCursor(cursor)

        def getCompletePos(self):
            current_text = self.__tab.textEdit.toPlainText()
            cursor_position = self.__tab.textEdit.textCursor().position()

            line_number = self.__tab.textEdit.textCursor().blockNumber()
            column = self.__tab.textEdit.textCursor().columnNumber()

            lines = current_text.splitlines()
            if 0 <= line_number < len(lines):
                line = lines[line_number]
                return current_text, line_number + 1, column
            else:
                return current_text, 0, 0

        def setCompleteList(self, lst):
            self.completer = self.__tab.textEdit.completer.updateCompletions(lst)

        def setHighlighter(self, hl):
            self.__tab.textEdit.highLighter.highlightingRules = hl

        def rehighlite(self):
            self.__tab.textEdit.highLighter.rehighlight()

        def show_popup(self, content, flags=0, location=-1, max_width=320, max_height=240, on_navigate=None, on_hide=None):
            self.content = content
            self.flags = flags
            self.location = location
            self.max_width = max_width
            self.max_height = max_height
            self.on_navigate = on_navigate
            self.on_hide = on_hide

            self.dialog = QtWidgets.QDialog()
            self.dialog.setWindowFlags(self.flags)
            self.dialog.setMaximumWidth(self.max_width)
            self.dialog.setMaximumHeight(self.max_height)

            self.dialog.setLayout(self.content)

            self.dialog.exec()

    class Selection:
        def __init__(self, regions=None):
            self.regions = regions or []

        def clear(self):
            self.regions = []
        
        def add(self, region):
            self.regions.append(region)
        
        def subtract(self, region):
            self.regions = [r for r in self.regions if r != region]
        
        def contains(self, point):
            return any(region.contains(point) for region in self.regions)

        def text(self, view, region):
            return view.__tab.toPlainText()[region.begin():region.end()]

    class Region:
        def __init__(self, a, b):
            self.a = a
            self.b = b
        
        def begin(self):
            return min(self.a, self.b)
        
        def end(self):
            return max(self.a, self.b)
        
        def contains(self, point):
            return self.begin() <= point <= self.end()

    class Settings:
        def __init__(self, settings=None):
            self.settings = settings or {}

        def get(self, key, default=None):
            return self.settings.get(key, default)
        
        def set(self, key, value):
            self.settings[key] = value
        
        def erase(self, key):
            if key in self.settings:
                del self.settings[key]
        
        def has(self, key):
            return key in self.settings

    class Dialogs:
        def infoMessage(string):
            QtWidgets.QMessageBox.information(None, "Message", string)
        def warningMessage(string):
            QtWidgets.QMessageBox.warning(None, "Warning", string)
        def errorMessage(string):
            QtWidgets.QMessageBox.critical(None, "Error", string)

        def okCancelDialog(string):
            result = QtWidgets.QMessageBox.question(None, "Confirmation", string,
                                        QtWidgets.QMessageBox.StandardButton.Ok | QtWidgets.QMessageBox.StandardButton.Cancel,
                                        QtWidgets.QMessageBox.StandardButton.Cancel)
            return result == QtWidgets.QMessageBox.StandardButton.Ok

        def yesNoCancelDialog(string):
            result = QtWidgets.QMessageBox.question(None, "Confirmation", string,
                                        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No | QtWidgets.QMessageBox.StandardButton.Cancel,
                                        QtWidgets.QMessageBox.StandardButton.Cancel)
            if result == QtWidgets.QMessageBox.StandardButton.Yes:
                return "yes"
            elif result == QtWidgets.QMessageBox.StandardButton.No:
                return "no"
            else:
                return "cancel"

        def openFileDialog(e=None):
            dlg = QtWidgets.QFileDialog.getOpenFileNames(None, "Open File", "", "All Files (*);;Text Files (*.txt)")
            return dlg

        def saveFileDialog(e=None):
            dlg = QtWidgets.QFileDialog.getSaveFileName()
            return dlg

        def openDirDialog(self, e=None):
            dlg = QtWidgets.QFileDialog.getExistingDirectory(
                self.__window.treeView,
                caption="VarTexter - Get directory",
            )
            return str(dlg)

    class Plugin:
        class TextCommand:
            def __init__(self, view):
                self.view = view

            def run(self, edit):
                ...
            
            def is_enabled(self):
                pass
            
            def is_visible(self):
                pass
            
            def description(self):
                pass

        class WindowCommand:
            def __init__(self, window):
                self.window = window

            def run(self):
                ...
            
            def is_enabled(self):
                pass
            
            def is_visible(self):
                pass
            
            def description(self):
                pass

        class ApplicationCommand:
            def __init__(self):
                pass

            def run(self):
                ...
            
            def is_enabled(self):
                pass
            
            def is_visible(self):
                pass
            
            def description(self):
                pass

    class Point:
        def __init__(self, x=0, y=0):
            """Инициализация точки с координатами x и y."""
            self.x = x
            self.y = y

        def move(self, dx, dy):
            """Перемещение точки на (dx, dy)."""
            self.x += dx
            self.y += dy

        def distance_to(self, other):
            """Расчет расстояния до другой точки."""
            if not isinstance(other, MyAPI.Point):
                raise ValueError("The other must be an instance of Point.")
            return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

        def __str__(self):
            """Строковое представление точки."""
            return f"Point({self.x}, {self.y})"

        def __eq__(self, other):
            """Сравнение двух точек."""
            if isinstance(other, MyAPI.Point):
                return self.x == other.x and self.y == other.y
            return False

    class SigSlots(QtCore.QObject):
        commandsLoaded = QtCore.pyqtSignal()
        tabClosed = QtCore.pyqtSignal(int, str)
        tabCreated = QtCore.pyqtSignal()
        tabChanged = QtCore.pyqtSignal()
        textChanged = QtCore.pyqtSignal()
        windowClosed = QtCore.pyqtSignal()

        treeWidgetClicked = QtCore.pyqtSignal(QtCore.QModelIndex)
        treeWidgetDoubleClicked = QtCore.pyqtSignal(QtCore.QModelIndex)
        treeWidgetActivated = QtCore.pyqtSignal()

        def __init__(self, w):
            super().__init__(w)
            self.__window = w

            self.__window.treeView.doubleClicked.connect(self.onDoubleClicked)

        def tabChngd(self, index):
            if index > -1:
                self.__window.setWindowTitle(
                    f"{os.path.normpath(self.__window.api.Tab.getTabFile(index) or 'Untitled')} - {self.__window.appName}")
                if index >= 0: self.__window.encodingLabel.setText(self.__window.tabWidget.widget(index).encoding)
                self.updateEncoding()
            else:
                self.__window.setWindowTitle(self.__window.appName)
            self.tabChanged.emit()

        def updateEncoding(self):
            e = self.__window.api.Tab.getTabEncoding(self.__window.api.Tab.currentTabIndex())
            self.__window.encodingLabel.setText(e)

        def onDoubleClicked(self, index):
            self.treeWidgetDoubleClicked.emit(index)

        def onClicked(self, index):
            self.treeWidgetClicked.emit(index)

        def onActivated(self):
            self.treeWidgetActivated.emit()

    def activeWindow(self) -> Window:
        return self.activeWindow

    def windows(self):
        return self.windows

    def loadSettings(self, name):
        pass

    def saveSettings(self, name):
        pass

    def importModule(self, name):
        return importlib.import_module(name)

    def statusMessage(self, string):
        print(f"Status: {string}")

    def setTimeout(self, function, delay):
        QtCore.QTimer.singleShot(delay, function)

    def setTimeout_async(self, function, delay):
        self.setTimeout(function, delay)

    def scoreSelector(self, location, scope):
        return 100

    def version(self):
        return "4.0"

    def platform(self):
        return sys.platform

    def arch(self):
        if sys.maxsize > 2**32:
            if platform.system() == "Windows":
                return "x64"
            else:
                return "amd64"
        else:
            return "x86"

    def packagesPath(self):
        return "/"

    def installed_packagesPath(self):
        return "/path/to/installed/packages"
