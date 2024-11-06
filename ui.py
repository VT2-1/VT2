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
        if self.__window.api.activeWindow:
            dock = self.__window.api.activeWindow.isDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea)
            if dock:
                try:
                    console = dock.textEdit
                    console.clear()
                    console.append(value)
                except: pass

    def write(self, message):
        if message:
            if self.__window.logStdout:
                self.__window.api.activeWindow.setLogMsg(f"stdout: {message}")
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
        if not api: self.api = VtAPI()
        else: self.api = api
        self.settings()
        self.api.appName = self.MainWindow.appName
        self.api.packagesDir = self.packageDirs
        self.api.pluginsDir = self.pluginsDir
        self.api.cacheDir = self.cacheDir
        self.api.themesDir = self.themesDir
        self.logger = Logger(self.MainWindow)
        self.logger.log = "VarTexter window loading..."

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

        self.frame = QtWidgets.QFrame(parent=self.tab)
        self.frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame.setObjectName("tabFrame")
        self.verticalLayout.addWidget(self.frame)

        self.tab.textEdit = TextEdit(self.MainWindow)
        self.tab.textEdit.setReadOnly(False)

        self.tab.textEdit.safeSetText(text)
        self.tab.textEdit.setObjectName("textEdit")

        self.verticalLayout.addLayout(self.tab.textEdit.layout)

        self.tabWidget.addTab(self.tab, "")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), name or "Untitled")
        self.api.activeWindow.setTab(-1)

        new_view = self.api.View(self.api, self.api.activeWindow, qwclass=self.tab)
        self.api.activeWindow.views.append(new_view)
        self.api.activeWindow.focus(new_view)

        self.api.activeWindow.signals.tabCreated.emit()

    def defineLocale(self):
        return QtCore.QLocale.system().name().split("_")[0]

    def translate(self, d):
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, f"{self.locale}.vt-locale")):
            if self.translator.load(os.path.join(d, f"{self.locale}.vt-locale")):
                QtCore.QCoreApplication.installTranslator(self.translator)

    def settings(self):
        self.settFile = open(os.path.join(self.appPath, 'ui/Main.settings'), 'r+', encoding='utf-8')
        self.settData = json.load(self.settFile)
        self.packageDirs = self.settData.get("packageDirs")
        if self.packageDirs:
            self.packageDirs = self.api.replacePaths(self.packageDirs.get(self.api.platform()))
            if not os.path.isdir(self.packageDirs): os.makedirs(self.packageDirs)
            self.themesDir = self.api.replacePaths(os.path.join(self.packageDirs, "Themes"))
            if not os.path.isdir(self.themesDir): os.makedirs(self.themesDir)
            self.pluginsDir = self.api.replacePaths(os.path.join(self.packageDirs, "Plugins"))
            if not os.path.isdir(self.pluginsDir): os.makedirs(self.pluginsDir)
            self.uiDir = self.api.replacePaths(os.path.join(self.packageDirs, "Ui"))
            if not os.path.isdir(self.uiDir): os.makedirs(self.uiDir)
            self.cacheDir = self.api.replacePaths(os.path.join(self.packageDirs, "cache"))
            if not os.path.isdir(self.cacheDir): os.makedirs(self.cacheDir)
        self.MainWindow.appName = self.settData.get("appName")
        self.MainWindow.__version__ = self.settData.get("apiVersion")
        self.logStdout = self.settData.get("logStdout")
        self.MainWindow.remindOnClose = self.settData.get("remindOnClose")
        self.menuFile = self.api.replacePaths(os.path.join(self.packageDirs, self.settData.get("menu")))
        os.chdir(self.packageDirs)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        openFile = self.api.getCommand("OpenFileCommand")
        if openFile:
            self.api.activeWindow.runCommand({"command": "OpenFileCommand", "kwargs": {"f": files}})
        else:
            QtWidgets.QMessageBox.warning(self.MainWindow, self.MainWindow.appName + " - Warning", f"Open file function not found. Check your Open&Save plugin at {os.path.join(self.pluginsDir, 'Open&Save')}")

    def getCommand(self, name):
        return getattr(sys.modules[__name__], name, None)

    def windowInitialize(self):
        [os.makedirs(dir) for dir in [self.themesDir, self.pluginsDir, self.uiDir] if not os.path.isdir(dir)]
        self.tabLog = {}
        stateFile = os.path.join(self.packageDirs, 'data.msgpack')
        self.MainWindow.setWindowTitle(self.MainWindow.appName)
        try:
            if os.path.isfile(stateFile):
                with open(stateFile, 'rb') as f:
                    packed_data = f.read()
                    self.tabLog = msgpack.unpackb(packed_data, raw=False)
        except ValueError:
            self.logger.log += f"\nFailed to restore window state. No file found at {stateFile}"  
            self.tabLog = {}
        if self.tabLog.get("themeFile"): self.themeFile = self.tabLog.get("themeFile")
        if self.tabLog.get("locale"): self.locale = self.tabLog.get("locale")
        else: self.locale = self.settData.get("locale")
        if self.locale == "auto":
            self.locale = self.defineLocale()
        self.api.activeWindow.setTheme(self.themeFile)

    def restoreWState(self):
        for tab in self.tabLog.get("tabs") or []:
            tab = self.tabLog.get("tabs").get(tab)
            self.addTab()
            self.api.activeWindow.activeView.setTitle(tab.get("name"))
            self.api.activeWindow.activeView.setFile(tab.get("file"))
            self.api.activeWindow.activeView.setText(tab.get("text"))
            self.api.activeWindow.activeView.setCanSave(tab.get("canSave"))
            self.api.activeWindow.activeView.setSaved(tab.get("saved"))
            self.MainWindow.setWindowTitle(f"{self.api.activeWindow.activeView.getTitle()} - VarTexter2")
            self.api.activeWindow.activeView.setTextSelection(tab.get("selection")[0], tab.get("selection")[1])
            self.api.activeWindow.activeView.setMmapHidden(tab.get("mmaphidden", 0))
        if self.tabLog.get("activeTab"):
            self.tabWidget.setCurrentIndex(int(self.tabLog.get("activeTab")))
        if self.tabLog.get("splitterState"): self.treeSplitter.restoreState(self.tabLog.get("splitterState"))

    def closeEvent(self, e: QtCore.QEvent):
        self.saveWState()
        self.api.activeWindow.signals.windowClosed.emit()

        e.accept()

    def saveWState(self):
        tabsInfo = {}
        tabs = tabsInfo["tabs"] = {}
        tabsInfo["themeFile"] = self.themeFile
        tabsInfo["locale"] = self.locale
        if self.api.activeWindow.activeView and self.api.activeWindow.activeView in self.api.activeWindow.views: tabsInfo["activeTab"] = str(self.api.activeWindow.activeView.tabIndex())
        tabsInfo["splitterState"] = self.treeSplitter.saveState().data()
        stateFile = os.path.join(self.packageDirs, 'data.msgpack')
        for view in self.api.activeWindow.views:
            cursor = view.getTextCursor()
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            tabs[str(view.tabIndex())] = {
                "name": view.getTitle(),
                "file": view.getFile(),
                "canSave": view.getCanSave(),
                "text": view.getText(),
                "saved": view.getSaved(),
                "selection": [start, end],
                "modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "mmaphidden": view.isMmapHidden()
            }
        tabs = {str(idx): tabs[str(idx)] for idx in range(len(tabs))}
        if os.path.isfile(stateFile):
            mode = 'wb'
        else:
            mode = 'ab'
        with open(stateFile, mode) as f:
            packed_data = msgpack.packb(tabsInfo, use_bin_type=True)
            f.write(packed_data)
        self.settFile.close()

