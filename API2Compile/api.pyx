from enum import Enum
from PySide6 import QtWidgets, QtCore, QtGui
from typing import *
import os, sys, json, importlib, re, platform, asyncio, time, functools
import importlib.util
import inspect

cimport cython

cdef object findMatch(list lst, object obj):
    return [i for i in lst if i == obj][0]

cdef public str _replace_var(str data):
    cdef match
    def replace_var(match):
        env_var = match.group(1)
        return os.getenv(env_var, f'%{env_var}%')
    return re.sub(r'%([^%]+)%', replace_var, data)

cdef public findKey(str p, dict d):
    cdef object current = d
    cdef list path = p.split(".")
    cdef str key
    for key in path:
        if isinstance(current, dict) and key in current:
             current = current[key]
        else:
             return None
    return current

cdef public addKey(str p, object value, dict d):
    cdef list path = p.split(".")
    cdef object current = d
    cdef str key
    for key in path[:-1]:
        if key not in current or not isinstance(current[key], dict):
             current[key] = {}
        current = current[key]
    current[path[-1]] = value

cdef public object importModule(str name):
    return importlib.import_module(name)

cdef public void setTimeout(function, int delay):
    QtCore.QTimer.singleShot(delay, function)

cdef public str version():
    return "1.3"

cdef public str getPlatform():
    cdef str current_platform = platform.system()
    if current_platform == "Darwin":
        return "OSX"
    return current_platform

cdef public str arch():
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

cdef class Selection:
    cdef list regions
    def __cinit__(self, regions=None):
        self.regions = regions or []

    cpdef void clear(self):
        self.regions = []
    
    cpdef void add(self, object region):
        self.regions.append(region)
    
    cpdef void subtract(self, object region):
        self.regions = [r for r in self.regions if r != region]
    
    cpdef cython.bint contains(self, object point):
        for region in self.regions:
            if region.contains(point):
                return True
        return False

    cpdef str text(self, object view, object region):
        return view.__tab.toPlainText()[region.begin():region.end()]

cdef class Region:
    cdef int a
    cdef int b
    def __cinit__(self, int a, int b):
        self.a = a
        self.b = b
    
    cpdef int begin(self):
        return min(self.a, self.b)
    
    cpdef int end(self):
        return max(self.a, self.b)
    
    cpdef cython.bint contains(self, int point):
        return self.begin() <= point <= self.end()

cdef class Settings:
    cdef settings
    def __cinit__(self, settings=None):
        self.settings = settings or {}
    
    cpdef data(self):
        return self.settings

    cpdef get(self, str key, str default=None):
        return self.settings.get(key, default)
    
    cpdef set(self, str key, str value):
        self.settings[key] = value
    
    cpdef erase(self, str key):
        if key in self.settings:
            del self.settings[key]
    
    cpdef has(self, key):
        return key in self.settings
    
    @classmethod
    def fromFile(cls, f: "VtAPI.File"):
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

cdef class Path:
    cdef str path
    def __cinit__(self, path: str = None, encoding="utf-8"):
        self.path = path

    def __str__(self):
        return self.path

    cpdef cython.bint exists(self):
        return os.path.exists(self.path)
    
    cpdef cython.bint isFile(self):
        return os.path.isfile(self.path)
    
    cpdef cython.bint isDir(self):
        return os.path.isdir(self.path)
    
    def joinPath(*args):
        return os.path.join(*args)
    
    cpdef str dirName(self):
        return os.path.dirname(self.path)
    
    cpdef void chdir(path):
        os.chdir(path)
    
    cpdef void create(self):
        os.makedirs(self.path)
    
    cpdef str normalize(self):
        return os.path.normpath(self.path)
    
    cpdef list dir(self):
        return os.listdir(self.path)
    
    cpdef void remove(self):
        os.remove(self.path)

