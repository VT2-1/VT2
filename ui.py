import sys, json, os, uuid

from PyQt6 import QtCore, QtWidgets
from datetime import datetime
import msgpack, io

from addit import *
from api2 import PluginManager, VtAPI

class Logger:
    def __init__(self, window):
        self._log = ""
        self.__window = window
        
        self._stdout_backup = sys.stdout
        self._log_stream = io.StringIO()
        sys.stdout = self

    @property
    def log(self):
        return self._log

    @log.setter
    def log(self, value):
        self._log = value
        self.__window.api.activeWindow.signals.logWrited.emit(value)

    def write(self, message):
        if message:
            if self.__window.logStdout:
                self.__window.api.activeWindow.setLogMsg(f"stdout: {message}")
                self.__window.api.activeWindow.signals.logWrited.emit(message)
            self._stdout_backup.write(message)

    def flush(self):
        pass

    def close(self):
        sys.stdout = self._stdout_backup
        self._log_stream.close()

class Ui_MainWindow(object):
    sys.path.insert(0, ".")

    def setupUi(self, MainWindow, argv=[], api=None):
        self.MainWindow: QtWidgets.QMainWindow = MainWindow
        self.appPath = os.path.basename(__file__)
        self.appPath = os.path.dirname(argv[0])
        self.themeFile = ""
        self.localeDirs = []
        self.api: VtAPI = api
        self.settings()

        self.MainWindow.setFocus()
        self.MainWindow.setObjectName("MainWindow")
        self.MainWindow.resize(800, 600)

        self.console = None

        self.translator = QtCore.QTranslator()

        self.centralwidget = QtWidgets.QWidget(parent=self.MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.treeView = QtWidgets.QTreeView(parent=self.centralwidget)
        self.treeView.setMinimumWidth(150)
        self.treeView.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        self.treeView.setMaximumWidth(300)
        self.treeView.setObjectName("treeWidget")

        self.treeSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.horizontalLayout.addWidget(self.treeSplitter)

        self.tabWidget = TabWidget(parent=self.centralwidget, MainWindow=self.MainWindow)
        self.treeSplitter.addWidget(self.treeView)
        self.treeSplitter.addWidget(self.tabWidget)

        self.MainWindow.setCentralWidget(self.centralwidget)

        self.menubar = QtWidgets.QMenuBar(parent=self.MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 21))
        self.menubar.setObjectName("menuBar")

        self.MainWindow.setMenuBar(self.menubar)

        self.encodingLabel = QtWidgets.QLabel("UTF-8")
        self.encodingLabel.setObjectName("encodingLabel")
        self.statusbar = QtWidgets.QStatusBar(parent=self.MainWindow)
        self.statusbar.setObjectName("statusbar")
        self.statusbar.addPermanentWidget(self.encodingLabel)
        self.MainWindow.setStatusBar(self.statusbar)

        self.tagBase = TagDB(os.path.join(self.api.packagesDirs, ".ft"))
        self.logger = self.MainWindow.logger

        QtCore.QMetaObject.connectSlotsByName(self.MainWindow)

    def addTab(self, name: str = "", text: str = "", i: int = -1, file=None, canSave=True, canEdit=True, encoding="UTF-8"):
        self.tab = QtWidgets.QWidget()
        self.tab.file = file
        self.tab.canSave = canSave
        self.tab.canEdit = canEdit
        self.tabWidget.tabBar().setTabSaved(self.tab, True)
        self.tab.encoding = encoding
        self.tab.setObjectName(f"tab-{uuid.uuid4()}")

        self.verticalLayout = QtWidgets.QVBoxLayout(self.tab)
        self.verticalLayout.setObjectName("verticalLayout")

        self.tab.frame = TagContainer(parent=self.tab, api=self.api)
        self.tab.frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.tab.frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.tab.frame.setObjectName("tabFrame")
        self.verticalLayout.addWidget(self.tab.frame)

        self.tab.textEdit = TextEdit(self.MainWindow)
        self.tab.textEdit.setReadOnly(False)

        self.tab.textEdit.safeSetText(text)
        self.tab.textEdit.setObjectName("textEdit")

        self.verticalLayout.addLayout(self.tab.textEdit.layout)

        newView = self.api.View(self.api, self.api.activeWindow, qwclass=self.tab)
        self.api.activeWindow.views.append(newView)

        self.tabWidget.addTab(self.tab, "")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), name or "Untitled")
        self.api.activeWindow.setTab(-1)

        self.api.activeWindow.focus(newView)

        self.api.activeWindow.signals.tabCreated.emit()

    def getCommand(self, name):
        return getattr(sys.modules[__name__], name, None)

    def defineLocale(self):
        return QtCore.QLocale.system().name().split("_")[0]

    def translate(self, d):
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, f"{self.locale}.vt-locale")):
            if self.translator.load(os.path.join(d, f"{self.locale}.vt-locale")):
                QtCore.QCoreApplication.installTranslator(self.translator)

    def settings(self):
        try:
            self.settFile = open(os.path.join(self.appPath, 'ui/Main.settings'), 'r+', encoding='utf-8')
            self.settData = json.load(self.settFile)
        except:
            self.settData = {}
            self.api.activeWindow.setLogMsg("Error reading settings. Check /ui/Main.settings file", self.api.ERROR)
        self.api.packagesDirs = self.settData.get("packageDirs") or "./Packages/"
        if type(self.api.packagesDirs) == dict:
            self.api.packagesDirs = self.api.replacePaths(self.api.packagesDirs.get(self.api.platform()))
        self.api.themesDir = self.api.replacePaths(os.path.join(self.api.packagesDirs, "Themes"))
        self.api.pluginsDir = self.api.replacePaths(os.path.join(self.api.packagesDirs, "Plugins"))
        self.api.uiDir = self.api.replacePaths(os.path.join(self.api.packagesDirs, "Ui"))
        self.api.cacheDir = self.api.replacePaths(os.path.join(self.api.packagesDirs, "cache"))
        for d in [self.api.packagesDirs, self.api.themesDir, self.api.pluginsDir, self.api.uiDir, self.api.cacheDir]:
            if not os.path.isdir(d): os.makedirs(d)
        self.api.appName = self.settData.get("appName") or "VT2"
        self.api.__version__ = self.settData.get("apiVersion") or "1.0"
        self.MainWindow.logStdout = self.settData.get("logStdout") or False
        self.saveState = self.settData.get("saveState") or True
        self.MainWindow.remindOnClose = self.settData.get("remindOnClose")
        self.themeFile = ""
        if self.settData.get("menu"): self.menuFile = self.api.replacePaths(os.path.join(self.api.packagesDirs, self.settData.get("menu")))
        else: self.menuFile = None
        os.chdir(self.api.packagesDirs)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        openFile = self.api.getCommand("OpenFileCommand")
        if openFile:
            self.api.activeWindow.runCommand({"command": "OpenFileCommand", "kwargs": {"f": files}})
        else:
            QtWidgets.QMessageBox.warning(self.MainWindow, self.MainWindow.appName + " - Warning", f"Open file function not found. Check your Open&Save plugin at {os.path.join(self.api.pluginsDir, 'Open&Save')}")

    def closeEvent(self, e: QtCore.QEvent):
        if self.saveState: self.saveWState()
        self.api.activeWindow.signals.windowClosed.emit()

        e.accept()

    def windowInitialize(self):
        [os.makedirs(dir) for dir in [self.api.themesDir, self.api.pluginsDir, self.api.uiDir] if not os.path.isdir(dir)]
        self.tabLog = {}
        stateFile = os.path.join(self.api.packagesDirs, '.ws')
        self.MainWindow.setWindowTitle(self.api.appName)
        try:
            if os.path.isfile(stateFile):
                with open(stateFile, 'rb') as f:
                    packed_data = f.read()
                    self.tabLog = msgpack.unpackb(packed_data, raw=False)
                    self.api.STATEFILE = self.tabLog
        except ValueError:
            self.logger.log += f"\nFailed to restore window state. No file found at {stateFile}"  
            self.tabLog = {}
        if self.api.findKey("settings.themeFile", self.api.STATEFILE): self.themeFile = self.api.findKey("settings.themeFile", self.api.STATEFILE)
        if self.api.findKey("settings.locale", self.api.STATEFILE): self.locale = self.api.findKey("settings.locale", self.api.STATEFILE)
        else: self.locale = self.api.findKey("settings.locale", self.api.STATEFILE)
        if self.locale == "auto" or not self.locale:
            self.locale = self.defineLocale()
        # self.locale = "ru" # Проверка ./locale/
        self.api.activeWindow.setTheme(self.themeFile)

    def restoreWState(self):
        for idx, tab in enumerate(self.api.findKey("state.tabWidget.tabs", self.api.STATEFILE) or []):
            tab = self.api.findKey(f"state.tabWidget.tabs.{str(idx)}", self.api.STATEFILE)
            self.addTab()
            self.api.activeWindow.activeView.setTitle(self.api.findKey(f"state.tabWidget.tabs.{str(idx)}.name", self.api.STATEFILE))
            self.api.activeWindow.activeView.setFile(self.api.findKey(f"state.tabWidget.tabs.{str(idx)}.file", self.api.STATEFILE))
            self.api.activeWindow.activeView.setText(self.api.findKey(f"state.tabWidget.tabs.{str(idx)}.text", self.api.STATEFILE))
            self.api.activeWindow.activeView.setCanSave(self.api.findKey(f"state.tabWidget.tabs.{str(idx)}.canSave", self.api.STATEFILE))
            self.api.activeWindow.activeView.setSaved(self.api.findKey(f"state.tabWidget.tabs.{str(idx)}.isSaved", self.api.STATEFILE))
            self.api.activeWindow.setTitle(os.path.normpath(self.api.activeWindow.activeView.getFile() or 'Untitled'))
            self.api.activeWindow.activeView.setTextSelection(self.api.findKey(f"state.tabWidget.tabs.{str(idx)}.selection", self.api.STATEFILE)[0], self.api.findKey(f"state.tabWidget.tabs.{str(idx)}.selection", self.api.STATEFILE)[1])
            self.api.activeWindow.activeView.setMmapHidden(self.api.findKey(f"state.tabWidget.tabs.{str(idx)}.mmapHidden", self.api.STATEFILE) or 0)
            if self.api.activeWindow.activeView.getFile(): self.api.activeWindow.signals.fileOpened.emit(self.api.activeWindow.activeView)
        self.api.activeWindow.setTreeWidgetDir(self.api.findKey("state.treeWidget.openedDir", self.api.STATEFILE) or "/")
        if self.api.findKey("state.tabWidget.activeTab", self.api.STATEFILE):
            self.tabWidget.setCurrentIndex(int(self.api.findKey("state.tabWidget.activeTab", self.api.STATEFILE)))
        if self.api.findKey(f"state.splitter.data", self.api.STATEFILE): self.treeSplitter.restoreState(self.api.findKey(f"state.splitter.data", self.api.STATEFILE))
        self.tabWidget.tabBar().setMovable(self.api.findKey("state.tabWidget.tabBar.movable", self.api.STATEFILE) or 1)
        self.tabWidget.tabBar().setTabsClosable(self.api.findKey("state.tabWidget.tabBar.closable", self.api.STATEFILE) or 1)
        self.api.activeWindow.signals.windowStateRestoring.emit()

    def saveWState(self):
        stateDict = {}
        self.api.STATEFILE = stateDict
        tabWidgetTabsState = {}
        self.api.addKey("settings.themeFile", self.themeFile, self.api.STATEFILE)
        self.api.addKey("settings.locale", self.locale, self.api.STATEFILE)
        self.api.addKey("state.splitter.data", self.treeSplitter.saveState().data(), self.api.STATEFILE)
        self.api.addKey("state.tabWidget.tabBar.movable", self.tabWidget.tabBar().isMovable(), self.api.STATEFILE)
        self.api.addKey("state.tabWidget.tabBar.closable", self.tabWidget.tabBar().tabsClosable(), self.api.STATEFILE)
        index = self.treeView.currentIndex()
        if self.api.activeWindow.model.isDir(index): self.api.addKey("state.treeWidget.openedDir", self.api.activeWindow.model.filePath(index), self.api.STATEFILE)
        if self.api.activeWindow.activeView in self.api.activeWindow.views: self.api.addKey("state.tabWidget.activeTab", str(self.api.activeWindow.activeView.tabIndex()), self.api.STATEFILE)
        stateFile = os.path.join(self.api.packagesDirs, '.ws')
        for view in self.api.activeWindow.views:
            cursor = view.getTextCursor()
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            tabWidgetTabsState[str(view.tabIndex())] = {
                "name": view.getTitle(),
                "file": view.getFile(),
                "canSave": view.getCanSave(),
                "text": view.getText(),
                "isSaved": view.getSaved(),
                "selection": [start, end],
                # "modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "mmapHidden": view.isMmapHidden()
            }
        self.api.addKey("state.tabWidget.tabs", {str(idx): tabWidgetTabsState[str(idx)] for idx in range(len(tabWidgetTabsState))}, self.api.STATEFILE)
        self.api.activeWindow.signals.windowStateSaving.emit()
        if os.path.isfile(stateFile): mode = 'wb'
        else: mode = 'ab'
        with open(stateFile, mode) as f: f.write(msgpack.packb(stateDict, use_bin_type=True))
        self.settFile.close()

