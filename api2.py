from enum import Enum
from PySide6 import QtWidgets, QtCore, QtGui
from typing import *
import os, sys, json, importlib, re, platform, inspect, asyncio, builtins, traceback, time
import urllib.request as requests
import functools
import importlib.util

BLOCKED = [
    "PyQt6",
    "PyQt5",
    "PyQt4",
    "shiboken"
]

oldCoreApp = QtCore.QCoreApplication
oldQApp = QtWidgets.QApplication
oldGuiApp = QtGui.QGuiApplication

class SafeImporter:
    def __init__(self, disallowed_imports):
        self.disallowed_imports = disallowed_imports

    def __enter__(self):
        self.original_import = builtins.__import__
        builtins.__import__ = self.import_hook

    def __exit__(self, exc_type, exc_value, traceback):
        builtins.__import__ = self.original_import

    def import_hook(self, name, *args, **kwargs):
        for disallowed in self.disallowed_imports:
            if name.startswith(disallowed):
                raise ImportError(f"Importing '{name}' is not allowed.")
        return self.original_import(name, *args, **kwargs)

class BlockedQApplication:
    def __init__(self, *args, **kwargs):
        raise ImportError("Access to QApplication is not allowed.")

class PluginManager:
    def __init__(self, plugin_directory: str, w):
        self.plugin_directory = plugin_directory
        self.plugins = {}
        self.__window: QtWidgets.QMainWindow = w
        self.__windowApi: VtAPI = self.__window.api
        self.__menu_map = {}
        self.shortcuts = []
        self.regCommands = {}
        self.dPath = os.getcwd()

    def importModule(self, path, n):
        spec = importlib.util.spec_from_file_location(n, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[n] = module
        spec.loader.exec_module(module)
        return module

    def loadPlugins(self):
        try:
            sys.path.insert(0, self.plugin_directory)
            for plugDir in os.listdir(self.plugin_directory):
                if self.__windowApi.Path(VtAPI.Path.joinPath(self.plugin_directory, plugDir)).isDir():
                    self.fullPath = os.path.join(self.plugin_directory, plugDir)
                    self.plugins[plugDir] = self.fullPath

            if self.plugins.get("Basic"):
                self.loadPlugin("Basic")
                self.plugins.pop("Basic")
            else:
                self.__windowApi.activeWindow.runCommand({"command": "LoadBasicCommand", "kwargs": {"url": "https://github.com/cherry220-v/Basic"}})
            for pl in self.plugins:
                self.loadPlugin(pl)
        except Exception as e:
            print(e, self.__windowApi.Color.ERROR)
        finally:
            os.chdir(self.dPath)

    def loadPlugin(self, name):
        fullPath = self.plugins.get(name)
        os.chdir(fullPath)
        if os.path.isdir(fullPath) and os.path.isfile(f"config.vt-conf"):
            self.initPlugin(os.path.join(fullPath, "config.vt-conf"))
            if self.mainFile:
                pyFile = self.mainFile
                try:
                    with SafeImporter(BLOCKED):
                        # sys.modules['PyQt6.QtWidgets'].QApplication = BlockedQApplication
                        # sys.modules['PyQt6.QtCore'].QCoreApplication = BlockedQApplication
                        # sys.modules['PyQt6.QtGui'].QGuiApplication = BlockedQApplication
                        sys.path.insert(0, fullPath)
                        self.module = self.importModule(pyFile, self.name + "Plugin")
                        if hasattr(self.module, "initAPI"):
                            self.module.initAPI(self.__windowApi)
                        # sys.modules['PyQt6.QtWidgets'].QApplication = oldQApp
                        # sys.modules['PyQt6.QtGui'].QGuiApplication = oldGuiApp
                        # sys.modules['PyQt6.QtCore'].QCoreApplication = oldCoreApp
                    self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Loaded plugin '{}'").format(self.name), self.__windowApi.Color.INFO)
                except Exception as e:
                    print(self.name, e)
                    self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Failed load plugin '{}' commands: {}").format(self.name, e), self.__windowApi.Color.ERROR)
                    self.module = None
                finally:
                    sys.path.pop(0)
            if self.menuFile:
                self.loadMenu(self.menuFile, module=self.module, path=fullPath)
            os.chdir(self.__windowApi.packagesDirs)

    def loadMenu(self, f, module=None, path=None):
        try:
            menuFile = json.load(open(f, "r+"))
            localeDir = os.path.join(path if path else "", "locale")
            if os.path.isdir(localeDir):
                self.__window.addTranslation(localeDir)
            for menu in menuFile:
                if menu == "menuBar" or menu == "mainMenu":
                    self.parseMenu(menuFile.get(menu), self.__window.menuBar(), pl=module, localemenu="MainMenu")
                elif menu == "textContextMenu":
                    self.parseMenu(menuFile.get(menu), self.__window.textContextMenu, pl=module, localemenu="TextContextMenu")
                elif menu == "tabBarContextMenu":
                    self.parseMenu(menuFile.get(menu), self.__window.tabBarContextMenu, pl=module, localemenu="TabBarContextMenu")
        except Exception as e:
            self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Failed load menu from '{}': {}").format(f, e))


    def initPlugin(self, path):
        config = json.load(open(path, "r+"))

        self.name = config.get('name', 'Unknown')
        self.version = config.get('version', '1.0')
        self.mainFile = config.get('main', '')
        self.menuFile = config.get('menu', '')

    def parseMenu(self, data, parent, pl=None, localemenu="MainMenu", regc=True):
        if isinstance(data, dict):
            data = [data]

        for item in data:
            if item.get('caption') == "-":
                parent.addSeparator()
                continue
            menu_id = item.get('id')
            if menu_id:
                fmenu = self.findMenu(parent, menu_id)
                if fmenu:
                    if 'children' in item:
                        self.parseMenu(item['children'], fmenu, pl)
                else:
                    menu = self.__menu_map.setdefault(menu_id, QtWidgets.QMenu(self.__window.translate(localemenu, item.get('caption', 'Unnamed')), self.__window))
                    menu.setObjectName(item.get('id'))
                    parent.addMenu(menu)
                    if 'children' in item:
                        self.parseMenu(item['children'], menu, pl)
            else:
                action = QtGui.QAction(self.__window.translate(localemenu, item.get('caption', 'Unnamed')), self.__window)
                if 'shortcut' in item:
                    if not item['shortcut'] in self.shortcuts:
                        if type(item["shortcut"]) != list:
                            item["shortcut"] = [item['shortcut']]
                        action.setShortcuts(item["shortcut"])
                            # action.setStatusTip(item['shortcut'])
                        self.shortcuts.append(key for key in item["shortcut"])
                        self.__window.addAction(action)
                    else:
                        self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Shortcut '{}' for function '{}' is already used.").format(item['shortcut'], item['command']))

                if 'command' in item:
                    args = item.get('command').get("args")
                    kwargs = item.get('command').get("kwargs")
                    data = {"action": action, "command": item['command'], "plugin": pl, "args": args, "kwargs": kwargs}
                    if 'checkable' in item:
                        action.setCheckable(item['checkable'])
                        if "checkedStatePath" in item:
                            data["checkedStatePath"] = item.get("checkedStatePath")
                        if 'checked' in item:
                            action.setChecked(item['checked'])
                    if regc: self.registerCommand(data)
                    else: action.triggered.connect(lambda: self.__windowApi.activeWindow.runCommand(item["command"]))
                parent.addAction(action)

    def executeCommand(self, c, *args, **kwargs):
        ckwargs = kwargs
        command = c
        c = self.regCommands.get(command.get("command"))
        if c:
            try:
                args = command.get("args") or []
                kwargs = command.get("kwargs") or {}
                action = c.get("action")
                if action and action.isCheckable():
                    if c.get("checkedStatePath"):
                        value = self.__windowApi.findKey(c.get("checkedStatePath"), self.__windowApi.STATEFILE)
                        if value in [True, False]:
                            if "restoring" in kwargs:
                                action.setChecked(value)
                            else:
                                action.setChecked(not value)
                cl = c.get("command")
                if issubclass(cl, VtAPI.Plugin.TextCommand):
                    c = cl(self.__windowApi, self.__windowApi.activeWindow.activeView)
                elif issubclass(cl, VtAPI.Plugin.WindowCommand):
                    c = cl(self.__windowApi, self.__windowApi.activeWindow)
                elif issubclass(cl, VtAPI.Plugin.ApplicationCommand):
                    c = cl(self.__windowApi)
                out = c.run(*args or [], **kwargs or {})
                self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Executed command '{}'").format(command), self.__windowApi.Color.INFO)
                if out:
                    self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Command '{}' returned '{}'").format(command, out), self.__windowApi.Color.ERROR)
            except Exception as e:
                traceback.print_exc()
                self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Found error in '{}' - '{}'").format(command, e), self.__windowApi.Color.ERROR)
        else:
            self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Command '{}' not found").format(command), self.__windowApi.Color.WARNING)

    def registerClass(self, data):
        commandClass = data.get("command")
        if inspect.isclass(commandClass):
            commandN = commandClass.__name__
            pl = commandClass.__module__
            args = data.get("args", [])
            kwargs = data.get("kwargs", {})
            action = data.get("action") or QtGui.QAction("", self.__window)
            chkdStatePath = data.get("checkedStatePath")
            if 'shortcut' in data:
                if not data['shortcut'] in self.shortcuts:
                    action.setShortcut(QtGui.QKeySequence(data['shortcut']))
                    self.shortcuts.append(data['shortcut'])
                    action.triggered.connect(lambda: self.executeCommand({"command": commandN, "args": args, "kwargs": kwargs}))
                    self.__window.addAction(action)
            self.regCommands[commandN] = {
                "action": action,
                "command": commandClass,
                "args": args,
                "kwargs": kwargs,
                "plugin": pl,
                "checkedStatePath": chkdStatePath,
            }

    def registerCommand(self, commandInfo):
        command = commandInfo.get("command")
        if type(command) == str:
            commandN = command
        elif inspect.isclass(command):
            commandN = command
        else:
            commandN = command.get("command")
        pl = commandInfo.get("plugin")
        action = commandInfo.get("action") or QtGui.QAction("", self.__window)

        args = commandInfo.get("args", [])
        kwargs = commandInfo.get("kwargs", {})
        chkdStatePath = commandInfo.get("checkedStatePath")
        action.triggered.connect(lambda: self.executeCommand({"command": commandN, "args": args, "kwargs": kwargs}))
        if 'shortcut' in commandInfo:
            if not commandInfo['shortcut'] in self.shortcuts:
                action.setShortcut(QtGui.QKeySequence(commandInfo['shortcut']))
                self.shortcuts.append(commandInfo['shortcut'])
                self.__window.addAction(action)

        if pl:
            try:
                command_func = getattr(pl, commandN)
                self.regCommands[commandN] = {
                    "action": action,
                    "command": command_func,
                    "args": args,
                    "kwargs": kwargs,
                    "plugin": pl,
                    "checkedStatePath": chkdStatePath,
                }
            except (ImportError, AttributeError, TypeError) as e:
                self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Error when registering '{}' from '{}': {}").format(commandN, pl, e))

        else:
            if not inspect.isclass(commandN):
                command_func = self.__window.getCommand(commandN)
            else:
                command_func = commandN
            if command_func:
                self.regCommands[commandN] = {
                    "action": action,
                    "command": command_func,
                    "args": args,
                    "kwargs": kwargs,
                    "plugin": None,
                    "checkedStatePath": chkdStatePath,
                }
            else:
                print(commandN)
                self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Command '{}' not found").format(commandN))

    def findAction(self, parent_menu, caption=None, command=None):
        for action in parent_menu.actions():
            if caption and action.text() == caption:
                return action
            if command and hasattr(action, 'command') and action.command == command:
                return action

        for action in parent_menu.actions():
            if action.menu():
                found_action = self.findAction(action.menu(), caption, command)
                if found_action:
                    return found_action

        return None

    def findActionShortcut(self, shortcut):
        key_sequence = QtGui.QKeySequence(shortcut)
        actions = self.__window.actions()
        for action in actions:
            if action.shortcut() == key_sequence:
                return action

    def findMenu(self, menubar, menu_id):
        for action in menubar.actions():
            menu = action.menu()
            if menu:
                if menu.objectName() == menu_id:
                    return menu
                found_menu = self.findMenu2(menu, menu_id)
                if found_menu:
                    return found_menu
        return None

    def findMenu2(self, menu, menu_id):
        for action in menu.actions():
            submenu = action.menu()
            if submenu:
                if submenu.objectName() == menu_id:
                    return submenu
                found_menu = self.findMenu2(submenu, menu_id)
                if found_menu:
                    return found_menu
        return None

    def clearMenu(self, menu, menu_id):
        menu = self.findMenu(menu, menu_id)
        if menu:
            menu.clear()

class VtAPI:
    __slots__ = ('_VtAPI__app', '_VtAPI__windows', '_VtAPI__activeWindow', 'STATEFILE', 'CLOSINGSTATEFILE', '__weakref__', 'packagesDirs', 'pluginsDir', 'uiDir', 'themesDir', 'cacheDir', 'appName', '__version__')
    def __init__(self, app=None):
        try:
            self.__app = QtWidgets.QApplication.instance()
        except:
            self.__app: QtWidgets.QApplication = app
        self.__windows = []
        self.__activeWindow: VtAPI.Window | None = None

        self.STATEFILE = {}
        self.CLOSINGSTATEFILE = {}
    
    class Color(Enum):
        INFO = ""
        WARNING = "#edba00"
        ERROR = "#e03c00"
        SUCCESS = "#61a600"
        BLUE = "#4034eb"

    class Window:
        """Окно и управление им"""
        __slots__ = ('api', '_Window__mw', 'signals', '_Window__views', '_Window__activeView', 'model', 'id')
        def __init__(self, api: "VtAPI", id: Optional[str] = None, views: Optional[List['VtAPI.View']] = None, activeView: Optional['VtAPI.View'] = None, qmwclass: Optional[QtWidgets.QMainWindow] = None) -> None:
            """Инициализация для использования
```
w = Window(api, wId, [View(api, w)])
w.focus(w.views[0])
api.addWindow(w)
```
            """
            self.api: VtAPI = api
            self.__mw: QtWidgets.QMainWindow = qmwclass
            self.signals: VtAPI.Signals = VtAPI.Signals(self.__mw)
            self.__views = views or []
            self.__activeView: VtAPI.View | None = activeView
            self.model = QtWidgets.QFileSystemModel()
            self.id = id
        
        def __eq__(self, value):
            return self.id == value.id

        def newFile(self) -> 'VtAPI.View':
            """Создаёт новую вкладку"""
            self.__mw.addTab()
            return self.activeView
        
        def openFiles(self, files: List[str]) -> None:
            """Открывает файл(ы) (Запускает стандартную привязанную команду OpenFileCommand)"""
            self.runCommand({"command": "OpenFileCommand", "args": [files]})
        
        def saveFile(self, view: Optional['VtAPI.View'] = None, dlg: bool = False) -> None:
            """Сохраняет текст вкладки (Запускает стандартную привязанную команду SaveFileCommand)"""
            self.runCommand({"command": "SaveFileCommand", "kwargs": {"dlg": dlg}})
        
        @property
        def activeView(self) -> 'VtAPI.View':
            """Получает активную вкладку"""
            return self.__activeView
        
        @activeView.setter
        def activeView(self, view: 'VtAPI.View') -> Optional['VtAPI.View']:
            for v in self.__views:
                if v == view:
                    self.__activeView = v
                    break
                    return v
            return None
                    
        @property
        def views(self) -> Tuple['VtAPI.View']:
            """Получает список вкладок"""
            return tuple(self.__views)
        
        def addView(self, view: 'VtAPI.View') -> True:
            for v in self.__views:
                if v == view:
                    return True
            self.__views.append(view)
            return True
        
        def delView(self, view: 'VtAPI.View') -> True:
            for v in self.__views:
                if v == view:
                    self.__views.remove(v)
                    return True

        def state(self) -> dict:
            """Получает состояние окна"""
            return self.api.STATEFILE.get(self.id)
        
        def plugins(self) -> dict:
            """Получает загруженные плагины окна"""
            if hasattr(self.__mw, "pl"):
                if isinstance(self.__mw.pl, PluginManager):
                    return self.__mw.pl.plugins

        def translate(self, text, trtype="Console"):
            return self.__mw.translate(trtype, text)

        def update(self):
            QtCore.QCoreApplication.processEvents()

        def setUpdatesEnabled(self, b: bool):
            self.__mw.setUpdatesEnabled(b)

        def getTitle(self) -> str:
            return self.__mw.windowTitle()

        def setTitle(self, s: str) -> str:
            self.__mw.setWindowTitle(f"{s} - {self.api.appName}")
            return self.getTitle()

        def focus(self, view):
            if view in self.views:
                self.__mw.tabWidget.setCurrentIndex(view.tabIndex())
                self.activeView = view
                self.setTitle(os.path.normpath(self.activeView.getFile() or 'Untitled'))

        def registerCommandClass(self, data):
            if hasattr(self.__mw, "pl"):
                if isinstance(self.__mw.pl, PluginManager):
                    self.__mw.pl.registerClass(data)

        def registerCommand(self, data):
            if hasattr(self.__mw, "pl"):
                if isinstance(self.__mw.pl, PluginManager):
                    self.__mw.pl.registerCommand(data)

        def runCommand(self, command):
            if hasattr(self.__mw, "pl"):
                if isinstance(self.__mw.pl, PluginManager):
                    self.__mw.pl.executeCommand(command)

        def getCommand(self, name):
            if hasattr(self.__mw, "pl"):
                if isinstance(self.__mw.pl, PluginManager):
                    return self.__mw.pl.regCommands.get(name)

        def getTheme(self):
            return self.__mw.themeFile

        def setTheme(self, theme):
            themePath = os.path.join(self.api.themesDir, theme)
            if os.path.isfile(themePath):
                self.__mw.setStyleSheet(open(themePath, "r+").read())
                self.__mw.themeFile = theme

        def getLocale(self):
            return self.__mw.locale

        def setLocale(self, s: str, auto=False):
            if auto: locale = self.__mw.defineLocale()
            else: locale = s
            self.__mw.locale = locale
            return locale

        def getLog(self):
            return self.__mw.logger.log

        def setLogMsg(self, msg, t: "VtAPI.Color" = None):
            msg = f"""<i style="color: {t.value if t else ""};">{msg}</i>"""
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

        def setTabsMovable(self, b: bool):
            return self.__mw.tabWidget.tabBar().setMovable(b)

        def setTabsClosable(self, b: bool):
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

        def addDockWidget(self, areas, dock: 'VtAPI.Widgets.DockWidget'):
            self.__mw.addDockWidget(areas, dock)

        def showDialog(self, content, flags=0, location=-1, width=320, height=240, on_navigate=None, on_hide=None):
            self.content = content
            self.flags = flags
            self.location = location
            self.width = width
            self.height = height
            self.on_navigate = on_navigate
            self.on_hide = on_hide

            self.dialog = VtAPI.Widgets.Dialog(parent=self.__mw)
            self.dialog.setWindowTitle(self.api.appName)
            if self.flags:
                self.dialog.setWindowFlags(self.flags)
            self.dialog.setFixedWidth(self.width)
            self.dialog.setFixedHeight(self.height)

            self.dialog.setLayout(self.content)
            self.dialog.exec()
        
        def isDockWidget(self, area):
            dock_widgets = self.__mw.findChildren(QtWidgets.QDockWidget)
            for dock in dock_widgets:
                if self.__mw.dockWidgetArea(dock) == area: return dock

        def statusMessage(self, text, timeout=0):
            self.__mw.statusbar.showStatusMessage(text, timeout)

    class View:
        __slots__ = ['api', '_View__tab', 'tagBase', '_View__window', '_View__tagBase', '_View__tabWidget', '_View__id']
        def __init__(self, api, window, qwclass=None, id=None):
            self.api: VtAPI = api
            self.__window: VtAPI.Window = window
            self.__tab: QtWidgets.QWidget = qwclass
            if self.__tab:
                self.__id: str = self.__tab.objectName().split("-")[-1]
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

        def update(self):
            view = VtAPI.View(self.api, self.__window, qwclass=self.__tabWidget.currentWidget())
            view.id = self.__tabWidget.currentWidget().objectName().split("-")[-1]
            self.window().focus(view)

        def __hash__(self):
            return hash(self.tabIndex())

        def tabIndex(self):
            return self.__tabWidget.indexOf(self.__tab)

        def close(self):
            return self.__tabWidget.closeTab(self.__tab)
        
        def window(self):
            return self.__window

        def focus(self):
            self.window.focus(self)
            self.__tab.textEdit.setFocus()

        def getTitle(self):
            return self.__tabWidget.tabText(self.__tabWidget.indexOf(self.__tab))

        def setTitle(self, text):
            return self.__tabWidget.setTabText(self.__tabWidget.indexOf(self.__tab), text)

        def getText(self):
            text = self.__tab.textEdit.toPlainText()
            return text

        def getHtml(self):
            text = self.__tab.textEdit.toHtml()
            return text

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

        def setCanSave(self, b: bool):
            self.__tab.canSave = b
            return b

        def getCanEdit(self):
            return self.__tab.canEdit

        def isReadOnly(self):
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
            return self.__tabWidget.isSaved(self.__tab)

        def setSaved(self, b: bool):
            self.__tabWidget.tabBar().setTabSaved(self.__tab, b)
            print(self.getTitle(), b)
            return b

        def size(self):
            return self.__tab.textEdit.textLen()

        def substr(self, region: "VtAPI.Region"):
            return self.__tab.textEdit.toPlainText()[region.begin():region.end()]

        def insert(self, string, point: "VtAPI.Point"=None):
            textEdit = self.__tab.textEdit
            cursor = textEdit.textCursor()
            if point is not None:
                line_index, char_index = point.x, point.y
                lines = textEdit.toPlainText().splitlines()
                abs_position = sum(len(lines[i]) + 1 for i in range(line_index)) + char_index
                cursor.setPosition(abs_position)
            else:
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            textEdit.safeSetText(string, cursor)
            textEdit.setTextCursor(cursor)
            self.setSaved(False)
        
        def erase(self, region: "VtAPI.Region"):
            t = self.__tab.textEdit.toPlainText()
            self.__tab.textEdit.setPlainText(t[:region.begin()] + t[region.end():])
        
        def replace(self, region: "VtAPI.Region", string):
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
            if self.__tab.textEdit.document().isUndoAvailable():
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
            return self.__window.tabWidget.isSaved(self.__tab)

        def getTextSelection(self):
            return self.__tab.textEdit.textCursor().selectedText()

        def getTextCursor(self):
            return self.__tab.textEdit.textCursor()

        def setTextSelection(self, region: "VtAPI.Region"):
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

        def setHighlighter(self, hl: dict):
            for _type in hl:
                self.__tab.textEdit.highLighter.addHighlightingRule(_type, hl.get(_type))
        
        def setAddititionalHL(self, data):
            self.__tab.textEdit.highLighter.addHighlightingData(data)

        def rehighlite(self):
            QtCore.QMetaObject.invokeMethod(
                self.__tab.textEdit.highLighter, "rehighlight",
                QtCore.Qt.QueuedConnection
            )

        def setMmapHidden(self, b: bool):
            if b:
                self.__tab.textEdit.minimapScrollArea.hide()
            else:
                self.__tab.textEdit.minimapScrollArea.show()

        def isMmapHidden(self) -> bool:
            return self.__tab.textEdit.minimapScrollArea.isHidden()
        
        def initTagFile(self, path):
            if os.path.isfile(path): self.tagBase.addFile(path)

        def getTags(self, path):
            return self.tagBase.getTagsForFile(path)

        def addTag(self, path, tag: str):
            self.tagBase.addTag(path, tag)
            self.__tab.frame.addTag(tag)

        def removeTag(self, path=None, tag=None, show=False):
            if not path: path = self.getFile()
            self.tagBase.removeTag(path, tag)
            self.__tab.frame.removeTag(tag, show)
        
        def getTagFiles(self, tag):
            return self.tagBase.getFilesForTag(tag)

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

        @functools.lru_cache
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
            return self.settings.get(key, default)
        
        def set(self, key, value):
            self.settings[key] = value
        
        def erase(self, key):
            if key in self.settings:
                del self.settings[key]
        
        def has(self, key):
            return key in self.settings
        
        def fromFile(self, f: "VtAPI.File"):
            self.content = "".join(f.read())
            self.settings = json.loads(self.content)
            return self

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
        def __init__(self, path: str = None, encoding="utf-8"):
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
            os.makedirs(self.path)
        
        def normalize(self):
            return os.path.normpath(self.path)
        
        def dir(self):
            return os.listdir(self.path)
        
        def remove(self):
            os.remove(self.path)

    class File:
        def __init__(self, path: str = None, encoding="utf-8"):
            self.path = path
            self.encoding = encoding

        def __str__(self):
            return self.path
    
        def read(self, chunk=1024):
            if self.encoding == "binary":
                self.mode = "rb"
            else:
                self.mode = "r"
            if self.exists() and not os.path.isdir(self.path):
                lines = []
                with open(self.path, self.mode, encoding=None if self.mode == "rb" else self.encoding, errors="ignore") as file:
                    while chunk_data := file.read(int(chunk)):
                        lines.append(chunk_data)
                return lines

        def write(self, content, chunk=1024):
            chunk = int(chunk)
            total_length = len(content)
            with open(self.path, 'w', encoding=self.encoding) as file:
                for i in range(0, total_length, chunk):
                    chunkk = content[i:i + chunk]
                    file.write(str(chunkk))

        def exists(self): return os.path.isfile(self.path)

        def create(self, rewrite=False):
            if rewrite:
                open(self.path, "a+", encoding=self.encoding).close()
            elif not self.exists(): open(self.path, "a", encoding=self.encoding).close()

    class Theme:
        def __init__(self, name: str | None = None, path: str | None = None):
            self.name = name
            self.path = path

        def __str__(self):
            return self.path

        def use(self, window: "VtAPI.Window" = None):
            window.setTheme(self.path)

        def exists(self):
            return os.path.isfile(self.path)

    class Plugin:
        def __init__(self, api:"VtAPI", name: str, path: str):
            self.api: VtAPI = api
            self.name = name
            self.path = path

        def __str__(self):
            return self.path

        def load(self, window):
            window._Window__mw.pl.plugins[self.name] = self.path
            window._Window__mw.pl.loadPlugin(self.name)

        class ApplicationCommand(QtCore.QObject):
            def __init__(self, api: "VtAPI"):
                super().__init__()
                self.api = api

            def run(self): raise NotImplementedError("You must rewrite 'run' function of your command")

            def description(self): ...

        class WindowCommand(ApplicationCommand):
            def __init__(self, api: "VtAPI", window: "VtAPI.Window"):
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
            def __init__(self, api: "VtAPI", view: "VtAPI.View"):
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
                super.__init__(*args, **kwargs)
        
        class Action(QtGui.QAction):
            def __init__(self, *args, **kwargs):
                super.__init__(*args, **kwargs)

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
                    try: slot(*args, **kwargs)
                    except Exception as e: slot()

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
                        self.__window.setWindowTitle(self.__windowApi.appName)
                else:
                    self.__window.setWindowTitle(self.__windowApi.appName)
            except Exception as e:
                self.__window.setWindowTitle(self.__windowApi.appName)
                self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Error when updating tabs: {}").format(e))

        def updateEncoding(self):
            e = self.__windowApi.activeWindow.activeView.getEncoding()
            self.__window.statusBar().encodingLabel.setText(e.upper())

    @property
    def activeWindow(self) -> Window:
        return self.__activeWindow
    
    @activeWindow.setter
    def activeWindow(self, w: Window):
        self.__activeWindow = w
        return w

    @property
    def windows(self):
        return tuple(self.__windows)
    
    def addWindow(self, window: Window):
        self.__windows.append(window)

    @staticmethod
    def isDir(path): return os.path.isdir(path)

    @staticmethod
    def importModule(name):
        return importlib.import_module(name)

    @staticmethod
    def setTimeout(function, delay):
        QtCore.QTimer.singleShot(delay, function)

    @staticmethod
    async def setTimeout_async(function, delay):
        await asyncio.sleep(delay / 1000)
        function()

    @staticmethod
    def version():
        return "1.3"

    @staticmethod
    def platform():
        current_platform = platform.system()
        if current_platform == "Darwin":
            return "OSX"
        return current_platform

    @staticmethod
    def arch():
        if sys.maxsize > 2**32:
            if platform.system() == "Windows":
                return "x64"
            else:
                return "amd64"
        else:
            return "x86"

    @staticmethod
    def replaceConsts(data, constants):
        stack = [data]
        result = data

        while stack:
            current = stack.pop()
            
            if isinstance(current, dict):
                items = list(current.items())
                for key, value in items:
                    if isinstance(value, (dict, list)):
                        stack.append(value)
                    elif isinstance(value, str):
                        try:
                            current[key] = value.format(**constants)
                        except KeyError as e:
                            print(f"Missing key in constants: {e}")
                        except ValueError:
                            current[key] = value.replace('{', '{{').replace('}', '}}')
                        
            elif isinstance(current, list):
                items = list(current)
                for i, item in enumerate(items):
                    if isinstance(item, (dict, list)):
                        stack.append(item)
                    elif isinstance(item, str):
                        try:
                            current[i] = item.format(**constants)
                        except KeyError as e:
                            print(f"Missing key in constants: {e}")
                        except ValueError:
                            current[i] = item.replace('{', '{{').replace('}', '}}')

        return result

    @staticmethod
    def findKey(p, d):
        current = d
        for key in p.split("."):
            if isinstance(current, dict) and key in current: current = current[key]
            else: return None
        return current

    @staticmethod
    def addKey(p, value, d):
        path = p.split(".")
        current = d
        for key in path[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[path[-1]] = value

    @staticmethod
    def replacePaths(data):
        def replace_var(match):
            env_var = match.group(1)
            return os.getenv(env_var, f'%{env_var}%')
        return re.sub(r'%([^%]+)%', replace_var, data)

    @staticmethod
    def defineLocale():
        return QtCore.QLocale.system().name().split("_")[0]

    def packagesPath(self):
        return self.packagesDir