cdef class File:
    cdef str path
    cdef str encoding
    cdef str mode

    def __init__(self, path: str = None, encoding="utf-8"):
        self.path = path
        self.encoding = encoding

    def __str__(self):
        return self.path

    cpdef list read(self, chunk=1024):
        cdef list lines = []
        if self.encoding == "binary":
            self.mode = "rb"
        else:
            self.mode = "r"
        if self.exists() and not os.path.isdir(self.path):
            with open(self.path, self.mode, encoding=None if self.mode == "rb" else self.encoding, errors="ignore") as file:
                while True:
                    chunk_data = file.read(chunk)
                    if not chunk_data:
                        break
                    lines.append(chunk_data)
        return lines

    cpdef void write(self, content, chunk=1024):
        cdef int total_length = len(content)
        with open(self.path, 'w', encoding=self.encoding) as file:
            for i in range(0, total_length, chunk):
                chunkk = content[i:i + chunk]
                file.write(str(chunkk))

    cpdef bint exists(self):
        return os.path.isfile(self.path)

    cpdef void create(self, rewrite=False):
        if rewrite:
            open(self.path, "a+", encoding=self.encoding).close()
        elif not self.exists():
            open(self.path, "a", encoding=self.encoding).close()

cdef class Theme:
    cdef str name
    cdef str path

    def __init__(self, name: str = None, path: str = None):
        self.name = name
        self.path = path

    def __str__(self):
        return self.path

    cpdef void use(self, window: "VtAPI.Window" = None):
        window.setTheme(self.path)

    cpdef bint exists(self):
        return os.path.isfile(self.path)

class Plugin:
    def __init__(self, api, name: str, path: str):
        self.api = api  # Оставляем без аннотации типа
        self.name = name
        self.path = path

    def __str__(self) -> str:
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

cdef class Point:
    cdef int x
    cdef int y
    def __cinit__(self, x=0, y=0):
        """Инициализация точки с координатами x и y."""
        self.x = x
        self.y = y

    cpdef move(self, dx, dy):
        """Перемещение точки на (dx, dy)."""
        self.x += dx
        self.y += dy

    cpdef distance_to(self, other):
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

    def addSignal(self, signalName: str, signal):
        if not signalName in self._signals: self._signals[signalName] = signal
        else: raise self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Signals already has signal '{}'".format(signalName)))

    def deleteSignal(self, signalName: str):
        if signalName in self._signals: self._signals.pop(signalName)

    def findSignal(self, signalName: str):
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

