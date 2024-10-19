import sys
import json
import os
import io
from datetime import datetime
import msgpack
from PyQt6 import QtCore, QtWidgets

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
        if self.__window.console:
            self.__window.console.textEdit.clear()
            self.__window.console.textEdit.append(value)

    def write(self, message):
        if message:
            self.__window.api.App.setLogMsg(f"stdout: {message}")
            self._stdout_backup.write(message)

    def flush(self):
        pass

    def close(self):
        sys.stdout = self._stdout_backup
        self._log_stream.close()

class Ui_MainWindow(object):
    def setupUi(self, MainWindow, argv=[]):
        self.MainWindow = MainWindow
        self.appPath = os.path.dirname(argv[0])
        self.localeDirs = []
        self.settings()

        self.MainWindow.setObjectName("MainWindow")
        self.MainWindow.setWindowTitle(self.MainWindow.appName)
        self.MainWindow.resize(800, 600)

        self.console = None

        self.logger = Logger(self.MainWindow)
        self.translator = QtCore.QTranslator()

        self.centralwidget = QtWidgets.QWidget(parent=self.MainWindow)
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.treeView = self.createTreeView()
        self.treeSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.tabWidget = TabWidget(parent=self.centralwidget, MainWindow=self.MainWindow)

        self.setupMainWindow()
        self.api = VtAPI(self.MainWindow)
        self.logger.log = "VarTexter window loading..."

        QtCore.QMetaObject.connectSlotsByName(self.MainWindow)

    def createTreeView(self):
        treeView = QtWidgets.QTreeView(parent=self.centralwidget)
        treeView.setMinimumWidth(150)
        treeView.setMaximumWidth(300)
        treeView.setObjectName("treeWidget")
        treeView.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        return treeView

    def setupMainWindow(self):
        self.MainWindow.setCentralWidget(self.centralwidget)
        self.horizontalLayout.addWidget(self.treeSplitter)
        self.treeSplitter.addWidget(self.treeView)
        self.treeSplitter.addWidget(self.tabWidget)

        self.menubar = QtWidgets.QMenuBar(parent=self.MainWindow)
        self.MainWindow.setMenuBar(self.menubar)

        self.encodingLabel = QtWidgets.QLabel("UTF-8")
        self.statusbar = QtWidgets.QStatusBar(parent=self.MainWindow)
        self.statusbar.addPermanentWidget(self.encodingLabel)
        self.MainWindow.setStatusBar(self.statusbar)

    def addTab(self, name="", text="", file=None, canSave=True, canEdit=True, encoding="UTF-8"):
        tab = self.createTab(name, text, file, canSave, canEdit, encoding)
        self.tabWidget.addTab(tab, name or "Untitled")
        self.api.Tab.setTab(-1)
        self.api.SigSlots.tabCreated.emit()

    def createTab(self, name, text, file, canSave, canEdit, encoding):
        tab = QtWidgets.QWidget()
        tab.file = file
        tab.canSave = canSave
        tab.canEdit = canEdit
        tab.encoding = encoding
        tab.setObjectName("tab")

        verticalLayout = QtWidgets.QVBoxLayout(tab)
        frame = QtWidgets.QFrame(parent=tab)
        frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        verticalLayout.addWidget(frame)

        textEdit = TextEdit(self.MainWindow)
        textEdit.safeSetText(text)
        verticalLayout.addLayout(textEdit.layout)
        tab.textEdit = textEdit

        return tab

    def closeTab(self, i=None):
        if i is None:
            i = self.api.Tab.currentTabIndex()
        self.tabWidget.closeTab(i)

    def defineLocale(self):
        return QtCore.QLocale.system().name().split("_")[0]

    def translate(self, locale_dir):
        locale_file = os.path.join(locale_dir, f"{self.locale}.vt-locale")
        if os.path.isdir(locale_dir) and os.path.isfile(locale_file):
            if self.translator.load(locale_file):
                QtCore.QCoreApplication.installTranslator(self.translator)

    def logConsole(self, checked=None):
        if not hasattr(self, 'console'):
            self.console = ConsoleWidget(self.MainWindow)
            self.console.textEdit.append(self.logger.log)
            self.MainWindow.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.console)
        else:
            self.console.deleteLater()
            del self.console

    def settings(self):
        self.settFile = open(os.path.join(self.appPath, 'ui/Main.settings'), 'r+', encoding='utf-8')
        self.settData = json.load(self.settFile)
        self.initializeDirectories()
        self.MainWindow.appName = self.settData.get("appName")
        self.MainWindow.__version__ = self.settData.get("apiVersion")
        self.MainWindow.remindOnClose = self.settData.get("remindOnClose")
        self.menuFile = StaticInfo.replacePaths(os.path.join(self.packageDirs, self.settData.get("menu")))
        self.hotKeysFile = StaticInfo.replacePaths(os.path.join(self.packageDirs, self.settData.get("hotkeys")))
        self.locale = self.settData.get("locale", "auto")
        os.chdir(self.packageDirs)

    def initializeDirectories(self):
        self.packageDirs = self.settData.get("packageDirs")
        if self.packageDirs:
            self.packageDirs = StaticInfo.replacePaths(self.packageDirs.get(StaticInfo.get_platform()))
            os.makedirs(self.packageDirs, exist_ok=True)
            self.themesDir = StaticInfo.replacePaths(os.path.join(self.packageDirs, "Themes"))
            os.makedirs(self.themesDir, exist_ok=True)
            self.pluginsDir = StaticInfo.replacePaths(os.path.join(self.packageDirs, "Plugins"))
            os.makedirs(self.pluginsDir, exist_ok=True)
            self.uiDir = StaticInfo.replacePaths(os.path.join(self.packageDirs, "Ui"))
            os.makedirs(self.uiDir, exist_ok=True)
            self.cacheDir = StaticInfo.replacePaths(os.path.join(self.packageDirs, "cache"))
            os.makedirs(self.cacheDir, exist_ok=True)

    def hideShowMinimap(self):
        tab = self.tabWidget.currentWidget()
        if tab:
            minimap = tab.textEdit.minimapScrollArea
            minimap.setVisible(not minimap.isVisible())

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        openFileCommand = self.api.getCommand("openFile")
        if openFileCommand:
            openFileCommand.get("command")(files)
        else:
            self.showWarning("Open file function not found.")

    def showWarning(self, message):
        QtWidgets.QMessageBox.warning(self.MainWindow, f"{self.MainWindow.appName} - Warning", message)

    def saveWState(self):
        tabsInfo = {
            "tabs": {},
            "themeFile": self.themeFile,
            "locale": self.locale,
            "activeTab": str(self.api.Tab.currentTabIndex()),
            "splitterState": self.treeSplitter.saveState().data()
        }
        stateFile = os.path.join(self.packageDirs, 'data.msgpack')

        for idx in range(self.tabWidget.count()):
            widget = self.tabWidget.widget(idx)
            if widget and isinstance(widget, QtWidgets.QWidget):
                cursor = self.api.Text.getTextCursor(idx)
                start, end = cursor.selectionStart(), cursor.selectionEnd()
                tabsInfo["tabs"][str(idx)] = {
                    "name": self.api.Tab.getTabTitle(idx),
                    "file": self.api.Tab.getTabFile(idx),
                    "canSave": self.api.Tab.getTabCanSave(idx),
                    "text": self.api.Tab.getTabText(idx),
                    "saved": self.api.Tab.getTabSaved(idx),
                    "selection": [start, end],
                    "modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

        mode = 'ab' if os.path.isfile(stateFile) else 'wb'
        with open(stateFile, mode) as f:
            packed_data = msgpack.packb(tabsInfo, use_bin_type=True)
            f.write(packed_data)

        self.settFile.close()

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.constants = {
            "platform": StaticInfo.get_platform(),
            "basedir": StaticInfo.get_basedir(),
            "filedir": StaticInfo.get_filedir(__file__),
            "username": os.getlogin(),
        }

        self.textContextMenu = QtWidgets.QMenu(self)
        self.tabBarContextMenu = QtWidgets.QMenu(self)

        self.setupUi(self, sys.argv)
        self.windowInitialize()

        self.pl = PluginManager(self.pluginsDir, self)
        self.registerCommands()
        self.loadMenuAndPlugins()
        self.restoreWState()

        self.api.App.setTreeWidgetDir("/")
        self.executeOpenFileCommand()

    def registerCommands(self):
        commands = [
            {"command": "setTheme"},
            {"command": "hideShowMinimap"},
            {"command": "settingsHotKeys"},
            {"command": "argvParse"},
            {"command": "closeTab"},
            {"command": "addTab"},
            {"command": "showPackages"}
        ]
        for cmd in commands:
            self.pl.registerCommand(cmd)

    def loadMenuAndPlugins(self):
        if self.menuFile and os.path.isfile(self.menuFile):
            self.pl.loadMenu(self.menuFile)
        if os.path.isdir(os.path.join(self.uiDir, "locale")):
            self.translate(os.path.join(self.uiDir, "locale"))
        self.pl.load_plugins()
        self.api.loadThemes(self.menuBar())
        if self.hotKeysFile and os.path.isfile(self.hotKeysFile):
            self.pl.registerShortcuts(json.load(open(self.hotKeysFile, "r+")))
        self.pl.clearCache()

    def executeOpenFileCommand(self):
        openFileCommand = self.api.getCommand("openFile")
        if openFileCommand:
            openFileCommand.get("command")(sys.argv[1:])

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