class NewWindowCommand(VtAPI.Plugin.ApplicationCommand):
    def run(self):
        w = MainWindow(restoreState=False)
        w.show()

class ShowHideMinimap(VtAPI.Plugin.TextCommand):
    def run(self):
        self.view.setMmapHidden(not self.view.isMmapHidden())

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, api=None, restoreState=True):
        super().__init__()

        self.textContextMenu = QtWidgets.QMenu(self)
        self.tabBarContextMenu = QtWidgets.QMenu(self)

        self.setupUi(self, self.argvParse(), api)
        self.api.activeWindow = self.api.Window(self.api, qmwclass=self)
        self.windowInitialize()

        self.pl = PluginManager(self.pluginsDir, self)
        if self.menuFile and os.path.isfile(self.menuFile): self.pl.loadMenu(self.menuFile)
        if os.path.isdir(os.path.join(self.uiDir, "locale")): self.translate(os.path.join(self.uiDir, "locale"))

        self.pl.load_plugins()
        # self.api.activeWindow.registerCommandClass({"command": NewWindowCommand, "shortcut": "ctrl+shift+n"})
        # self.api.activeWindow.registerCommandClass({"command": ShowHideMinimap, "shortcut": "ctrl+d"})
        self.api.activeWindow.signals.windowStarted.emit()

        if restoreState: self.restoreWState()

        self.api.activeWindow.setTreeWidgetDir("/")

        self.api.activeWindow.openFiles([sys.argv[1]] if len(sys.argv) > 1 else [])
        if self.api.activeWindow.activeView: self.api.activeWindow.activeView.update()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        w = self.api.Window(self.api, qmwclass=self)
        if w in self.api.windows:
            self.api.activeWindow = w

    def argvParse(self):
        return sys.argv

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
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()