cdef class View:
    cdef readonly object api
    cdef readonly object __window
    cdef readonly object __tab
    cdef readonly str __id
    cdef readonly object __tabWidget
    cdef readonly object tagBase

    def __cinit__(self, api, window, qwclass=None, id=None):
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
   
    cpdef str id(self):
       return self.__id

    def __hash__(self):
        return hash(self.tabIndex())

    cpdef int tabIndex(self):
        return self.__tabWidget.indexOf(self.__tab)

    cpdef void close(self):
        self.__tabWidget.closeTab(self.__tab)

    cpdef object window(self):
        return self.__window

    cpdef void focus(self):
        self.window.focus(self)
        self.__tab.textEdit.setFocus()

    cpdef str getTitle(self):
        return self.__tabWidget.tabText(self.__tabWidget.indexOf(self.__tab))

    cpdef void setTitle(self, str text):
        self.__tabWidget.setTabText(self.__tabWidget.indexOf(self.__tab), text)

    cpdef str getText(self):
        return self.__tab.textEdit.toPlainText()

    cpdef str getHtml(self):
        return self.__tab.textEdit.toHtml()

    cpdef str setText(self, str text):
        self.__tab.textEdit.safeSetText(text)
        self.setSaved(False)
        return text

    cpdef object getFile(self):
        return self.__tab.file

    cpdef object setFile(self, object file):
        self.__tab.file = file
        return self.__tab.file

    cpdef cython.bint getCanSave(self):
        return self.__tab.canSave

    cpdef cython.bint setCanSave(self, cython.bint b):
        self.__tab.canSave = b
        return b

    cpdef cython.bint getCanEdit(self):
        return self.__tab.canEdit

    cpdef cython.bint isReadOnly(self):
        return self.__tab.canEdit

    cpdef cython.bint setReadOnly(self, cython.bint b):
        self.__tab.canEdit = b
        self.__tab.textEdit.setReadOnly(b)
        self.__tab.textEdit.setDisabled(b)
        return b

    cpdef str getEncoding(self):
        return self.__tab.encoding

    cpdef str setEncoding(self, str enc):
        self.__tab.encoding = enc
        return enc

    cpdef cython.bint getSaved(self):
        return self.__tabWidget.isSaved(self.__tab)

    cpdef cython.bint setSaved(self, cython.bint b):
        self.__tabWidget.tabBar().setTabSaved(self.__tab, b)
        return b

    cpdef int size(self):
        return self.__tab.textEdit.textLen()

    cpdef str substr(self, object region):
        return self.__tab.textEdit.toPlainText()[region.begin():region.end()]

    cpdef void insert(self, str string, object point=None):
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

    cpdef void erase(self, object region):
        t = self.__tab.textEdit.toPlainText()
        self.__tab.textEdit.setPlainText(t[:region.begin()] + t[region.end():])

    cpdef void replace(self, object region, str string):
        t = self.__tab.textEdit.toPlainText()
        self.__tab.textEdit.setPlainText(t[:region.begin()] + string + t[region.end():])
        self.setSaved(False)

    cpdef void undo(self):
        self.__tab.textEdit.undo()
        self.setSaved(False)

    cpdef void redo(self):
        if self.__tab.textEdit.document().isRedoAvailable():
            self.__tab.textEdit.redo()
            self.setSaved(False)

    cpdef void cut(self):
        if self.__tab.textEdit.document().isUndoAvailable():
            self.__tab.textEdit.cut()
            self.setSaved(False)

    cpdef void copy(self):
        self.__tab.textEdit.copy()

    cpdef void paste(self):
        self.__tab.textEdit.paste()
        self.setSaved(False)

    cpdef void clearUndoRedoStacks(self):
        self.__tab.textEdit.document().clearUndoRedoStacks()

    cpdef void selectAll(self):
        self.__tab.textEdit.selectAll()

    cpdef void setSyntax(self, data=None, path=None):
        if path:
            data = self.api.loadSettings(path)
        if data:
            self.setHighlighter(data)

    cpdef cython.bint isDirty(self):
        return self.__window.tabWidget.isSaved(self.__tab)

    cpdef str getTextSelection(self):
        return self.__tab.textEdit.textCursor().selectedText()

    cpdef object getTextCursor(self):
        return self.__tab.textEdit.textCursor()

    cpdef void setTextSelection(self, object region):
        cursor = self.__tab.textEdit.textCursor()
        cursor.setPosition(region.begin())
        cursor.setPosition(region.end(), QtGui.QTextCursor.MoveMode.KeepAnchor)
        self.__tab.textEdit.setTextCursor(cursor)

    cpdef tuple getCompletePos(self):
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

    cpdef void setCompleteList(self, list lst):
        self.completer = self.__tab.textEdit.completer.updateCompletions(lst)

    cpdef void setHighlighter(self, dict hl):
        for _type in hl:
            self.__tab.textEdit.highLighter.addHighlightingRule(_type, hl.get(_type))

    cpdef void setAddititionalHL(self, data):
        self.__tab.textEdit.highLighter.addHighlightingData(data)

    cpdef void rehighlite(self):
        QtCore.QMetaObject.invokeMethod(
            self.__tab.textEdit.highLighter, "rehighlight",
            QtCore.Qt.QueuedConnection
        )

    cpdef void setMmapHidden(self, cython.bint b):
        if b:
            self.__tab.textEdit.minimapScrollArea.hide()
        else:
            self.__tab.textEdit.minimapScrollArea.show()

    cpdef cython.bint isMmapHidden(self):
        return self.__tab.textEdit.minimapScrollArea.isHidden()

    cpdef void initTagFile(self, str path):
        if os.path.isfile(path):
            self.tagBase.addFile(path)

    cpdef list getTags(self, str path):
        return self.tagBase.getTagsForFile(path)

    cpdef void addTag(self, str path, str tag):
        self.tagBase.addTag(path, tag)
        self.__tab.frame.addTag(tag)

    cpdef void removeTag(self, str path=None, str tag=None, cython.bint show=False):
        if not path:
            path = self.getFile()
        self.tagBase.removeTag(path, tag)
        self.__tab.frame.removeTag(tag, show)

    cpdef list getTagFiles(self, str tag):
        return self.tagBase.getFilesForTag(tag)

