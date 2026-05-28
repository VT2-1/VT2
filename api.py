from enum import Enum
from PySide6 import QtWidgets, QtCore, QtGui
from typing import *
import os, sys, json, importlib, re, platform, asyncio, time, functools, html
import importlib.util
import inspect


def findMatch(lst, obj):
    return next((i for i in lst if i == obj), None)

def _replace_var(data):
    def replace_var(match):
        env_var = match.group(1)
        return os.getenv(env_var, f'%{env_var}%')
    return re.sub(r'%([^%]+)%', replace_var, data)

def findKey(p, d):
    current = d
    path = p.split(".")
    for key in path:
        if isinstance(current, dict) and key in current:
             current = current[key]
        else:
             return None
    return current

def addKey(p, value, d):
    path = p.split(".")
    current = d
    for key in path[:-1]:
        if key not in current or not isinstance(current[key], dict):
             current[key] = {}
        current = current[key]
    current[path[-1]] = value

def importModule(name):
    return importlib.import_module(name)

def setTimeout(function, delay):
    QtCore.QTimer.singleShot(delay, function)

def version():
    return "1.3"

def getPlatform():
    current_platform = platform.system()
    if current_platform == "Darwin":
        return "OSX"
    return current_platform

def arch():
    if sys.maxsize > 2**32:
        if platform.system() == "Windows":
             return "x64"
        else:
             return "amd64"
    else:
        return "x86"

class Color(str, Enum):
    INFO = ""
    WARNING = "#edba00"
    ERROR = "#e03c00"
    SUCCESS = "#61a600"
    BLUE = "#4034eb"

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
        for region in self.regions:
            if region.contains(point):
                return True
        return False

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
    
    def data(self):
        return self.settings

    def get(self, key, default=None):
        if type(self.settings) == dict:
            return self.settings.get(key, default)
    
    def set(self, key, value):
        if type(self.settings) == dict:
            self.settings[key] = value
    
    def erase(self, key):
        if type(self.settings) == dict:
            if key in self.settings:
                del self.settings[key]
    
    def has(self, key):
        return key in self.settings

    def write(self, file):
        if type(file) == str:
            file = VtAPI.File(file)
        file.write(json.dumps(self.settings))
    
    @classmethod
    def fromFile(cls, f):
        content = "".join(f.read())
        settings = json.loads(content)
        return cls(settings)

class Dialogs:
    def infoMessage(string, title=None):
        QtWidgets.QMessageBox.information(None, title or "Message", string)
    def warningMessage(string, title=None):
        QtWidgets.QMessageBox.warning(None, title or "Warning", string)
    def errorMessage(string, title=None):
        QtWidgets.QMessageBox.critical(None, title or "Error", string)

    def okCancelDialog(string, title=None):
        result = QtWidgets.QMessageBox.question(None, title or "Confirmation", string,
                                     QtWidgets.QMessageBox.StandardButton.Ok | QtWidgets.QMessageBox.StandardButton.Cancel,
                                     QtWidgets.QMessageBox.StandardButton.Cancel)
        return result == QtWidgets.QMessageBox.StandardButton.Ok

    def yesNoCancelDialog(string, title=None):
        result = QtWidgets.QMessageBox.question(None, title or "Confirmation", string,
                                     QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No | QtWidgets.QMessageBox.StandardButton.Cancel,
                                     QtWidgets.QMessageBox.StandardButton.Cancel)
        if result == QtWidgets.QMessageBox.StandardButton.Yes:
            return "yes"
        elif result == QtWidgets.QMessageBox.StandardButton.No:
            return "no"
        else:
            return "cancel"

    def openFileDialog(title=None):
        dlg = QtWidgets.QFileDialog.getOpenFileNames(None, title or "Open File", "", "All Files (*);;Text Files (*.txt)")
        return dlg

    def saveFileDialog(title=None):
        dlg = QtWidgets.QFileDialog.getSaveFileName(caption=title or "Save File")
        return dlg

    def openDirDialog(title=None):
        dlg = QtWidgets.QFileDialog.getExistingDirectory(caption=title or "Get directory")
        return str(dlg)

    def inputDialog(title=""):
        dlg = QtWidgets.QDialog()
        dlg.setWindowTitle(title)

        layout = QtWidgets.QVBoxLayout(dlg)
        
        line_edit = QtWidgets.QLineEdit(dlg)
        layout.addWidget(line_edit)
        
        ok_button = QtWidgets.QPushButton("OK", dlg)
        layout.addWidget(ok_button)
        
        def accept_dialog():
            dlg.accept()

        ok_button.clicked.connect(accept_dialog)
        
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            return line_edit.text(), dlg
        return None, dlg

