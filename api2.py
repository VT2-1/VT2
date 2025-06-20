from PySide6 import QtWidgets, QtGui
import os, sys, importlib, inspect, builtins, traceback
import importlib.util
from functools import partial
from api import VtAPI

BLOCKED = [ # не позволяет добавить импорт сторонней версии PyQt|PySide. Защищает от вылета
    "PyQt6",
    "PyQt5",
    "PyQt4",
    "shiboken",
    "PySide2",
    "PySide6"
]

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
            for plugDir in VtAPI.Path(self.plugin_directory).dir():
                if self.__windowApi.Path(VtAPI.Path.joinPath(self.plugin_directory, plugDir)).isDir():
                    self.fullPath = VtAPI.Path.joinPath(self.plugin_directory, plugDir)
                    self.plugins[plugDir] = self.fullPath
            # self.__windowApi.activeWindow.setLogMsg(f"Modules {self.__windowApi.activeWindow.appName()} loading...")
            bP = self.plugins.get("Basic")
            if not bP:
                if self.__windowApi.activeWindow.getCommand("LoadBasicCommand"):
                    self.__windowApi.activeWindow.runCommand({"command": "LoadBasicCommand", "kwargs": {"url": "https://github.com/cherry220-v/Basic"}})
            else:
                self.loadPlugin("Basic")
                self.plugins.pop("Basic")
            for pl in self.plugins:
                self.loadPlugin(pl)
        except Exception as e:
            self.__windowApi.activeWindow.setLogMsg(e, self.__windowApi.Color.ERROR)
        finally:
            VtAPI.Path.chdir(self.dPath)

    def loadPlugin(self, name):
        self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Loading plugin '{}'").format(name))
        fullPath = self.plugins.get(name)
        VtAPI.Path.chdir(fullPath)
        if VtAPI.Path(fullPath).isDir() and VtAPI.Path(f"config.vt-conf").isFile():
            self.initPlugin(VtAPI.Path.joinPath(fullPath, "config.vt-conf"))
            if self.mainFile:
                pyFile = self.mainFile
                try:
                    with SafeImporter(BLOCKED):
                        sys.path.insert(0, fullPath)
                        self.module = self.importModule(pyFile, self.name + "Plugin")
                        if hasattr(self.module, "initAPI"):
                            self.module.initAPI(self.__windowApi)
                    self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Loaded plugin '{}'").format(self.name), self.__windowApi.Color.SUCCESS)
                except Exception as e:
                    self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Failed load plugin '{}' commands: {}").format(self.name, e), self.__windowApi.Color.ERROR)
                    self.module = None
                finally:
                    sys.path.pop(0)
            if self.menuFile:
                self.loadMenu(self.menuFile, module=self.module, path=fullPath)
            VtAPI.Path.chdir(self.__windowApi.getFolder("packages"))
            return self.module

    def loadMenu(self, f, module=None, path=None):
        try:
            menuFile = VtAPI.Settings().fromFile(VtAPI.File(f)).data()
            localeDir = VtAPI.Path.joinPath(path if path else "", "locale")
            if VtAPI.Path(localeDir).isDir():
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
        config = VtAPI.Settings().fromFile(VtAPI.File(path)).data()

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
                    else: action.triggered.connect(partial(self.__windowApi.activeWindow.runCommand, item["command"]))
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
                        value = self.__windowApi.findKey(c.get("checkedStatePath"), self.__windowApi.activeWindow.state())
                        if value in [True, False]:
                            if "restoring" in kwargs:
                                action.setChecked(value)
                            else:
                                action.setChecked(not value)
                cl = c.get("command")
                if issubclass(cl, VtAPI.Plugin.TextCommand):
                    cnd = cl(self.__windowApi, self.__windowApi.activeWindow.activeView)
                elif issubclass(cl, VtAPI.Plugin.WindowCommand):
                    cnd = cl(self.__windowApi, self.__windowApi.activeWindow)
                elif issubclass(cl, VtAPI.Plugin.ApplicationCommand):
                    cnd = cl(self.__windowApi)
                else:
                    cnd = VtAPI.Plugin.ApplicationCommand(self.__windowApi)
                    cnd.run = lambda: self.__windowApi.activeWindow.setLogMsg("ERROR", self.__windowApi.Color.ERROR)
                out = cnd.run(*args or [], **kwargs or {})
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
            self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("'{}' from '{}' loaded").format(commandN, pl), self.__windowApi.Color.BLUE)

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
                self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("'{}' from '{}' loaded").format(commandN, pl), self.__windowApi.Color.BLUE)
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
                self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("'{}' from '{}' loaded").format(commandN, pl), self.__windowApi.Color.BLUE)
            else:
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