cdef class Window:
    cdef readonly VtAPI api
    cdef readonly object __mw
    cdef readonly object signals
    cdef list __views
    cdef object __activeView
    cdef object model
    cdef readonly bytes __id

    View = View
    Signals = Signals

    def __cinit__(self, api: "VtAPI", id: Optional[str] = None, views: Optional[List['VtAPI.View']] = None, activeView: Optional['VtAPI.View'] = None, qmwclass: Optional[QtWidgets.QMainWindow] = None):
        self.api: VtAPI = api
        self.__mw: QtWidgets.QMainWindow = qmwclass
        if self.__mw:
             self.signals: VtAPI.Signals = VtAPI.Signals(self.__mw)
        self.__views = views or []
        self.__activeView = None
        self.model = QtWidgets.QFileSystemModel()
        self.__id = bytes(id, encoding="utf-8")
    
    def __eq__(self, value):
        return self.id == value.id

    @property
    def activeView(self): return self.__activeView

    @activeView.setter
    def activeView(self, view: 'VtAPI.View') -> Optional['VtAPI.View']:
        self.__activeView = [findMatch(self.__views, view) if findMatch(list(self.__views), view) else ""][0]

    @property
    def id(self): return self.__id.decode()

    cpdef object newFile(self):
        self.__mw.addTab()
        return self.activeView

    cpdef void openFiles(self, files: List[str]):
        self.runCommand({"command": "OpenFileCommand", "args": [files]})
    
    cpdef void saveFile(self, view: Optional['VtAPI.View'] = None, dlg: cython.bint = False):
        self.runCommand({"command": "SaveFileCommand", "kwargs": {"dlg": dlg}})
    
    @property
    def views(self) -> Tuple['VtAPI.View']:
        """Получает список вкладок"""
        return tuple(self.__views)
    
    cpdef cython.bint addView(self, view: 'VtAPI.View'):
        for v in self.__views:
             if v == view:
                 return True
        self.__views.append(view)
        return True
    
    cpdef void delView(self, view: 'VtAPI.View'):
        for v in self.__views:
             if v == view:
                 self.__views.remove(v)

    cpdef dict state(self): return self.api.STATEFILE.get(self.id) or {}
    
    cpdef dict icsetState(self, dict data):
        self.api.STATEFILE[self.id] = data
        return self.state()

    cpdef dict plugins(self):
        if hasattr(self.__mw, "pl"):
            return self.__mw.pl.plugins

    cpdef str translate(self, str text, str trtype="Console"):
        return self.__mw.translate(trtype, text)

    cpdef void update(self):
        QtCore.QCoreApplication.processEvents()

    cpdef void setUpdatesEnabled(self, cython.bint b):
        self.__mw.setUpdatesEnabled(b)

    cpdef str getTitle(self):
        return self.__mw.windowTitle()

    cpdef str setTitle(self, str s):
        self.__mw.setWindowTitle(f"{s} - {self.api.__appName}")
        return self.getTitle()

    cpdef cython.bint focus(self, object view):
        if view in self.views:
             self.__mw.tabWidget.setCurrentIndex(view.tabIndex())
             self.activeView = view
             self.setTitle(os.path.normpath(self.activeView.getFile() or 'Untitled'))
             return True
        return False

    cpdef void resizeDock(self, object dock, int w, h=None):
        self.__mw.resizeDocks([dock], [w], QtCore.Qt.Horizontal)
        if h:
            self.__mw.resizeDocks([dock], [h], QtCore.Qt.Vertical)

    cpdef void registerCommandClass(self, dict data):
        if hasattr(self.__mw, "pl"):
            self.__mw.pl.registerClass(data)

    cpdef void registerCommand(self, dict data):
        if hasattr(self.__mw, "pl"):
            self.__mw.pl.registerCommand(data)

    cpdef void runCommand(self, dict command):
        if hasattr(self.__mw, "pl"):
            self.__mw.pl.executeCommand(command)

    cpdef dict getCommand(self, str name):
        if hasattr(self.__mw, "pl"):
            return self.__mw.pl.regCommands.get(name)

    cpdef str getTheme(self):
        return self.__mw.themeFile

    cpdef void setTheme(self, str theme):
        if os.path.isfile(theme):
             self.__mw.setStyleSheet(open(theme, "r+").read())
             self.__mw.themeFile = theme

    cpdef str getLocale(self):
        return self.__mw.locale

    cpdef str setLocale(self, s: str, auto=False):
        if auto: locale = self.__mw.defineLocale()
        else: locale = s
        self.__mw.locale = locale
        return locale

    cpdef str getLog(self):
        return self.__mw.logger.log

    cpdef void setLogMsg(self, msg, t: "VtAPI.Color" = None):
        msg = f"""<i style="color: {t.value if t else ""};">{msg}</i>"""
        self.__mw.logger.log += f"<br>{time.strftime('[%H:%M:%S %d %b];', time.localtime())}: {msg}"

    cpdef void setTab(self, int i):
        self.__mw.tabWidget.setCurrentIndex(i - 1)

    cpdef dict splitterData(self):
        return self.__mw.treeSplitter.saveState().data()

    cpdef void restoreSplitter(self, dict data):
        self.__mw.treeSplitter.restoreState(data)

    cpdef cython.bint isTabsMovable(self):
        return self.__mw.tabWidget.tabBar().isMovable()

    cpdef cython.bint isTabsClosable(self):
        return self.__mw.tabWidget.tabBar().tabsClosable()

    cpdef cython.bint setTabsMovable(self, cython.bint b):
        return self.__mw.tabWidget.tabBar().setMovable(b)

    cpdef cython.bint setTabsClosable(self, cython.bint b):
        return self.__mw.tabWidget.tabBar().setTabsClosable(b)

    cpdef void updateMenu(self, str menu, data):
        cdef object menuClass = self.__mw.pl.findMenu(self.__mw.menuBar(), menu)
        if menuClass:
             self.__mw.pl.clearMenu(self.__mw.menuBar(), menu)
             self.__mw.pl.parseMenu(data, menuClass, regc=False)

    cpdef void addToolBar(self, list items, list flags=[]):
        toolBar = QtWidgets.QToolBar()
        for action in items:
             if isinstance(action, QtGui.QAction) or isinstance(action, VtAPI.Widgets.Action):
                 toolBar.addAction(action)
        self.__mw.addToolBar(toolBar)

    cpdef void addDockWidget(self, areas, dock: 'VtAPI.Widgets.DockWidget'):
       self.__mw.addDockWidget(areas, dock)

    cpdef void showDialog(self, object content, list flags=[], int location=-1, int width=320, int height=240, on_hide=None):
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