class Path:
    def __init__(self, path=None, encoding="utf-8"):
        self.path = path

    def __str__(self):
        return self.path

    def exists(self):
        return os.path.exists(self.path)
    
    def isFile(self):
        return os.path.isfile(self.path)
    
    def isDir(self):
        return os.path.isdir(self.path)
    
    def joinPath(*args):
        return os.path.join(*args)
    
    def dirName(self):
        return os.path.dirname(self.path)
    
    def chdir(path):
        os.chdir(path)
    
    def create(self):
        os.makedirs(self.path, exist_ok=True)
    
    def normalize(self):
        return os.path.normpath(self.path)
    
    def dir(self):
        return os.listdir(self.path)
    
    def remove(self):
        os.remove(self.path)

class File:

    def __init__(self, path=None, encoding="utf-8"):
        self.path = path
        self.encoding = encoding

    def __str__(self):
        return self.path

    def read(self, chunk=1024):
        lines = []
        if self.encoding == "binary":
            self.mode = "rb"
        else:
            self.mode = "r"
        if self.exists() and not os.path.isdir(self.path):
            with open(self.path, self.mode, encoding=None if self.mode == "rb" else self.encoding) as file:
                while True:
                    chunk_data = file.read(chunk)
                    if not chunk_data:
                        break
                    lines.append(chunk_data)
        return lines

    def write(self, content, chunk=1024):
        total_length = len(content)
        mode = 'wb' if isinstance(content, (bytes, bytearray)) or self.encoding == 'binary' else 'w'
        open_kwargs = {} if 'b' in mode else {'encoding': self.encoding}
        with open(self.path, mode, **open_kwargs) as file:
            for i in range(0, total_length, chunk):
                chunkk = content[i:i + chunk]
                file.write(chunkk if 'b' in mode else str(chunkk))

    def exists(self):
        return os.path.isfile(self.path)

    def create(self, rewrite=False):
        if rewrite:
            open(self.path, "a+", encoding=self.encoding).close()
        elif not self.exists():
            open(self.path, "a", encoding=self.encoding).close()

class Theme:

    def __init__(self, name=None, path=None):
        self.name = name
        self.path = path

    def __str__(self):
        return self.path

    def use(self, window=None):
        window.setTheme(self.path)

    def exists(self):
        return os.path.isfile(self.path)

class Plugin:
    def __init__(self, api, name, path):
        self.api = api  # Оставляем без аннотации типа
        self.name = name
        self.path = path

    def __str__(self):
        return self.path

    def load(self, window):
        window._Window__mw.pl.plugins[self.name] = self.path
        window._Window__mw.pl.loadPlugin(self.name)
        window._Window__mw.pl.plugins.pop(self.name)

    class ApplicationCommand(QtCore.QObject):
        def __init__(self, api):
             super().__init__()
             self.api = api

        def run(self):
             raise NotImplementedError("You must rewrite 'run' function of your command")

        def description(self):
             pass

    class WindowCommand(ApplicationCommand):
        def __init__(self, api, window):
             super().__init__(api)
             self.window = window
             self.__signals = {}

        def __del__(self):
             for signal in self.__signals:
                 self.window.signals.deleteSignal(signal)

        def addSignal(self, name, signal):
             self.__signals[name] = signal
             self.window.signals.addSignal(name, signal)

    class TextCommand(WindowCommand):
        def __init__(self, api, view):
             super().__init__(api, view.window())
             self.view = view

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
        if not isinstance(other, VtAPI.Point):
             raise ValueError("The other must be an instance of Point.")
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def __str__(self):
        """Строковое представление точки."""
        return f"Point({self.x}, {self.y})"

    def __eq__(self, other):
        """Сравнение двух точек."""
        if isinstance(other, VtAPI.Point):
             return self.x == other.x and self.y == other.y
        return False

