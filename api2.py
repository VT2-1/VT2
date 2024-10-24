from PyQt6 import QtWidgets, QtCore, QtGui
import os, sys, configparser, json, importlib, re, subprocess, platform, inspect
import importlib.util
import PyQt6
import os, json
import builtins

from addit import PackageManager


BLOCKED = [
    "PyQt6"
]

oldCoreApp = QtCore.QCoreApplication


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

def importModule(path, n):
    spec = importlib.util.spec_from_file_location(n, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[n] = module
    spec.loader.exec_module(module)
    return module

class PluginManager:
    def __init__(self, plugin_directory: str, w):
        self.plugin_directory = plugin_directory
        self.__window = w
        self.pm = PackageManager(w, self.plugin_directory)
        self.__menu_map = {}
        self.commands = []
        self.shortcuts = []
        self.regCommands = {}
        self.dPath = None

    def load_plugins(self):
        try:
            self.dPath = os.getcwd()
            sys.path.insert(0, self.plugin_directory)
            for plugDir in os.listdir(self.plugin_directory):
                fullPath = os.path.join(self.plugin_directory, plugDir)
                os.chdir(fullPath)
                if os.path.isdir(fullPath) and os.path.isfile(f"config.vt-conf"):
                    module = None
                    info = self.initPlugin(os.path.join(fullPath, "config.vt-conf"))
                    if self.mainFile:
                        pyFile = self.mainFile
                        try:
                            with SafeImporter(BLOCKED):
                                # sys.modules['PyQt6.QtWidgets'].QApplication = BlockedQApplication
                                # sys.modules['PyQt6.QtCore'].QCoreApplication = BlockedQApplication
                                sys.path.insert(0, fullPath)
                                module = importModule(pyFile, self.name + "Plugin")
                                if hasattr(module, "initAPI"):
                                    module.initAPI(self.__window.api)
                                    self.newRegCommands(module)
                                # sys.modules['PyQt6.QtCore'].QCoreApplication = oldCoreApp
                        except Exception as e:
                            self.__window.api.activeWindow.setLogMsg(f"Failed load plugin '{self.name}' commands: {e}")
                        finally:
                            sys.path.pop(0)
                    if self.menuFile:
                        self.loadMenu(self.menuFile, module)
                    if self.scFile:
                        try:
                            self.registerShortcuts(json.load(open(self.scFile, "r+")))
                        except Exception as e:
                            self.__window.api.activeWindow.setLogMsg(
                                f"Failed load shortcuts for '{self.name}' from '{self.scFile}': {e}")

        finally:
            os.chdir(self.dPath)

    def loadMenu(self, f, module=None):
        try:
            menuFile = json.load(open(f, "r+"))
            localeDir = os.path.join(os.path.dirname(f), "locale")
            if os.path.isdir(localeDir): self.__window.translate(localeDir)
            for menu in menuFile:
                if menu == "menuBar" or menu == "mainMenu":
                    self.parseMenu(menuFile.get(menu), self.__window.menuBar(), module, "MainMenu")
                elif menu == "textContextMenu":
                    self.parseMenu(menuFile.get(menu), self.__window.textContextMenu, module, "TextContextMenu")
                elif menu == "tabBarContextMenu":
                    self.parseMenu(menuFile.get(menu), self.__window.tabBarContextMenu, module, "TabBarContextMenu")
        except Exception as e:
            self.__window.api.activeWindow.setLogMsg(f"Failed load menu from '{f}': {e}")

    def initPlugin(self, path):
        config = json.load(open(path, "r+"))

        self.name = config.get('name', 'Unknown')
        self.version = config.get('version', '1.0')
        self.mainFile = config.get('main', '')
        self.menuFile = config.get('menu', '')
        self.scFile = config.get('sc', '')

    def parseMenu(self, data, parent, pl=None, localemenu="MainMenu"):
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
                    menu = self.__menu_map.setdefault(menu_id, QtWidgets.QMenu(QtCore.QCoreApplication.translate("MainMenu", item.get('caption', 'Unnamed')), self.__window))
                    menu.setObjectName(item.get('id'))
                    parent.addMenu(menu)
                    if 'children' in item:
                        self.parseMenu(item['children'], menu, pl)
            else:
                action = QtGui.QAction(QtCore.QCoreApplication.translate(localemenu, item.get('caption', 'Unnamed')), self.__window)
                if 'shortcut' in item:
                    if not item['shortcut'] in self.shortcuts:
                        action.setShortcut(QtGui.QKeySequence(item['shortcut']))
                        action.setStatusTip(item['shortcut'])
                        self.shortcuts.append(item['shortcut'])
                    else:
                        self.__window.api.activeWindow.setLogMsg(
                            f"Shortcut '{item['shortcut']}' for function '{item['command']}' is already used.")

                if 'command' in item:
                    args = item.get('command').get("args")
                    kwargs = item.get('command').get("kwargs")
                    self.commands.append(
                        {"action": action, "command": item['command'], "plugin": pl, "args": args, "kwargs": kwargs})
                    if 'checkable' in item:
                        action.setCheckable(item['checkable'])
                        if 'checked' in item:
                            action.setChecked(item['checked'])
                    action.triggered.connect(lambda checked, cmd=item['command']:
                                             self.executeCommand(
                                                 cmd,
                                                 checked=checked
                                             )
                                             )
                parent.addAction(action)

    def executeCommand(self, c, *args, **kwargs):
        ckwargs = kwargs
        command = c
        c = self.regCommands.get(command.get("command"))
        print(c)
        if c:
            try:
                args = command.get("args")
                kwargs = command.get("kwargs")
                checkable = command.get("checkable")
                action = c.get("action")
                if action and action.isCheckable():
                    checked_value = ckwargs.get("checked")

                    if checked_value is not None:
                        action.setChecked(checked_value)
                    else:
                        new_checked_state = not action.isChecked()
                        action.setChecked(new_checked_state)
                cl = c.get("command")
                print(cl)
                if issubclass(cl, VtAPI.Plugin.TextCommand):
                    c = cl(self.__window.api, self.__window.api.activeWindow.activeView)
                elif issubclass(cl, VtAPI.Plugin.WindowCommand):
                    c = cl(self.__window.api, self.__window.api.activeWindow)
                elif issubclass(cl, VtAPI.Plugin.ApplicationCommand):
                    c = cl(self.__window.api)
                out = c.run(*args or [], **kwargs or {})
                self.__window.api.activeWindow.setLogMsg(f"Executed command '{command}' with args '{args}', kwargs '{kwargs}'")
                if out:
                    self.__window.api.activeWindow.setLogMsg(f"Command '{command}' returned '{out}'")
            except Exception as e:
                self.__window.api.activeWindow.setLogMsg(f"Found error in '{command}' - '{e}'.\nInfo: {c}")
                print(e)
        else:
            self.__window.api.activeWindow.setLogMsg(f"Command '{command}' not found")

    def registerShortcuts(self, data):
        for sh in data:
            keys = sh.get("keys")
            command = sh.get("command")
            cmd_name = command.get("command")

            if keys not in self.shortcuts:
                action = QtGui.QAction(self.__window)
                for key in keys:
                    action.setShortcut(QtGui.QKeySequence(key))
                    action.setStatusTip(key)
                    self.shortcuts.append(key)

                action.triggered.connect(lambda checked, cmd=command:
                                         self.executeCommand(cmd)
                                         )
                self.__window.addAction(action)
                self.__window.api.activeWindow.setLogMsg(f"Shortcut '{keys}' for function '{cmd_name}' registered.")
            else:
                self.__window.api.activeWindow.setLogMsg(f"Shortcut '{keys}' for function '{cmd_name}' already used.")

    def registerCommand(self, commandInfo):
        command = commandInfo.get("command")
        if type(command) == str:
            commandN = command
        elif inspect.isclass(command):
            commandN = command
        else:
            commandN = command.get("command")
        pl = commandInfo.get("plugin")
        action = commandInfo.get("action")

        args = commandInfo.get("args", [])
        kwargs = commandInfo.get("kwargs", {})

        if 'shortcut' in commandInfo:
            if not commandInfo['shortcut'] in self.shortcuts:
                action = QtGui.QAction("", self.__window)
                action.setShortcut(QtGui.QKeySequence(commandInfo['shortcut']))
                self.shortcuts.append(commandInfo['shortcut'])

        if pl:
            try:
                command_func = getattr(pl, commandN)
                self.regCommands[commandN] = {
                    "action": action,
                    "command": command_func,
                    "args": args,
                    "kwargs": kwargs,
                    "plugin": pl,
                }
            except (ImportError, AttributeError, TypeError) as e:
                self.__window.api.activeWindow.setLogMsg(f"Error when registering '{commandN}' from '{pl}': {e}")
        else:
            if not inspect.isclass(commandN):
                command_func = getattr(sys.modules[__name__], commandN, None)
            else:
                command_func = commandN
            if command_func:
                self.regCommands[commandN] = {
                    "action": action,
                    "command": command_func,
                    "args": args,
                    "kwargs": kwargs,
                    "plugin": None,
                }
            else:
                self.__window.api.activeWindow.setLogMsg(f"Command '{commandN}' not found")

    def registerCommands(self):
        for commandInfo in self.commands:
            command = commandInfo.get("command")
            if type(command) == str:
                commandN = command
            else:
                commandN = command.get("command")
            pl = commandInfo.get("plugin")
            action = commandInfo.get("action")

            args = commandInfo.get("args", [])
            kwargs = commandInfo.get("kwargs", {})
            checkable = commandInfo.get("checkable", False)

            if pl:
                try:
                    command_func = getattr(pl, commandN)
                    self.regCommands[commandN] = {
                        "action": action,
                        "command": command_func,
                        "args": args,
                        "kwargs": kwargs,
                        "plugin": pl,
                    }
                except (ImportError, AttributeError, TypeError) as e:
                    self.__window.api.activeWindow.setLogMsg(f"Error when registering '{commandN}' from '{pl}': {e}")
            else:
                command_func = getattr(sys.modules[__name__], commandN, None)
                if command_func:
                    self.regCommands[commandN] = {
                        "action": action,
                        "command": command_func,
                        "args": args,
                        "kwargs": kwargs,
                        "plugin": None,
                    }
                else:
                    self.__window.api.activeWindow.setLogMsg(f"Command '{commandN}' not found")
    def newRegCommands(self, m):
        classes = inspect.getmembers(m, inspect.isclass)
        for cl in classes:
            self.commands.append(cl)

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

    def clearCache(self):
        del self.dPath, self.commands, self.shortcuts

class VtAPI:
    def __init__(self):
        self.__app = QtWidgets.QApplication.instance()
        self.appName = self.__app.applicationName()
        self.windows = []
        self.activeWindow = None

    class Window:
        def __init__(self, api, views=None, activeView=None, qmwclass: QtWidgets.QMainWindow=None):
            self.__api = api
            self.__mw = qmwclass
            self.signals = VtAPI.Signals(self.__mw)
            self.views = views or []
            self.activeView = activeView

            self.__api.windows.append(self)

        def newFile(self):
            self.__mw.addTab()
            tab = self.__mw.tabWidget.currentWidget()
        
        def openFiles(self, files):
            self.__mw.pl.executeCommand({"command": "openFile", "args": files})
        
        def saveFile(self, view=False):
            self.__mw.pl.executeCommand({"command": "saveFile"})
        
        def activeView(self):
            return self.activeView
        
        def views(self):
            return self.views
        
        def focus(self, view):
            self.activeView = view
        
        def runCommand(self, command):
            self.__mw.pl.executeCommand(command)
        
        def showQuickPanel(self, items, on_select, on_highlight=None, flags=0, selected_index=-1):
            print(f"Showing quick panel with items: {items}")
        
        def showInputPanel(self, prompt, initial_text, on_done, on_change=None, on_cancel=None):
            print(f"Showing input panel with prompt: {prompt} and initial text: {initial_text}")
        
        def getCommand(self, name):
            return self.__mw.pl.regCommands.get(name)

        def getTheme(self):
            return self.__mw.themeFile

        def setTheme(self, theme):
            themePath = os.path.join(self.__mw.themesDir, theme)
            if os.path.isfile(themePath):
                self.__mw.setStyleSheet(open(themePath, "r+").read())

        def getLog(self):
            return self.__mw.logger.log

        def setLogMsg(self, msg):
            self.__mw.logger.log += f"\n{msg}"

        def getTreeModel(self):
            return self.model

        def getModelElement(self, i):
            return self.model.filePath(i)

        def setTreeWidgetDir(self, dir):
            self.model = QtGui.QFileSystemModel()
            self.model.setRootPath(dir)
            self.__mw.treeView.setModel(self.model)
            self.__mw.treeView.setRootIndex(self.model.index(dir))
            return self.model

        def setTheme(self, theme):
            themePath = os.path.join(self.__mw.themesDir, theme)
            if os.path.isfile(themePath):
                self.__mw.setStyleSheet(open(themePath, "r+").read())

        def setTab(self, i):
            self.__mw.tabWidget.setCurrentIndex(i - 1)

        def updateMenu(self, menu, data):
            menuClass = self.__mw.pl.findMenu(self.__mw.menuBar(), menu)
            if menu:
                self.__mw.pl.clearMenu(self.__mw.menuBar(), menu)
                self.__mw.pl.parseMenu(data, menuClass)

        def addDockWidget(self, areas, dock: 'VtAPI.Widgets.DockWidget'):
            self.__mw.addDockWidget(areas, dock)
        
        def isDockWidget(self, area):
            dock_widgets = self.__mw.findChildren(QtWidgets.QDockWidget)
            for dock in dock_widgets:
                if self.__mw.dockWidgetArea(dock) == area: return dock

        def loadThemes(self, menu):
            themeMenu = self.__mw.pl.findMenu(menu, "themes")
            if themeMenu:
                themes = []
                for theme in os.listdir(self.__mw.themesDir):
                    if os.path.isfile(os.path.join(self.__mw.themesDir, theme)):
                        themes.append({"caption": theme, "command": {"command": f"setTheme", "kwargs": {"theme": theme}}})
                self.updateMenu("themes", themes)

    class View:
        def __init__(self, api, window, qwclass=None, text="", syntaxFile=None, file_name=None, read_only=False):
            self.__api = api
            self.window = window
            self.__tab = qwclass
            self.__tabWidget = self.__tab.parentWidget().parentWidget()
            self.text = text
            self.syntaxFile = syntaxFile
            self.file_name = file_name
            self.read_only = read_only
            self.tab_title = None
            self.tab_encoding = None
        
        def tabIndex(self):
            return self.__tabWidget.currentIndex()

        def window(self):
            return self.window

        def getTitle(self):
            return self.__tabWidget.tabText(self.__tabWidget.indexOf(self.__tab))

        def setTitle(self, text):
            return self.__tabWidget.setText(self.__tabWidget.indexOf(self.__tab), text)

        def getText(self):
            text = self.__tab.textEdit.toPlainText()
            return text

        def getHtml(self):
            text = self.__tab.textEdit.toHtml()
            return text

        def setText(self, text):
            self.__tab.textEdit.setText(text)
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
            self.__tabWidget.tabBar().setTabSaved(self.__tab or self.__tabWidget.currentWidget(), b)
            return b

        def size(self):
            return len(self.__tab.textEdit.toPlainText())

        def substr(self, region):
            return self.__tab.textEdit.toPlainText()[region.begin():region.end()]

        def sel(self):
            pass

        def insert(self, point, string):
            t = self.__tab.textEdit.toPlainText()
            lines = self.text.splitlines()
            line_index = point.x
            char_index = point.y
            
            point = sum(len(lines[i]) + 1 for i in range(line_index)) + char_index
            self.__tab.textEdit.setPlainText(t[:point] + string + t[point:])
        
        def erase(self, region):
            t = self.__tab.textEdit.toPlainText()
            self.__tab.textEdit.setPlainText(t[:region.begin()] + t[region.end():])
        
        def replace(self, region, string):
            t = self.__tab.textEdit.toPlainText()
            self.__tab.textEdit.setPlainText(t[:region.begin()] + string + t[region.end():])

        def find(self, pattern, start_point, flags=0):
            pass

        def findAll(self, pattern, flags=0):
            pass

        def setSyntaxFile(self, syntaxFilePath):
            self.syntaxFile = syntaxFilePath

        def settings(self):
            pass

        def fileName(self):
            return self.fileName

        def isDirty(self):
            return self.__window.tabWidget.isSaved(self.__tab)

        def isReadOnly(self):
            return self.read_only

        def getTextSelection(self):
            return self.__tab.textEdit.textCursor().selectedText()

        def getTextCursor(self):
            return self.__tab.textEdit.textCursor()

        def setTextSelection(self, s, e):
            cursor = self.__tab.textEdit.textCursor()
            cursor.setPosition(s)
            cursor.setPosition(e, QtGui.QTextCursor.MoveMode.KeepAnchor)
            self.__tab.textEdit.setTextCursor(cursor)

        def getCompletePos(self):
            current_text = self.__tab.textEdit.toPlainText()
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
            self.__tab.textEdit.highLighter.highlightingRules = hl

        def rehighlite(self):
            self.__tab.textEdit.highLighter.rehighlight()

        def show_popup(self, content, flags=0, location=-1, max_width=320, max_height=240, on_navigate=None, on_hide=None):
            self.content = content
            self.flags = flags
            self.location = location
            self.max_width = max_width
            self.max_height = max_height
            self.on_navigate = on_navigate
            self.on_hide = on_hide

            self.dialog = QtWidgets.QDialog()
            self.dialog.setWindowFlags(self.flags)
            self.dialog.setMaximumWidth(self.max_width)
            self.dialog.setMaximumHeight(self.max_height)

            self.dialog.setLayout(self.content)

            self.dialog.exec()

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

        def get(self, key, default=None):
            return self.settings.get(key, default)
        
        def set(self, key, value):
            self.settings[key] = value
        
        def erase(self, key):
            if key in self.settings:
                del self.settings[key]
        
        def has(self, key):
            return key in self.settings

    class Dialogs:
        def infoMessage(string):
            QtWidgets.QMessageBox.information(None, "Message", string)
        def warningMessage(string):
            QtWidgets.QMessageBox.warning(None, "Warning", string)
        def errorMessage(string):
            QtWidgets.QMessageBox.critical(None, "Error", string)

        def okCancelDialog(string):
            result = QtWidgets.QMessageBox.question(None, "Confirmation", string,
                                        QtWidgets.QMessageBox.StandardButton.Ok | QtWidgets.QMessageBox.StandardButton.Cancel,
                                        QtWidgets.QMessageBox.StandardButton.Cancel)
            return result == QtWidgets.QMessageBox.StandardButton.Ok

        def yesNoCancelDialog(string):
            result = QtWidgets.QMessageBox.question(None, "Confirmation", string,
                                        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No | QtWidgets.QMessageBox.StandardButton.Cancel,
                                        QtWidgets.QMessageBox.StandardButton.Cancel)
            if result == QtWidgets.QMessageBox.StandardButton.Yes:
                return "yes"
            elif result == QtWidgets.QMessageBox.StandardButton.No:
                return "no"
            else:
                return "cancel"

        def openFileDialog(e=None):
            dlg = QtWidgets.QFileDialog.getOpenFileNames(None, "Open File", "", "All Files (*);;Text Files (*.txt)")
            return dlg

        def saveFileDialog(e=None):
            dlg = QtWidgets.QFileDialog.getSaveFileName()
            return dlg

        def openDirDialog(self, e=None):
            dlg = QtWidgets.QFileDialog.getExistingDirectory(
                self.__window.treeView,
                caption="VarTexter - Get directory",
            )
            return str(dlg)

    class Plugin:
        class TextCommand:
            def __init__(self, api, view):
                self.api = api
                self.view = view

            def run(self, edit):
                ...
            
            def is_enabled(self):
                pass
            
            def is_visible(self):
                pass
            
            def description(self):
                pass

        class WindowCommand:
            def __init__(self, api, window):
                self.api = api
                self.window = window

            def run(self):
                ...
            
            def is_enabled(self):
                pass
            
            def is_visible(self):
                pass
            
            def description(self):
                pass

        class ApplicationCommand:
            def __init__(self, api):
                self.api = api

            def run(self):
                ...
            
            def is_enabled(self):
                pass
            
            def is_visible(self):
                pass
            
            def description(self):
                pass

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

    class Signals(QtCore.QObject):
        commandsLoaded = QtCore.pyqtSignal()
        tabClosed = QtCore.pyqtSignal(int, str)
        tabCreated = QtCore.pyqtSignal()
        tabChanged = QtCore.pyqtSignal()
        textChanged = QtCore.pyqtSignal()
        windowClosed = QtCore.pyqtSignal()

        treeWidgetClicked = QtCore.pyqtSignal(QtCore.QModelIndex)
        treeWidgetDoubleClicked = QtCore.pyqtSignal(QtCore.QModelIndex)
        treeWidgetActivated = QtCore.pyqtSignal()

        def __init__(self, w):
            super().__init__(w)
            self.__window = w

            self.__window.treeView.doubleClicked.connect(self.onDoubleClicked)

        def tabChngd(self, index):
            if index > -1:
                self.__window.setWindowTitle(
                    f"{os.path.normpath(self.__window.api.Tab.getTabFile(index) or 'Untitled')} - {self.__window.appName}")
                if index >= 0: self.__window.encodingLabel.setText(self.__window.tabWidget.widget(index).encoding)
                self.updateEncoding()
            else:
                self.__window.setWindowTitle(self.__window.appName)
            self.tabChanged.emit()

        def updateEncoding(self):
            e = self.__window.api.Tab.getTabEncoding(self.__window.api.Tab.currentTabIndex())
            self.__window.encodingLabel.setText(e)

        def onDoubleClicked(self, index):
            self.treeWidgetDoubleClicked.emit(index)

        def onClicked(self, index):
            self.treeWidgetClicked.emit(index)

        def onActivated(self):
            self.treeWidgetActivated.emit()

    class Widgets:
        class DockWidget(QtWidgets.QDockWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.__window = None

            def parent(self):
                return None

            def window(self):
                return None

    def activeWindow(self) -> Window:
        return self.activeWindow

    def windows(self):
        return self.windows

    def loadSettings(self, name):
        pass

    def saveSettings(self, name):
        pass

    def importModule(self, name):
        return importlib.import_module(name)

    def statusMessage(self, string):
        print(f"Status: {string}")

    def setTimeout(self, function, delay):
        QtCore.QTimer.singleShot(delay, function)

    def setTimeout_async(self, function, delay):
        self.setTimeout(function, delay)

    def scoreSelector(self, location, scope):
        return 100

    def version(self):
        return "4.0"

    def platform(self):
        return sys.platform

    def arch(self):
        if sys.maxsize > 2**32:
            if platform.system() == "Windows":
                return "x64"
            else:
                return "amd64"
        else:
            return "x86"

    def packagesPath(self):
        return "/"

    def installed_packagesPath(self):
        return "/path/to/installed/packages"

class ConsoleWidget(VtAPI.Widgets.DockWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.setWindowTitle(self.api.appName+" - Console")
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.setAllowedAreas(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea)
        self.consoleWidget = QtWidgets.QWidget()
        self.consoleWidget.setObjectName("consoleWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.consoleWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.textEdit = QtWidgets.QTextEdit(parent=self.consoleWidget)
        self.textEdit.setReadOnly(True)
        self.textEdit.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
        self.textEdit.setObjectName("consoleOutput")
        self.verticalLayout.addWidget(self.textEdit)
        self.lineEdit = QtWidgets.QLineEdit(parent=self.consoleWidget)
        self.lineEdit.setMouseTracking(False)
        self.lineEdit.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.lineEdit.setCursorMoveStyle(QtCore.Qt.CursorMoveStyle.LogicalMoveStyle)
        self.lineEdit.setObjectName("consoleCommandLine")
        self.verticalLayout.addWidget(self.lineEdit)
        self.setWidget(self.consoleWidget)
        self.lineEdit.returnPressed.connect(self.sendCommand)
    def sendCommand(self):
        text = self.lineEdit.text()
        if text:
            if text.startswith("vtapi"):
                if len(text.split(".")) == 2:
                    apiCommand = text.split(".")[-1] 
                    if hasattr(self.window.api, apiCommand):
                        self.api.activeWindow.setLogMsg(str(getattr(self.window.api, apiCommand)()))
                self.api.activeWindow.setLogMsg(str(self.window.api))
                self.lineEdit.clear()
            else:
                self.api.activeWindow.runCommand({"command": self.lineEdit.text()})
                self.lineEdit.clear()
    def closeEvent(self, e):
        self.api.activeWindow.runCommand({"command": "LogConsoleCommand"})
        e.ignore()

class LogConsoleCommand(VtAPI.Plugin.WindowCommand):
    def run(self, checked=None):
        if not self.api.activeWindow.isDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea):
            self.console = ConsoleWidget(self.api)
            self.console.textEdit.append(self.window.getLog())
            self.window.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.console)
        else:
            self.console = self.window.isDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea)
            self.console.deleteLater()