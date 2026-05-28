from PySide6 import QtWidgets, QtGui
import os, sys, importlib, inspect, builtins, traceback, json, uuid
import importlib.util
from multiprocessing import Pipe, Process
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


class SandboxedPluginProcess:
    def __init__(self, manifest, plugin_file, window_api):
        self.manifest = manifest
        self.plugin_file = plugin_file
        self.window_api = window_api
        self.name = manifest.get("name", "Unknown")
        self.commands = set(manifest.get("commands", []))
        self.timeout_ms = int(manifest.get("timeoutMs", 3000))
        self.parent_conn, child_conn = Pipe()
        from plugin_sandbox import run_child
        self.process = Process(
            target=run_child,
            args=(
                child_conn,
                plugin_file,
                json.dumps(manifest),
                int(manifest.get("memoryMb", 64)),
                int(manifest.get("cpuSeconds", 2)),
            ),
            daemon=True,
        )
        self.process.start()
        child_conn.close()
        self._request_id = 0

    def __str__(self):
        return f"sandbox:{self.name}"

    def start(self):
        self._drain_until_ready()
        return self

    def _drain_until_ready(self):
        while self.parent_conn.poll(self.timeout_ms / 1000):
            msg = self.parent_conn.recv()
            if self._handle_event(msg):
                continue
            if msg.get("type") == "ready":
                return
            if msg.get("type") == "error":
                raise RuntimeError(msg.get("message"))
        raise TimeoutError(f"Sandboxed plugin '{self.name}' did not become ready")

    def _handle_event(self, msg):
        if not isinstance(msg, dict) or msg.get("type") != "event":
            return False
        event = msg.get("event")
        payload = msg.get("payload") or {}
        if event == "log":
            level = str(payload.get("level", "INFO")).upper()
            color = getattr(VtAPI.Color, level, VtAPI.Color.INFO)
            self.window_api.activeWindow.setLogMsg(f"[{self.name}] {payload.get('message', '')}", color)
        elif event == "status_message":
            self.window_api.activeWindow.statusMessage(str(payload.get("message", "")), int(payload.get("timeout", 0)))
        elif event == "register_command":
            command_name = str(payload.get("name"))
            if command_name:
                self.commands.add(command_name)
        return True

    def run_command(self, command, args=None, kwargs=None):
        if command not in self.commands:
            raise ValueError(f"Command '{command}' is not declared by sandboxed plugin '{self.name}'")
        self._request_id += 1
        request_id = str(uuid.uuid4())
        self.parent_conn.send({
            "type": "run",
            "id": request_id,
            "command": command,
            "args": args or [],
            "kwargs": kwargs or {},
        })
        while self.parent_conn.poll(self.timeout_ms / 1000):
            msg = self.parent_conn.recv()
            if self._handle_event(msg):
                continue
            if msg.get("type") == "result" and msg.get("id") == request_id:
                if msg.get("ok"):
                    return msg.get("result")
                raise RuntimeError(msg.get("error"))
            if msg.get("type") == "error":
                raise RuntimeError(msg.get("message"))
        self.stop(force=True)
        raise TimeoutError(f"Sandboxed command '{command}' timed out")

    def stop(self, force=False):
        try:
            if self.process.is_alive() and not force:
                self.parent_conn.send({"type": "shutdown"})
                self.process.join(timeout=1)
        except Exception:
            force = True
        if force and self.process.is_alive():
            self.process.kill()
        self.parent_conn.close()

class PluginManager:
    def __init__(self, plugin_directory: str, w):
        self.plugin_directory = plugin_directory
        self.plugins = {}
        self.__window: QtWidgets.QMainWindow = w
        self.__windowApi: VtAPI = self.__window.api
        self.__menu_map = {}
        self.shortcuts = []
        self.regCommands = {}
        self.sandboxedPlugins = {}
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
            try:
                plugin_dirs = VtAPI.Path(self.plugin_directory).dir()
            finally:
                if sys.path and sys.path[0] == self.plugin_directory:
                    sys.path.pop(0)
            for plugDir in plugin_dirs:
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
        self.module = None
        if not fullPath:
            return None
        VtAPI.Path.chdir(fullPath)
        if VtAPI.Path(fullPath).isDir() and VtAPI.Path(f"config.vt-conf").isFile():
            self.initPlugin(VtAPI.Path.joinPath(fullPath, "config.vt-conf"))
            if self.mainFile:
                pyFile = self.mainFile
                plugin_file = VtAPI.Path.joinPath(fullPath, pyFile)
                try:
                    if self.sandbox:
                        manifest = {
                            "name": self.name,
                            "version": self.version,
                            "commands": self.commands,
                            "timeoutMs": self.timeoutMs,
                            "memoryMb": self.memoryMb,
                            "cpuSeconds": self.cpuSeconds,
                        }
                        self.module = SandboxedPluginProcess(manifest, plugin_file, self.__windowApi).start()
                        self.sandboxedPlugins[self.name] = self.module
                        for command_name in self.module.commands:
                            self.registerCommand({"command": command_name, "plugin": self.module})
                    else:
                        with SafeImporter(BLOCKED):
                            sys.path.insert(0, fullPath)
                            self.module = self.importModule(plugin_file, self.name + "Plugin")
                            if hasattr(self.module, "initAPI"):
                                self.module.initAPI(self.__windowApi)
                    self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Loaded plugin '{}'").format(self.name), self.__windowApi.Color.SUCCESS)
                except Exception as e:
                    self.__windowApi.activeWindow.setLogMsg(self.__windowApi.activeWindow.translate("Failed load plugin '{}' commands: {}").format(self.name, e), self.__windowApi.Color.ERROR)
                    self.module = None
                finally:
                    if not self.sandbox and sys.path and sys.path[0] == fullPath:
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
        self.sandbox = config.get('sandbox', False)
        self.commands = config.get('commands', [])
        self.timeoutMs = config.get('timeoutMs', 3000)
        self.memoryMb = config.get('memoryMb', 64)
        self.cpuSeconds = config.get('cpuSeconds', 2)

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
                        self.shortcuts.extend(item["shortcut"])
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
                if inspect.isclass(cl) and issubclass(cl, VtAPI.Plugin.TextCommand):
                    cnd = cl(self.__windowApi, self.__windowApi.activeWindow.activeView)
                    out = cnd.run(*args or [], **kwargs or {})
                elif inspect.isclass(cl) and issubclass(cl, VtAPI.Plugin.WindowCommand):
                    cnd = cl(self.__windowApi, self.__windowApi.activeWindow)
                    out = cnd.run(*args or [], **kwargs or {})
                elif inspect.isclass(cl) and issubclass(cl, VtAPI.Plugin.ApplicationCommand):
                    cnd = cl(self.__windowApi)
                    out = cnd.run(*args or [], **kwargs or {})
                elif callable(cl):
                    out = cl(*args or [], **kwargs or {})
                else:
                    raise TypeError(f"Unsupported command type: {type(cl)!r}")
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
            commandN = command.__name__
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
                command_func = (lambda *a, _pl=pl, _command=commandN, **kw: _pl.run_command(_command, list(a), kw)) if isinstance(pl, SandboxedPluginProcess) else getattr(pl, commandN)
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