class Widgets:
    class DockWidget(QtWidgets.QDockWidget):
        def __init__(self, parent=None):
             super().__init__(parent)
             self.__window = None

        def parent(self):
             return None

        def window(self):
             return None

    class Dialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
             super().__init__(parent)
             self.__window = None

        def parent(self):
             return None

        def window(self):
             return None
    
    class Thread(QtCore.QThread):
        def __init__(self):
             super().__init__()
        
        def parent(self):
             return None

    class Process(QtCore.QProcess):
        def __init__(self):
             super().__init__()
    
    class ToolBar(QtWidgets.QToolBar):
        def __init__(self, *args, **kwargs):
             super().__init__(*args, **kwargs)
    
    class Action(QtGui.QAction):
        def __init__(self, *args, **kwargs):
             super().__init__(*args, **kwargs)

    class Signal(QtCore.QObject):
        """
        Custom signal with priority support.
        """
        def __init__(self, *args, **kwargs):
             super().__init__()
             self._signal = QtCore.Signal(*args)
             self._queue = []
             self._timer = QtCore.QTimer(self)
             self._args = []
             self._kwargs = {}

        def connect(self, slot, priority=1):
             """
             Connects a slot to the signal with a specified priority.
             """
             self._queue.append((priority, slot))

        def emit(self, *args, **kwargs):
            """Emits the signal, calling all connected slots in order of priority. """
            for priority, slot in sorted(self._queue, key=lambda x: x[0], reverse=True):
                try:
                    sig = inspect.signature(slot)
                    try:
                        sig.bind(*args, **kwargs)
                        slot(*args, **kwargs)
                    except TypeError:
                        slot()
                except Exception as e:
                    print(f"[Signal emit error] {slot} raised: {e}")

        def disconnect(self, slot):
             for sl in self._queue:
                 if sl[1] == slot:
                     self._queue.remove(sl)

class Signals(QtCore.QObject):
    def __init__(self, w):
        super().__init__(w)
        self.__window: QtWidgets.QMainWindow = w
        self.__windowApi: VtAPI = self.__window.api
        self._signals = {}

        self.addSignal("tabClosed", VtAPI.Widgets.Signal(object))
        self.addSignal("tabCreated", VtAPI.Widgets.Signal())
        self.addSignal("tabChanged", VtAPI.Widgets.Signal(object, object))

        self.addSignal("textChanged", VtAPI.Widgets.Signal())

        self.addSignal("windowClosed", VtAPI.Widgets.Signal())
        self.addSignal("windowStarted", VtAPI.Widgets.Signal())
        self.addSignal("windowStateRestoring", VtAPI.Widgets.Signal())
        self.addSignal("windowRunningStateInited", VtAPI.Widgets.Signal())
        self.addSignal("windowStateSaving", VtAPI.Widgets.Signal())

        self.addSignal("logWrited", VtAPI.Widgets.Signal(str))

        self.addSignal("treeWidgetClicked", VtAPI.Widgets.Signal(QtCore.QModelIndex))
        self.addSignal("treeWidgetDoubleClicked", VtAPI.Widgets.Signal(QtCore.QModelIndex))
        self.addSignal("treeWidgetActivated", VtAPI.Widgets.Signal())

        self.addSignal("fileOpened", VtAPI.Widgets.Signal(object))
        self.addSignal("fileSaved", VtAPI.Widgets.Signal(object))
        self.addSignal("fileTagInited", VtAPI.Widgets.Signal(object))

        self.addSignal("fileTagAdded", VtAPI.Widgets.Signal(object, str))
        self.addSignal("fileTagRemoved", VtAPI.Widgets.Signal(object, str))

    def __getattr__(self, name):
        if name in self._signals:
             return self._signals[name]
        raise AttributeError(f"'Signals' object has no attribute '{name}'")

    def addSignal(self, signalName, signal):
        if not signalName in self._signals: self._signals[signalName] = signal
        else: raise ValueError(self.__windowApi.activeWindow.translate("Signals already has signal '{}'".format(signalName)))

    def deleteSignal(self, signalName):
        if signalName in self._signals: self._signals.pop(signalName)

    def findSignal(self, signalName):
        return self._signals.get(signalName)

    def tabChngd(self, index):
        widget = self.__window.tabWidget.currentWidget()
        try:
             if widget:
                 view = self.__windowApi.View(self.__windowApi, self.__windowApi.activeWindow, id=widget.objectName().split("-")[-1])
                 for v in self.__windowApi.activeWindow.views:
                     if v == view:
                          self.tabChanged.emit(self.__windowApi.activeWindow.activeView, v)
                          self.__windowApi.activeWindow.focus(v)
                          self.updateEncoding()
                          break
                 else:
                     self.__window.setWindowTitle(self.__windowApi.appName())
             else:
                 self.__window.setWindowTitle(self.__windowApi.appName())
        except Exception as e:
             self.__window.setWindowTitle(self.__windowApi.appName())
             self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Error when updating tabs: {}").format(e))

    def updateEncoding(self):
        e = self.__windowApi.activeWindow.activeView.getEncoding()
        self.__window.statusBar().encodingLabel.setText(e.upper())

