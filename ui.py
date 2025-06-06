from PySide6 import QtCore, QtWidgets

from addit import *
from api2 import PluginManager
from api import VtAPI

import sys, uuid

class Ui_MainWindow(object):
    def setupUi(self, MainWindow, argv=[], api=None):
        self.MainWindow: QtWidgets.QMainWindow = MainWindow
        self.logger = Logger(self)
        self.api: VtAPI = api
        self.appPath = self.api.Path(argv[0]).dirName()
        self.themeFile = ""
        self.localeDirs = []
        self.translators = []
        self.settings()

        self.MainWindow.setObjectName("MainWindow")
        self.MainWindow.resize(1000, 700)

        self.translator = QtCore.QTranslator()

        self.centralwidget = QtWidgets.QWidget(parent=self.MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.treeSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.horizontalLayout.addWidget(self.treeSplitter)

        self.tabWidget = TabWidget(parent=self.centralwidget, MainWindow=self.MainWindow)
        self.treeSplitter.addWidget(self.tabWidget)

        self.MainWindow.setCentralWidget(self.centralwidget)

        self.menubar = QtWidgets.QMenuBar(parent=self.MainWindow)
        self.menubar.setObjectName("menuBar")

        self.MainWindow.setMenuBar(self.menubar)

        self.statusbar = StatusBar(parent=self.MainWindow)
        self.statusbar.setAnimationList(["▁", "▂", "▅", "▆", "▇"])
        self.MainWindow.setStatusBar(self.statusbar)
        self.tagBasePath = self.api.Path.joinPath(self.api.getFolder("packages"), ".ft")
        self.tagBase = TagDB(self.tagBasePath)
        self.logger = self.MainWindow.logger
        self.MainWindow.logStdout = self.settData.get("logStdout")

        QtCore.QMetaObject.connectSlotsByName(self.MainWindow)

    def addTab(self): self.tabWidget.cAddTab()

    def getCommand(self, name): return getattr(sys.modules[__name__], name, None)

    def defineLocale(self): return QtCore.QLocale.system().name().split("_")[0]

    def translate(self, context, source_text):
        for tr in self.translators:
            QtCore.QCoreApplication.installTranslator(tr)
            if QtCore.QCoreApplication.translate(context, source_text) != source_text:
                return QtCore.QCoreApplication.translate(context, source_text)
        return source_text

    def addTranslation(self, d):
        if self.api.isDir(d) and self.api.File(self.api.Path.joinPath(d, f"{self.locale}.vt-locale")).exists():
            translator = QtCore.QTranslator()
            if translator.load(self.api.Path.joinPath(d, f"{self.locale}.vt-locale")):
                self.translators.append(translator)
                QtCore.QCoreApplication.installTranslator(translator)

    def settings(self):
        try:
            self.settFile = self.api.File(self.api.Path.joinPath(self.appPath, 'ui/Main.settings'))
            if self.settFile.exists():
                self.settData = self.api.Settings().fromFile(self.settFile).data()
            else:
                raise FileNotFoundError("File doesn't exists")
        except Exception as e:
            print(e)
            self.settData = {}
            self.api.activeWindow.setLogMsg(self.translate("Error reading settings. Check /ui/Main.settings file", self.api.Color.ERROR))
        tempD = self.settData.get("packageDirs") or "./Packages/"
        if type(tempD) == dict and tempD:
            self.api.setFolder("packages", self.api.replacePaths(tempD.get(self.api.platform())))
            self.api.setFolder("themes", self.api.replacePaths(self.api.Path.joinPath(self.api.getFolder("packages"), "Themes")))
            self.api.setFolder("plugins", self.api.replacePaths(self.api.Path.joinPath(self.api.getFolder("packages"), "Plugins")))
            self.api.setFolder("ui", self.api.replacePaths(self.api.Path.joinPath(self.api.getFolder("packages"), "Ui")))
            self.api.setFolder("cache", self.api.replacePaths(self.api.Path.joinPath(self.api.getFolder("packages"), "cache")))
            for d in [self.api.getFolder("packages"), self.api.getFolder("themes"), self.api.getFolder("plugins"), self.api.getFolder("ui"), self.api.getFolder("cache")]:
                if not self.api.Path(d).isDir(): self.api.Path(d).create()
            self.api.Path.chdir(self.api.getFolder("packages"))
            self.dirsLoaded = True
        self.api.setAppName(self.settData.get("appName") or "VT2")
        # self.api.__version__ = self.settData.get("apiVersion") or "1.0"
        self.MainWindow.logStdout = self.settData.get("logStdout") or False
        self.saveState = self.settData.get("saveState") or True
        self.MainWindow.remindOnClose = self.settData.get("remindOnClose")
        self.themeFile = ""
        if self.settData.get("menu"): self.menuFile = self.api.replacePaths(self.api.Path.joinPath(self.api.getFolder("packages"), self.settData.get("menu")))
        else: self.menuFile = None
        self.themeFile = self.api.findKey("themeFile", self.settData)
        self.locale = self.api.findKey("locale", self.settData)
        if self.locale == "auto" or not self.locale:
            self.locale = self.defineLocale()

class NewWindowCommand(VtAPI.Plugin.ApplicationCommand):
    def run(self):
        MainWindow(self.api)

class LoadBasicCommand(VtAPI.Plugin.WindowCommand):
    def __init__(self, api, window):
        super().__init__(api, window)
        self.api: VtAPI
    def run(self, url):
        thread = DownloadThread(self.api, self.window)
        thread.start()
        thread.wait()

class DownloadThread(VtAPI.Widgets.Thread):
    def __init__(self, api, window):
        super().__init__()
        self.api: VtAPI = api
        self.window: VtAPI.Window = window
        self.requests = self.api.importModule("urllib.request")
        self.zipfile = self.api.importModule("zipfile")
        self.shutil = self.api.importModule("shutil")
    def run(self):
        url = "https://github.com/VT2-1/Basic"
        self.api.activeWindow.setLogMsg(self.api.activeWindow.translate("Plugin 'Basic' not found. Trying to install last version from '{}'".format(url)), self.api.Color.WARNING)
        tempdirName = "vt-basic-install"
        try:
            path = self.api.Path.joinPath(self.api.replacePaths("%TEMP%") or self.api.Path(__file__).dirName(), tempdirName)
            self.api.Path(path).create()

            filePath = self.api.Path.joinPath(path, "package.zip")
            self.requests.urlretrieve(url + "/zipball/master", filePath)
            with self.zipfile.ZipFile(filePath, 'r') as f:
                f.extractall(path)
            self.api.Path(filePath).remove()

            extracted_dir = next(
                self.api.Path.joinPath(path, d) for d in self.api.Path(path).dir()
                if self.api.Path(self.api.Path.joinPath(path, d)).isDir()
            )
            finalPackageDir = self.api.Path.joinPath(self.api.getFolder("packages"), "Plugins", url.split("/")[-1])
            if not self.api.Path(self.api.getFolder("packages")).exists(): self.api.Path(self.api.getFolder("packages")).create()

            self.shutil.move(extracted_dir, finalPackageDir)
        except Exception as e:
            self.api.activeWindow.setLogMsg(self.window.translate("Error when loading plugin from '{}'".format(url)), self.api.Color.ERROR)
        finally:
            self.shutil.rmtree(path)
            self.window.setLogMsg(self.window.translate("'Basic' plugin succesfully installed. Reboot the app"), self.api.Color.INFO)

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, api=None, restoreState=True):
        super().__init__()
        self.dirsLoaded = False
        self.wId = f"window-{str(uuid.uuid4())[:4]}"

        self.api = api

        self.textContextMenu = QtWidgets.QMenu(self)
        self.tabBarContextMenu = QtWidgets.QMenu(self)

        self.w = self.api.Window(self.api, id=self.wId, qmwclass=self)
        self.api.addWindow(self.w)
        self.api.activeWindow = self.w
        self.setupUi(self, self.argvParse(), self.api)
        self.api.activeWindow.setTitle("Main")
        self.installEventFilter(self)
        # Signals register area

        self.tabWidget.currentChanged.connect(self.api.activeWindow.signals.tabChngd)
        self.tabWidget.tabCloseRequested.connect(lambda i: self.api.activeWindow.runCommand({"command": "CloseTabCommand", "kwargs": {"view": self.api.View(self.api, self.api.activeWindow, self.tabWidget.widget(i))}}))

        #####################################

        # self.dirsLoaded = False # Отладка (проверка независимости приложения от PluginManager и на правильную загрузку настроек)

        if self.dirsLoaded:
            self.pl = PluginManager(self.api.getFolder("plugins"), self)
            if self.api.Path(self.api.Path.joinPath(self.api.getFolder("ui"), "locale")).isDir(): self.addTranslation(self.api.Path.joinPath(self.api.getFolder("ui"), "locale"))
            if self.menuFile and self.api.Path(self.menuFile).isFile(): self.pl.loadMenu(self.menuFile)
            
            # Commands registering area

            self.w.registerCommandClass({"command": LoadBasicCommand})

            ####################################

            self.pl.loadPlugins()

        if restoreState: self.api.activeWindow.signals.windowStateRestoring.emit()
        self.processArgv()
        self.show()

        self.statusbar.startAnimation()
        # self.statusbar.showStatusMessage("Hello")
        self.w.signals.windowStarted.emit()

    def processArgv(self):
        self.api.activeWindow.openFiles([arg for arg in sys.argv[1:] if not arg.startswith("--log")])

    def argvParse(self):
        return sys.argv

    # PYQT 6 standart events

    def eventFilter(self, a0, a1):
        if isinstance(a1, (QtGui.QHoverEvent, QtGui.QMoveEvent, QtGui.QResizeEvent, QtGui.QMouseEvent)):
            for window in self.api.windows:
                if window._Window__mw == a0:
                    self.api.activeWindow = window
        return super().eventFilter(a0, a1)

    def keyPressEvent(self, event):
        key_code = event.key()
        modifiers = event.modifiers()

        key_text = event.text()
        if key_text == '': return
        modifier_string = ""
        if modifiers & Qt.KeyboardModifier.ControlModifier: modifier_string += "Ctrl+"
        if modifiers & Qt.KeyboardModifier.ShiftModifier: modifier_string += "Shift+"
        if modifiers & Qt.KeyboardModifier.AltModifier: modifier_string += "Alt+"
        if key_code in range(Qt.Key.Key_A, Qt.Key.Key_Z + 1): key_text = chr(ord('A') + key_code - Qt.Key.Key_A)
        elif key_code in range(Qt.Key.Key_0, Qt.Key.Key_9 + 1): key_text = chr(ord('0') + key_code - Qt.Key.Key_0)
        elif key_code == Qt.Key.Key_Space: key_text = "Space"
        elif key_code == Qt.Key.Key_Return: key_text = "Return"
        elif key_code == Qt.Key.Key_Escape: key_text = "Esc"
        elif key_code == Qt.Key.Key_Backspace: key_text = "Backspace"
        elif key_code == Qt.Key.Key_Tab: key_text = "Tab"

        if hasattr(self, "pl"):
            if type(getattr(self, "pl")) == PluginManager:
                action = self.pl.findActionShortcut(modifier_string + key_text)
                if action:
                    action.trigger()
                    return action

    def dragEnterEvent(self, event): [event.acceptProposedAction() if event.mimeData().hasUrls() else ""]

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        openFile = self.api.activeWindow.getCommand("OpenFileCommand")
        if openFile: self.api.activeWindow.runCommand({"command": "OpenFileCommand", "kwargs": {"f": files}})
        else: QtWidgets.QMessageBox.warning(self.MainWindow, self.MainWindow.appName + " - Warning", f"Open file function not found. Check your Open&Save plugin at {self.api.Path.joinPath(self.api.getFolder("plugins"), 'Open&Save')}")

    def closeEvent(self, e: QtCore.QEvent):
        if self.saveState: self.api.activeWindow.signals.windowStateSaving.emit()
        self.api.activeWindow.signals.windowClosed.emit()
        e.accept()