class NewWindowCommand(VtAPI.Plugin.ApplicationCommand):
    def run(self):
        w = MainWindow(api, restoreState=False)
        w.show()

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, api=None, restoreState=True):
        super().__init__()

        self.api = api
        self.logger = Logger(self)

        self.textContextMenu = QtWidgets.QMenu(self)
        self.tabBarContextMenu = QtWidgets.QMenu(self)

        self.setupUi(self, self.argvParse(), self.api)
        self.w = self.api.Window(self.api, qmwclass=self)
        self.api.addWindow(self.w)
        self.api.activeWindow = self.w
        self.windowInitialize()
        self.installEventFilter(self)
        self.pl = PluginManager(self.api.pluginsDir, self)
        if self.menuFile and os.path.isfile(self.menuFile): self.pl.loadMenu(self.menuFile)
        if os.path.isdir(os.path.join(self.api.uiDir, "locale")): self.translate(os.path.join(self.api.uiDir, "locale"))

        # Commands register area

        self.treeView.doubleClicked.connect(self.api.activeWindow.signals.onDoubleClicked)
        self.tabWidget.currentChanged.connect(self.api.activeWindow.signals.tabChngd)
        self.tabWidget.tabCloseRequested.connect(lambda: self.api.activeWindow.runCommand({"command": "CloseTabCommand"}))

        #####################################

        self.pl.loadPlugins()

        self.api.activeWindow.signals.windowStarted.emit()

        if restoreState: self.restoreWState()

        self.api.activeWindow.openFiles([sys.argv[1]] if len(sys.argv) > 1 else [])
        if self.api.activeWindow.activeView: self.api.activeWindow.activeView.update()
        self.show()

    def argvParse(self):
        return sys.argv

    # PYQT 6 standart events

    def eventFilter(self, a0, a1):
        if type(a1) in [QtGui.QHoverEvent, QtGui.QMoveEvent, QtGui.QResizeEvent, QtGui.QMouseEvent]:
            for window in self.api.windows:
                if window._Window__mw == a0:
                    self.api.activeWindow = window
        return super().eventFilter(a0, a1)

    def keyPressEvent(self, event):
        key_code = event.key()
        modifiers = event.modifiers()

        key_text = event.text()
        if key_text == '':
            return

        modifier_string = ""
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            modifier_string += "Ctrl+"
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            modifier_string += "Shift+"
        if modifiers & Qt.KeyboardModifier.AltModifier:
            modifier_string += "Alt+"

        if key_code in range(Qt.Key.Key_A, Qt.Key.Key_Z + 1):
            key_text = chr(ord('A') + key_code - Qt.Key.Key_A)
        elif key_code in range(Qt.Key.Key_0, Qt.Key.Key_9 + 1):
            key_text = chr(ord('0') + key_code - Qt.Key.Key_0)
        elif key_code == Qt.Key.Key_Space:
            key_text = "Space"
        elif key_code == Qt.Key.Key_Return:
            key_text = "Return"
        elif key_code == Qt.Key.Key_Escape:
            key_text = "Esc"
        elif key_code == Qt.Key.Key_Backspace:
            key_text = "Backspace"
        elif key_code == Qt.Key.Key_Tab:
            key_text = "Tab"

        action = self.pl.findActionShortcut(modifier_string + key_text)
        if action: action.trigger()

def main():
    global api
    app = QtWidgets.QApplication(sys.argv)
    api = VtAPI(app)
    w = MainWindow(api)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()