class View:

    def __init__(self, api, window, qwclass=None, id=None):
        self.api: VtAPI = api
        self.__window: VtAPI.Window = window
        self.__tab: QtWidgets.QWidget = qwclass
        if self.__tab:
             self.__id = self.__tab.objectName().split("-")[-1]
             self.__tabWidget: QtWidgets.QTabWidget = self.window()._Window__mw.tabWidget
             self.tagBase = window._Window__mw.tagBase
        else:
             self.__id = id
             self.__tabWidget = None
             self.tagBase = None
    def __eq__(self, other):
       if not isinstance(other, VtAPI.View):
            return NotImplemented
       return self.id() == other.id()
   
    def id(self):
       return self.__id

    def __hash__(self):
        return hash(self.id())

    def tabIndex(self):
        return self.__tabWidget.indexOf(self.__tab)

    def close(self):
        self.__tabWidget.closeTab(self.__tab)

    def window(self):
        return self.__window

    def focus(self):
        self.window().focus(self)
        self.__tab.textEdit.setFocus()

    def getTitle(self):
        return self.__tabWidget.tabText(self.__tabWidget.indexOf(self.__tab))

    def setTitle(self, text):
        self.__tabWidget.setTabText(self.__tabWidget.indexOf(self.__tab), text)

    def getText(self):
        return self.__tab.textEdit.toPlainText()

    def getHtml(self):
        return self.__tab.textEdit.toHtml()

    def setText(self, text):
        self.__tab.textEdit.safeSetText(text)
        self.setSaved(False)
        return text

    def getFile(self):
        return self.__tab.file

    def setFile(self, file):
        self.__tab.file = file
        return self.__tab.file

    def getCanSave(self):
        return self.__tab.canSave

    def setCanSave(self, b):
        self.__tab.canSave = b
        return b

    def getCanEdit(self):
        return self.__tab.canEdit

    def isReadOnly(self):
        return self.__tab.canEdit

    def setReadOnly(self, b):
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
        return self.__tabWidget.isSaved(self.__tab)

    def setSaved(self, b):
        self.__tabWidget.tabBar().setTabSaved(self.__tab, b)
        return b

    def size(self):
        return self.__tab.textEdit.textLen()

    def substr(self, region):
        return self.__tab.textEdit.toPlainText()[region.begin():region.end()]

    def insert(self, string, point=None):
        textEdit = self.__tab.textEdit
        cursor = textEdit.textCursor()
        if point is not None:
            line_index, char_index = point.x, point.y
            lines = textEdit.toPlainText().splitlines()
            abs_position = 0
            for i in range(line_index):
                abs_position += len(lines[i]) + 1
            cursor.setPosition(abs_position)
        else:
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        textEdit.safeSetText(string, cursor)
        textEdit.setTextCursor(cursor)
        self.setSaved(False)

    def erase(self, region):
        t = self.__tab.textEdit.toPlainText()
        self.__tab.textEdit.setPlainText(t[:region.begin()] + t[region.end():])

    def replace(self, region, string):
        t = self.__tab.textEdit.toPlainText()
        self.__tab.textEdit.setPlainText(t[:region.begin()] + string + t[region.end():])
        self.setSaved(False)

    def undo(self):
        self.__tab.textEdit.undo()
        self.setSaved(False)

    def redo(self):
        if self.__tab.textEdit.document().isRedoAvailable():
            self.__tab.textEdit.redo()
            self.setSaved(False)

    def cut(self):
        if self.__tab.textEdit.textCursor().hasSelection():
            self.__tab.textEdit.cut()
            self.setSaved(False)

    def copy(self):
        self.__tab.textEdit.copy()

    def paste(self):
        self.__tab.textEdit.paste()
        self.setSaved(False)

    def clearUndoRedoStacks(self):
        self.__tab.textEdit.document().clearUndoRedoStacks()

    def selectAll(self):
        self.__tab.textEdit.selectAll()

    def setSyntax(self, data=None, path=None):
        if path:
            data = self.api.loadSettings(path)
        if data:
            self.setHighlighter(data)

    def isDirty(self):
        return not self.__window.tabWidget.isSaved(self.__tab)

    def getTextSelection(self):
        return self.__tab.textEdit.textCursor().selectedText()

    def getTextCursor(self):
        return self.__tab.textEdit.textCursor()

    def setTextSelection(self, region):
        cursor = self.__tab.textEdit.textCursor()
        cursor.setPosition(region.begin())
        cursor.setPosition(region.end(), QtGui.QTextCursor.MoveMode.KeepAnchor)
        self.__tab.textEdit.setTextCursor(cursor)

    def getCompletePos(self):
        current_text = self.__tab.textEdit.document().toPlainText()
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
        for _type in hl:
            self.__tab.textEdit.highLighter.addHighlightingRule(_type, hl.get(_type))

    def setAddititionalHL(self, data):
        self.__tab.textEdit.highLighter.addHighlightingData(data)

    def rehighlite(self):
        QtCore.QMetaObject.invokeMethod(
            self.__tab.textEdit.highLighter, "rehighlight",
            QtCore.Qt.QueuedConnection
        )

    def setMmapHidden(self, b):
        if b:
            self.__tab.textEdit.minimapScrollArea.hide()
        else:
            self.__tab.textEdit.minimapScrollArea.show()

    def isMmapHidden(self):
        return self.__tab.textEdit.minimapScrollArea.isHidden()

    def initTagFile(self, path):
        if os.path.isfile(path):
            self.tagBase.addFile(path)

    def getTags(self, path):
        return self.tagBase.getTagsForFile(path)

    def addTag(self, path, tag):
        self.tagBase.addTag(path, tag)
        self.__tab.frame.addTag(tag)

    def removeTag(self, path=None, tag=None, show=False):
        if not path:
            path = self.getFile()
        self.tagBase.removeTag(path, tag)
        self.__tab.frame.removeTag(tag, show)

    def getTagFiles(self, tag):
        return self.tagBase.getFilesForTag(tag)

