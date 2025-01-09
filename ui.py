from PyQt6 import QtCore, QtWidgets
import sys, uuid

from addit import *
from api2 import PluginManager, VtAPI

class Ui_MainWindow(object):
    def setupUi(self, MainWindow, argv=[], api=None):
        self.MainWindow: QtWidgets.QMainWindow = MainWindow
        self.api: VtAPI = api
        self.appPath = self.api.Path(argv[0]).dirName()
        self.wId = f"window-{str(uuid.uuid4())[:4]}"
        self.themeFile = ""
        self.localeDirs = []
        self.settings()

        self.MainWindow.setObjectName("MainWindow")
        self.MainWindow.resize(800, 600)

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
        self.menubar.setObjectName("menuBar")

        self.MainWindow.setMenuBar(self.menubar)

        self.encodingLabel = QtWidgets.QLabel("UTF-8")
        self.encodingLabel.setObjectName("encodingLabel")
        self.statusbar = QtWidgets.QStatusBar(parent=self.MainWindow)
        self.statusbar.setObjectName("statusbar")
        self.statusbar.addPermanentWidget(self.encodingLabel)
        self.MainWindow.setStatusBar(self.statusbar)
        self.tagBase = TagDB(self.api.Path.joinPath(self.api.packagesDirs, ".ft"))
        self.logger = self.MainWindow.logger

        QtCore.QMetaObject.connectSlotsByName(self.MainWindow)

    def addTab(self):
        self.tab = QtWidgets.QWidget()
        self.tab.file = None
        self.tab.canSave = None
        self.tab.canEdit = None
        self.tabWidget.tabBar().setTabSaved(self.tab, True)
        self.tab.encoding = "utf-8"
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
        self.tab.textEdit.setObjectName("textEdit")

        self.verticalLayout.addLayout(self.tab.textEdit.layout)

        newView = self.api.View(self.api, self.api.activeWindow, qwclass=self.tab)
        self.api.activeWindow.views.append(newView)

        self.tabWidget.addTab(self.tab, "")
        self.api.activeWindow.setTab(-1)
        self.api.activeWindow.focus(newView)

        self.api.activeWindow.signals.tabCreated.emit()

    def getCommand(self, name): return getattr(sys.modules[__name__], name, None)

    def defineLocale(self): return QtCore.QLocale.system().name().split("_")[0]

    def translate(self, d):
        if self.api.isDir(d) and self.api.File(self.api.Path.joinPath(d, f"{self.locale}.vt-locale")).exists():
            if self.translator.load(self.api.Path.joinPath(d, f"{self.locale}.vt-locale")):
                QtCore.QCoreApplication.installTranslator(self.translator)

    def settings(self):
        try:
            self.settFile = self.api.File(self.api.Path.joinPath(self.appPath, 'ui/Main.settings'))
            if self.settFile.exists():
                self.settData = self.api.Settings()
                self.settData.fromFile(self.settFile)
                self.settData = self.settData.data()
            else:
                raise FileNotFoundError("File doesn't exists")
        except Exception as e:
            self.settData = {}
            # self.api.activeWindow.setLogMsg("Error reading settings. Check /ui/Main.settings file", self.api.ERROR)
        self.api.packagesDirs = self.settData.get("packageDirs") or "./Packages/"
        if type(self.api.packagesDirs) == dict:
            self.api.packagesDirs = self.api.replacePaths(self.api.packagesDirs.get(self.api.platform()))
        self.api.themesDir = self.api.replacePaths(self.api.Path.joinPath(self.api.packagesDirs, "Themes"))
        self.api.pluginsDir = self.api.replacePaths(self.api.Path.joinPath(self.api.packagesDirs, "Plugins"))
        self.api.uiDir = self.api.replacePaths(self.api.Path.joinPath(self.api.packagesDirs, "Ui"))
        self.api.cacheDir = self.api.replacePaths(self.api.Path.joinPath(self.api.packagesDirs, "cache"))
        for d in [self.api.packagesDirs, self.api.themesDir, self.api.pluginsDir, self.api.uiDir, self.api.cacheDir]:
            if not self.api.Path(d).isDir(): self.api.Path(d).create()
        self.api.appName = self.settData.get("appName") or "VT2"
        self.api.__version__ = self.settData.get("apiVersion") or "1.0"
        self.MainWindow.logStdout = self.settData.get("logStdout") or False
        self.saveState = self.settData.get("saveState") or True
        self.MainWindow.remindOnClose = self.settData.get("remindOnClose")
        self.themeFile = ""
        if self.settData.get("menu"): self.menuFile = self.api.replacePaths(self.api.Path.joinPath(self.api.packagesDirs, self.settData.get("menu")))
        else: self.menuFile = None
        self.api.Path.chdir(self.api.packagesDirs)
        [self.api.Path(dir).create() for dir in [self.api.themesDir, self.api.pluginsDir, self.api.uiDir] if not self.api.Path(dir).isDir()]
        self.themeFile = self.api.findKey("themeFile", self.settData)
        self.locale = self.api.findKey("locale", self.settData)
        if self.locale == "auto" or not self.locale:
            self.locale = self.defineLocale()