cdef class VtAPI:
    cdef object __app
    cdef list __windows
    cdef object __activeWindow
    cdef dict STATEFILE
    cdef dict __CLOSINGSTATEFILE

    cdef str __appName
    cdef str themesDir
    cdef str packagesDir
    cdef str uiDir
    cdef str pluginsDir
    cdef str cacheDir

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

    def __cinit__(self, app=None):
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
    cpdef setFolder(self, str folder_type, str value):
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

    cpdef getFolder(self, folder_type: str):
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
    def activeWindow(self) -> Window:
        return self.__activeWindow

    @activeWindow.setter
    def activeWindow(self, w: Window):
        self.__activeWindow = w

    @property
    def windows(self):
        return tuple(self.__windows)

    def addWindow(self, window: Window):
        self.__windows.append(window)

    @staticmethod
    def isDir(path): return os.path.isdir(path)

    @staticmethod
    def importModule(str name):
        return importModule(name)

    @staticmethod
    def setTimeout(function, int delay):
        QtCore.QTimer.singleShot(delay, function)

    @staticmethod
    async def setTimeout_async(function, int delay):
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
    def findKey(str p, dict d):
        return findKey(p, d)

    @staticmethod
    def addKey(str p, value, dict d):
        addKey(p, value, d)

    @staticmethod
    def replacePaths(str data):
        return _replace_var(data)

    @staticmethod
    def defineLocale():
        return QtCore.QLocale.system().name().split("_")[0]

    cpdef packagesPath(self):
        return self.packagesDir