class Window:

    View = View
    Signals = Signals

    def __init__(self, api, id=None, views=None, activeView=None, qmwclass=None):
        self.api: VtAPI = api
        self.__mw: QtWidgets.QMainWindow = qmwclass
        if self.__mw:
             self.signals: VtAPI.Signals = VtAPI.Signals(self.__mw)
        self.__views = views or []
        self.__activeView = None
        self.model = QtWidgets.QFileSystemModel()
        self.__id = bytes(id or str(__import__("uuid").uuid4()), encoding="utf-8")
    
    def __eq__(self, value):
        return self.id == value.id

    @property
    def activeView(self): return self.__activeView

    @activeView.setter
    def activeView(self, view):
        self.__activeView = findMatch(list(self.__views), view)

    @property
    def id(self): return self.__id.decode()

    def newFile(self):
        self.__mw.addTab()
        return self.activeView

    def openFiles(self, files):
        self.runCommand({"command": "OpenFileCommand", "args": [files]})
    
    def saveFile(self, view=None, dlg=False):
        self.runCommand({"command": "SaveFileCommand", "kwargs": {"dlg": dlg}})
    
    @property
    def views(self):
        """Получает список вкладок"""
        return tuple(self.__views)
    
    def addView(self, view):
        for v in self.__views:
             if v == view:
                 return True
        self.__views.append(view)
        return True
    
    def delView(self, view):
        for v in self.__views:
             if v == view:
                 self.__views.remove(v)

    def state(self): return self.api.STATEFILE.get(self.id) or {}
    
    def icsetState(self, data):
        self.api.STATEFILE[self.id] = data
        return self.state()

    def plugins(self):
        if hasattr(self.__mw, "pl"):
            return self.__mw.pl.plugins

    def translate(self, text, trtype="Console"):
        return self.__mw.translate(trtype, text)

    def update(self):
        QtCore.QCoreApplication.processEvents()

    def setUpdatesEnabled(self, b):
        self.__mw.setUpdatesEnabled(b)

    def getTitle(self):
        return self.__mw.windowTitle()

    def setTitle(self, s):
        self.__mw.setWindowTitle(f"{s} - {self.api.appName()}")
        return self.getTitle()

    def focus(self, view):
        if view in self.views:
             self.__mw.tabWidget.setCurrentIndex(view.tabIndex())
             self.activeView = view
             self.setTitle(os.path.normpath(self.activeView.getFile() or 'Untitled'))
             return True
        return False

    def resizeDock(self, dock, w, h=None):
        self.__mw.resizeDocks([dock], [w], QtCore.Qt.Horizontal)
        if h:
            self.__mw.resizeDocks([dock], [h], QtCore.Qt.Vertical)

    def registerCommandClass(self, data):
        if hasattr(self.__mw, "pl"):
            self.__mw.pl.registerClass(data)

    def registerCommand(self, data):
        if hasattr(self.__mw, "pl"):
            self.__mw.pl.registerCommand(data)

    def runCommand(self, command):
        if hasattr(self.__mw, "pl"):
            self.__mw.pl.executeCommand(command)

    def getCommand(self, name):
        if hasattr(self.__mw, "pl"):
            return self.__mw.pl.regCommands.get(name)

    def getTheme(self):
        return self.__mw.themeFile

    def setTheme(self, theme):
        if os.path.isfile(theme):
             with open(theme, "r", encoding="utf-8") as theme_file:
                 self.__mw.setStyleSheet(theme_file.read())
             self.__mw.themeFile = theme

    def getLocale(self):
        return self.__mw.locale

    def setLocale(self, s, auto=False):
        if auto: locale = self.__mw.defineLocale()
        else: locale = s
        self.__mw.locale = locale
        return locale

    def getLog(self):
        return self.__mw.logger.log

    def setLogMsg(self, msg, t=None):
        msg = f"""<i style="color: {t.value if t else ""};">{html.escape(str(msg))}</i>"""
        self.__mw.logger.log += f"<br>{time.strftime('[%H:%M:%S %d %b];', time.localtime())}: {msg}"

    def setTab(self, i):
        self.__mw.tabWidget.setCurrentIndex(i - 1)

    def splitterData(self):
        return self.__mw.treeSplitter.saveState().data()

    def restoreSplitter(self, data):
        self.__mw.treeSplitter.restoreState(data)

    def isTabsMovable(self):
        return self.__mw.tabWidget.tabBar().isMovable()

    def isTabsClosable(self):
        return self.__mw.tabWidget.tabBar().tabsClosable()

    def setTabsMovable(self, b):
        return self.__mw.tabWidget.tabBar().setMovable(b)

    def setTabsClosable(self, b):
        return self.__mw.tabWidget.tabBar().setTabsClosable(b)

    def updateMenu(self, menu, data):
        menuClass = self.__mw.pl.findMenu(self.__mw.menuBar(), menu)
        if menuClass:
             self.__mw.pl.clearMenu(self.__mw.menuBar(), menu)
             self.__mw.pl.parseMenu(data, menuClass, regc=False)

    def addToolBar(self, items, flags=[]):
        toolBar = QtWidgets.QToolBar()
        for action in items:
             if isinstance(action, QtGui.QAction) or isinstance(action, VtAPI.Widgets.Action):
                 toolBar.addAction(action)
        self.__mw.addToolBar(toolBar)

    def addDockWidget(self, areas, dock):
       self.__mw.addDockWidget(areas, dock)

    def showDialog(self, content, flags=[], location=-1, width=320, height=240, on_hide=None):
        dialog = VtAPI.Widgets.Dialog(parent=self.__mw)
        dialog.setWindowTitle(self.api.appName())
        if flags:
             dialog.setWindowFlags(flags)
        dialog.setFixedWidth(width)
        dialog.setFixedHeight(height)

        dialog.setLayout(content)
        dialog.exec()
    
    def isDockWidget(self, area):
        dock_widgets = self.__mw.findChildren(QtWidgets.QDockWidget)
        for dock in dock_widgets:
             if self.__mw.dockWidgetArea(dock) == area: return dock

    def statusMessage(self, text, timeout=0):
        self.__mw.statusbar.showStatusMessage(text, timeout)

