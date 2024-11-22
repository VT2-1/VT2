from PyQt6 import QtWidgets, QtCore, QtGui
import os, sys, json, importlib, re, platform, inspect, asyncio
import importlib.util
import os
import builtins
import traceback

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

class PluginManager:
    def __init__(self, plugin_directory: str, w):
        self.plugin_directory = plugin_directory
        self.plugins = {}
        self.__window: QtWidgets.QMainWindow = w
        self.__windowApi: VtAPI = self.__window.api
        self.__menu_map = {}
        self.shortcuts = []
        self.regCommands = {}
        self.dPath = None

    def importModule(self, path, n):
        spec = importlib.util.spec_from_file_location(n, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[n] = module
        spec.loader.exec_module(module)
        return module

    def loadPlugins(self):
        try:
            self.dPath = os.getcwd()
            sys.path.insert(0, self.plugin_directory)
            for plugDir in os.listdir(self.plugin_directory):
                self.fullPath = os.path.join(self.plugin_directory, plugDir)
                self.plugins[plugDir] = self.fullPath

            if self.plugins.get("Basic"):
                self.loadPlugin("Basic")
                self.plugins.pop("Basic")
            
            for pl in self.plugins:
                self.loadPlugin(pl)
        except Exception as e:
            print(e, self.__windowApi.ERROR)
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
                        sys.modules['PyQt6.QtWidgets'].QApplication = BlockedQApplication
                        sys.modules['PyQt6.QtCore'].QCoreApplication = BlockedQApplication
                        sys.path.insert(0, fullPath)
                        self.module = self.importModule(pyFile, self.name + "Plugin")
                        if hasattr(self.module, "initAPI"):
                            self.module.initAPI(self.__windowApi)
                        sys.modules['PyQt6.QtCore'].QCoreApplication = oldCoreApp
                except Exception as e:
                    self.__windowApi.activeWindow.setLogMsg(f"Failed load plugin '{self.name}' commands: {e}")
                finally:
                    sys.path.pop(0)
            if self.menuFile:
                self.loadMenu(self.menuFile, module=self.module, path=fullPath)

    def loadMenu(self, f, module=None, path=None):
        try:
            menuFile = json.load(open(f, "r+"))
            localeDir = os.path.join(path if module else "", "locale")
            if os.path.isdir(localeDir):
                self.__window.translate(localeDir)
            for menu in menuFile:
                if menu == "menuBar" or menu == "mainMenu":
                    self.parseMenu(menuFile.get(menu), self.__window.menuBar(), pl=module, localemenu="MainMenu")
                elif menu == "textContextMenu":
                    self.parseMenu(menuFile.get(menu), self.__window.textContextMenu, pl=module, localemenu="TextContextMenu")
                elif menu == "tabBarContextMenu":
                    self.parseMenu(menuFile.get(menu), self.__window.tabBarContextMenu, pl=module, localemenu="TabBarContextMenu")
        except Exception as e:
            self.__windowApi.activeWindow.setLogMsg(f"Failed load menu from '{f}': {e}")

    def initPlugin(self, path):
        config = json.load(open(path, "r+"))

        self.name = config.get('name', 'Unknown')
        self.version = config.get('version', '1.0')
        self.mainFile = config.get('main', '')
        self.menuFile = config.get('menu', '')

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
                    menu = self.__menu_map.setdefault(menu_id, QtWidgets.QMenu(oldCoreApp.translate("MainMenu", item.get('caption', 'Unnamed')), self.__window))
                    menu.setObjectName(item.get('id'))
                    parent.addMenu(menu)
                    if 'children' in item:
                        self.parseMenu(item['children'], menu, pl)
            else:
                action = QtGui.QAction(oldCoreApp.translate(localemenu, item.get('caption', 'Unnamed')), self.__window)
                if 'shortcut' in item:
                    if not item['shortcut'] in self.shortcuts:
                        action.setShortcut(QtGui.QKeySequence(item['shortcut']))
                        action.setStatusTip(item['shortcut'])
                        self.shortcuts.append(item['shortcut'])
                        self.__window.addAction(action)
                    else:
                        self.__windowApi.activeWindow.setLogMsg(
                            f"Shortcut '{item['shortcut']}' for function '{item['command']}' is already used.")

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
                    self.registerCommand(data)
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
                self.__windowApi.activeWindow.setLogMsg(f"Executed command '{command}' with args '{args}', kwargs '{kwargs}'")
                if out:
                    self.__windowApi.activeWindow.setLogMsg(f"Command '{command}' returned '{out}'", self.__windowApi.ERROR)
            except Exception as e:
                traceback.print_exc()
                self.__windowApi.activeWindow.setLogMsg(f"Found error in '{command}' - '{e}'.\nInfo: {c}", self.__windowApi.ERROR)
        else:
            self.__windowApi.activeWindow.setLogMsg(f"Command '{command}' not found")

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
                self.__windowApi.activeWindow.setLogMsg(f"Error when registering '{commandN}' from '{pl}': {e}")
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
                self.__windowApi.activeWindow.setLogMsg(f"Command '{commandN}' not found")

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
    def __init__(self, app=None):
        try:
            self.__app = QtWidgets.QApplication.instance()
        except:
            self.__app: QtWidgets.QApplication = app
        self.__windows = []
        self.activeWindow: VtAPI.Window | None = None

        self.STATEFILE = None

        self.INFO = ""
        self.WARNING = "yellow"
        self.ERROR = "red"

    class Window:
        def __init__(self, api, views=None, activeView=None, qmwclass: QtWidgets.QMainWindow | None = None):
            self.api: VtAPI = api
            self.__mw: QtWidgets.QMainWindow = qmwclass
            self.__signals: VtAPI.Signals = VtAPI.Signals(self.__mw)
            self.views = views or []
            self.activeView: VtAPI.View | None = activeView
            self.model = QtGui.QFileSystemModel()

        def newFile(self) -> 'VtAPI.View':
            self.__mw.ui.addTab()
            return self.activeView
        
        def openFiles(self, files):
            """Use command with name 'OpenFileCommand'"""
            self.runCommand({"command": "OpenFileCommand", "args": [files]})
        
        def saveFile(self, view=None, dlg=False):
            self.runCommand({"command": "SaveFileCommand", "kwargs": {"dlg": dlg}})
        
        def activeView(self) -> 'VtAPI.View':
            return self.activeView

        def views(self):
            return self.views
        
        @property
        def signals(self):
            return self.__signals

        def setTitle(self, s):
            self.__mw.setWindowTitle(f"{s} - {self.api.appName}")

        def focus(self, view):
            if view in self.views:
                self.__mw.tabWidget.setCurrentIndex(view.tabIndex())
                self.activeView = view

        def registerCommandClass(self, data):
            self.__mw.pl.registerClass(data)

        def registerCommand(self, data):
            self.__mw.pl.registerCommand(data)

        def runCommand(self, command):
            self.__mw.pl.executeCommand(command)
        
        def addToolBar(self, items, flags=[]):
            toolBar = QtWidgets.QToolBar()
            for action in items:
                if issubclass(action, QtGui.QAction):
                    self.__mw.addAction(action)
        
        def getCommand(self, name):
            return self.__mw.pl.regCommands.get(name)

        def getTheme(self):
            return self.__mw.themeFile

        def setTheme(self, theme):
            themePath = os.path.join(self.api.themesDir, theme)
            if os.path.isfile(themePath):
                self.__mw.setStyleSheet(open(themePath, "r+").read())
                self.__mw.themeFile = theme

        def getLog(self):
            return self.__mw.logger.log

        def setLogMsg(self, msg, t=""):
            msg = f"""<i style="color: {t};">{msg}</i>"""
            self.__mw.logger.log += f"<br>{msg}"

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

        def setTab(self, i):
            self.__mw.tabWidget.setCurrentIndex(i - 1)

        def updateMenu(self, menu, data):
            menuClass = self.__mw.pl.findMenu(self.__mw.menuBar(), menu)
            if menuClass:
                self.__mw.pl.clearMenu(self.__mw.menuBar(), menu)
                self.__mw.pl.parseMenu(data, menuClass)

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

        def statusMessage(self, text, timeout=None):
            self.__mw.statusbar.showMessage(text, timeout)

    class View:
        def __init__(self, api, window, qwclass=None):
            self.api: VtAPI = api
            self.__window: VtAPI.Window = window
            self.__tab: QtWidgets.QWidget = qwclass
            if self.__tab:
                self.id: str = self.__tab.objectName().split("-")[-1]
                self.__tabWidget: QtWidgets.QTabWidget = self.window()._Window__mw.ui.widgets.tabWidget
                self.tagBase = window._Window__mw.ui.tagBase
            else:
                self.id = None
                self.__tabWidget = None
                self.tagBase = None

        def __eq__(self, other):
            if not isinstance(other, VtAPI.View):
                return NotImplemented
            return self.id == other.id
        
        def id(self):
            return self.id

        def update(self):
            view = VtAPI.View(self.api, self.__window, qwclass=self.__tabWidget.currentWidget())
            view.id = self.__tabWidget.currentWidget().objectName().split("-")[-1]
            self.window().focus(view)

        def __hash__(self):
            return hash(self.tabIndex())

        def tabIndex(self):
            return self.__tabWidget.indexOf(self.__tab)

        def close(self):
            return self.__tabWidget.closeTab(self.tabIndex())

        def window(self):
            return self.__window

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
        
        def erase(self, region: "VtAPI.Region"):
            t = self.__tab.textEdit.toPlainText()
            self.__tab.textEdit.setPlainText(t[:region.begin()] + t[region.end():])
        
        def replace(self, region: "VtAPI.Region", string):
            t = self.__tab.textEdit.toPlainText()
            self.__tab.textEdit.setPlainText(t[:region.begin()] + string + t[region.end():])

        def undo(self):
            self.__tab.textEdit.undo()

        def redo(self):
            self.__tab.textEdit.redo()

        def cut(self):
            self.__tab.textEdit.cut()

        def copy(self):
            self.__tab.textEdit.copy()

        def paste(self):
            self.__tab.textEdit.paste()

        def selectAll(self):
            self.__tab.textEdit.selectAll()

        def setSyntax(self, data=None, path=None):
            if path:
                data = self.api.loadSettings(path)
            if data:
                self.setHighlighter(data)

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

        def setHighlighter(self, hl):
            self.__tab.textEdit.highLighter.highlightingRules = hl

        def rehighlite(self):
            self.__tab.textEdit.highLighter.rehighlight()

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

    class Plugin:
        class TextCommand:
            def __init__(self, api, view):
                self.api: VtAPI = api
                self.view: VtAPI.View = view

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
                self.api: VtAPI = api
                self.window: VtAPI.Window = window

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
                self.api: VtAPI = api

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
        tabClosed = QtCore.pyqtSignal(object)
        tabCreated = QtCore.pyqtSignal()
        tabChanged = QtCore.pyqtSignal()

        textChanged = QtCore.pyqtSignal()

        windowClosed = QtCore.pyqtSignal()
        windowStarted = QtCore.pyqtSignal()
        windowStateRestoring = QtCore.pyqtSignal()
        windowRunningStateInited = QtCore.pyqtSignal()
        windowStateSaving = QtCore.pyqtSignal()

        logWrited = QtCore.pyqtSignal(str)

        treeWidgetClicked = QtCore.pyqtSignal(QtCore.QModelIndex)
        treeWidgetDoubleClicked = QtCore.pyqtSignal(QtCore.QModelIndex)
        treeWidgetActivated = QtCore.pyqtSignal()

        fileOpened = QtCore.pyqtSignal(object)
        fileSaved = QtCore.pyqtSignal(object)
        fileTagInited = QtCore.pyqtSignal(object)

        fileTagAdded = QtCore.pyqtSignal(object, str)
        fileTagRemoved = QtCore.pyqtSignal(object, str)

        def __init__(self, w):
            super().__init__(w)
            self.__window: QtWidgets.QMainWindow = w
            self.__windowApi: VtAPI = self.__window.api

        def addSignal(self, signalName: str, signalArgs: list):
            signalType = [arg for arg in signalArgs]
            signal = QtCore.pyqtSignal(*signalType)
            
            setattr(self, signalName, signal)

        def findSignal(self, signalName: str):
            return getattr(self, signalName)

        def tabChngd(self, index):
            widget = self.__window.tabWidget.currentWidget()
            try:
                if widget:
                    view = self.__windowApi.View(self.__windowApi, self.__windowApi.activeWindow, qwclass=widget)
                    view.id = widget.objectName().split("-")[-1]
                    for v in self.__windowApi.activeWindow.views:
                        if v == view:
                            self.__windowApi.activeWindow.activeView = v
                            self.__windowApi.activeWindow.setTitle(os.path.normpath(self.__windowApi.activeWindow.activeView.getFile() or 'Untitled'))
                            self.updateEncoding()
                            break
                    else:
                        self.__window.setWindowTitle(self.__windowApi.appName)
                else:
                    self.__window.setWindowTitle(self.__windowApi.appName)
                self.tabChanged.emit()
            except Exception as e:
                self.__window.setWindowTitle(self.__windowApi.appName)
                self.__windowApi.activeWindow.setLogMsg(f"Error when updating tabs: {e}")

        def updateEncoding(self):
            e = self.__windowApi.activeWindow.activeView.getEncoding()
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

    def activeWindow(self) -> Window:
        return self.activeWindow

    @property
    def windows(self):
        return tuple(self.__windows)
    
    def addWindow(self, window: Window):
        self.__windows.append(window)

    def loadSettings(self, path=None, pl=None):
        if pl and not path:
            path = os.path.dirname(pl)
        if os.path.isfile(path):
            with open(path, "r+") as f:
                return json.load(f)
        else:
            return {}

    def saveSettings(self, data, path=None, pl=None):
        if pl and not path:
            path = os.path.dirname(pl)
        if os.path.isfile(path):
            with open(path, "r+") as f:
                json.dump(data, f)

    def importModule(self, name):
        return importlib.import_module(name)

    def setTimeout(self, function, delay):
        QtCore.QTimer.singleShot(delay, function)

    async def setTimeout_async(self, function, delay):
        await asyncio.sleep(delay / 1000)
        function()

    def version(self):
        return "4.0"

    def platform(self):
        current_platform = platform.system()
        if current_platform == "Darwin":
            return "OSX"
        return current_platform

    def arch(self):
        if sys.maxsize > 2**32:
            if platform.system() == "Windows":
                return "x64"
            else:
                return "amd64"
        else:
            return "x86"
    
    def replaceConsts(self, data, constants):
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

    def findKey(self, p, d):
        current = d
        for key in p.split("."):
            if isinstance(current, dict) and key in current: current = current[key]
            else: return None
        return current

    def addKey(self, p, value, d):
        path = p.split(".")
        current = d
        for key in path[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[path[-1]] = value

    def replacePaths(self, data):
        def replace_var(match):
            env_var = match.group(1)
            return os.getenv(env_var, f'%{env_var}%')
        return re.sub(r'%([^%]+)%', replace_var, data)

    def defineLocale(self):
        return QtCore.QLocale.system().name().split("_")[0]

    def packagesPath(self):
        return self.packagesDir