class NewWindowCommand(VtAPI.Plugin.ApplicationCommand):
    def run(self):
        MainWindow(self.api)

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, api=None, restoreState=True):
        super().__init__()

        self.api = api
        self.logger = Logger(self)

        self.textContextMenu = QtWidgets.QMenu(self)
        self.tabBarContextMenu = QtWidgets.QMenu(self)

        self.setupUi(self, self.argvParse(), self.api)
        self.w = self.api.Window(self.api, id=self.wId, qmwclass=self)
        self.api.addWindow(self.w)
        self.api.activeWindow = self.w
        self.api.activeWindow.setTitle("Main")
        self.installEventFilter(self)
        self.pl = PluginManager(self.api.pluginsDir, self)
        if self.menuFile and self.api.Path(self.menuFile).isFile(): self.pl.loadMenu(self.menuFile)
        if self.api.Path(self.api.Path.joinPath(self.api.uiDir, "locale")).isDir(): self.translate(self.api.Path.joinPath(self.api.uiDir, "locale"))

        # Commands/signals register area

        self.treeView.doubleClicked.connect(self.api.activeWindow.signals.onDoubleClicked)
        self.tabWidget.currentChanged.connect(self.api.activeWindow.signals.tabChngd)
        self.tabWidget.tabCloseRequested.connect(lambda: self.api.activeWindow.runCommand({"command": "CloseTabCommand"}))

        #####################################

        self.pl.loadPlugins()
        otherPlugin = api.Plugin(api, "PythonSyntax", r"C:\Users\Trash\Documents\VarTexter2\Plugins\PythonSyntax")
        [otherPlugin.load(w) for w in api.windows]
        self.api.activeWindow.signals.windowStarted.emit()

        if restoreState: self.api.activeWindow.signals.windowStateRestoring.emit()

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

        action = self.pl.findActionShortcut(modifier_string + key_text)
        if action: action.trigger()

    def dragEnterEvent(self, event): [event.acceptProposedAction() if event.mimeData().hasUrls() else ""]

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        openFile = self.api.activeWindow.getCommand("OpenFileCommand")
        if openFile:
            self.api.activeWindow.runCommand({"command": "OpenFileCommand", "kwargs": {"f": files}})
        else:
            QtWidgets.QMessageBox.warning(self.MainWindow, self.MainWindow.appName + " - Warning", f"Open file function not found. Check your Open&Save plugin at {self.api.Path.joinPath(self.api.pluginsDir, 'Open&Save')}")

    def closeEvent(self, e: QtCore.QEvent):
        if self.saveState: self.api.activeWindow.signals.windowStateSaving.emit()
        self.api.activeWindow.signals.windowClosed.emit()
        e.accept()

def main():
    app = QtWidgets.QApplication(sys.argv)
    api = VtAPI(app)
    w = MainWindow(api)

    # TEST CODE OF PLUGIN LOADING

    if not "PythonIDE" in api.activeWindow.plugins():
        otherPlugin2 = api.Plugin(api, "PythonIDE", r"C:\Users\Trash\Documents\VarTexter2\Plugins\PythonIDE")
        [otherPlugin2.load(w) for w in api.windows]
    sys.exit(app.exec())

if __name__ == "__main__":
    main()