class VtAPI:


    Color = Color
    Window = Window
    View = View
    Signals = Signals
    Plugin = Plugin
    File = File
    Theme = Theme
    Settings = Settings
    Dialogs = Dialogs
    Widgets = Widgets
    Path = Path
    Point = Point
    Region = Region
    Selection = Selection

    def __init__(self, app=None):
        if app is None:
             self.__app = QtWidgets.QApplication.instance()
        else:
             self.__app = app
        
        self.__windows = []
        self.__appName = "VT2"
        self.__activeWindow = None
        self.STATEFILE = {}
        self.__CLOSINGSTATEFILE = {}

        self.themesDir = ""  # Инициализация атрибутов
        self.packagesDir = ""
        self.uiDir = ""
        self.pluginsDir = ""
        self.cacheDir = ""
    @property
    def CLOSINGSTATEFILE(self):
        return self.__CLOSINGSTATEFILE

    def appName(self):
        return self.__appName

    def setAppName(self, appName):
        self.__appName = appName
    def setFolder(self, folder_type, value):
        if folder_type == "themes":
             self.themesDir = value
        elif folder_type == "packages":
             self.packagesDir = value
        elif folder_type == "ui":
             self.uiDir = value
        elif folder_type == "plugins":
             self.pluginsDir = value
        elif folder_type == "cache":
             self.cacheDir = value
        else:
             raise ValueError(f"Unknown folder type: {folder_type}")

    def getFolder(self, folder_type):
        if folder_type == "themes":
             return self.themesDir
        elif folder_type == "packages":
             return self.packagesDir
        elif folder_type == "ui":
             return self.uiDir
        elif folder_type == "plugins":
             return self.pluginsDir
        elif folder_type == "cache":
             return self.cacheDir
        else:
             raise ValueError(f"Unknown folder type: {folder_type}")

    @property
    def activeWindow(self):
        return self.__activeWindow

    @activeWindow.setter
    def activeWindow(self, w):
        self.__activeWindow = w

    @property
    def windows(self):
        return tuple(self.__windows)

    def addWindow(self, window):
        self.__windows.append(window)

    @staticmethod
    def isDir(path): return os.path.isdir(path)

    @staticmethod
    def importModule(name):
        return importModule(name)

    @staticmethod
    def setTimeout(function, delay):
        QtCore.QTimer.singleShot(delay, function)

    @staticmethod
    async def setTimeout_async(function, delay):
        await asyncio.sleep(delay)
        function()

    @staticmethod
    def version():
        return version()

    @staticmethod
    def platform():
        return getPlatform()

    @staticmethod
    def arch():
        return arch()

    @staticmethod
    def findKey(p, d):
        return findKey(p, d)

    @staticmethod
    def addKey(p, value, d):
        addKey(p, value, d)

    @staticmethod
    def replacePaths(data):
        return _replace_var(data)

    @staticmethod
    def defineLocale():
        return QtCore.QLocale.system().name().split("_")[0]

    def packagesPath(self):
        return self.packagesDir
