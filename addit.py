import platform, os, re, shutil, urllib.request, uuid, json, zipfile, pip
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSlot

from PyQt6.QtWidgets import QCompleter
from PyQt6.QtCore import QStringListModel, Qt
from PyQt6.QtGui import QTextCursor

class MiniMap(QtWidgets.QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.setFixedWidth(150)
        self.setObjectName("miniMap")
        self.setTextInteractionFlags (QtCore.Qt.TextInteractionFlag.NoTextInteraction) 
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        self._isDragging = False

    def setTextEdit(self, text_edit):
        self.textEdit = text_edit
        self.setHtml(self.textEdit.toHtml())
        self.textEdit.verticalScrollBar().valueChanged.connect(self.syncScroll)
        self.textEdit.cursorPositionChanged.connect(self.syncSelection)
        self.textEdit.verticalScrollBar().rangeChanged.connect(self.update_minimap)
        self.textEdit.textChanged.connect(self.update_minimap)
        self.setFontPointSize(3)
        self.update_minimap()
        self.viewport().update()

    @pyqtSlot()
    def syncScroll(self):
        maxValue = self.textEdit.verticalScrollBar().maximum()
        if maxValue != 0:
            value = self.textEdit.verticalScrollBar().value()
            ratio = value / maxValue
            self.verticalScrollBar().setValue(int(ratio * self.verticalScrollBar().maximum()))
        self.viewport().update()

    def syncSelection(self):
        c = QtGui.QTextCursor(self.textEdit.document())
        c.setPosition(self.textEdit.textCursor().selectionStart())
        c.setPosition(self.textEdit.textCursor().selectionEnd(), QtGui.QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(c)
        self.viewport().update()

    @pyqtSlot()
    def update_minimap(self):
        self.setPlainText(self.textEdit.toPlainText())
        self.syncScroll()
        self.viewport().update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._isDragging = True
            self.syncScroll_from_position(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._isDragging:
            self.syncScroll_from_position(event.pos())
            self.textCursor().clearSelection()
        super().mouseMoveEvent(event)
        self.textCursor().clearSelection()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.textCursor().clearSelection()
            self._isDragging = False
        super().mouseReleaseEvent(event)

    def syncScroll_from_position(self, pos):
        if self.viewport().height() != 0:
            ratio = pos.y() / self.viewport().height()
            value = int(ratio * self.textEdit.verticalScrollBar().maximum())
            self.textEdit.verticalScrollBar().setValue(value)
            self.textCursor().clearSelection()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        scroll_bar = self.textEdit.verticalScrollBar()
        scroll_bar.setValue(int(scroll_bar.value() - delta / 1.5))

    def resizeEvent(self, event):
        self.update_minimap()
        super().resizeEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.textEdit is None:
            return

        viewportRect = self.textEdit.viewport().rect()
        content_rect = self.textEdit.document().documentLayout().blockBoundingRect(self.textEdit.document().firstBlock()).united(
            self.textEdit.document().documentLayout().blockBoundingRect(self.textEdit.document().lastBlock())
        )

        viewportHeight = self.viewport().height()
        contentHeight = content_rect.height()
        if contentHeight == 0:
            return
        scaleFactor = viewportHeight / contentHeight

        visibleRectHeight = viewportRect.height() * scaleFactor
        visibleRectTop = self.textEdit.verticalScrollBar().value() * scaleFactor

        visibleRect = QtCore.QRectF(
            0,
            visibleRectTop,
            self.viewport().width(),
            visibleRectHeight
        )

        painter = QtGui.QPainter(self.viewport())
        painter.setBrush(QtGui.QColor(0, 0, 255, 50))
        painter.setPen(QtGui.QColor(0, 0, 255))
        painter.drawRect(visibleRect)

class StandartHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, document: QtGui.QTextDocument):
        super().__init__(document)

        self.highlightingRules = {}
        document.contentsChange.connect(self.onContentsChange)

    def highlightBlock(self, text):
        for category in self.highlightingRules.keys():
            for pattern_info in self.highlightingRules[category]:
                pattern, index, fmt = pattern_info
                match = pattern.match(text)  # Используйте match для поиска совпадений
                while match.hasMatch():
                    start = match.capturedStart()
                    end = match.capturedEnd()
                    self.setFormat(start, end - start, fmt)  # Установить формат
                    match = pattern.match(text, end)  # Ищем следующее совпадение

        self.setCurrentBlockState(0)

        if self.highlightingRules.get("multi_line_strings"):
            in_multiline_single = self.match_multiline(
                text, 
                self.highlightingRules['multi_line_strings'][0][0],  # Получаем первый разделитель
                1, 
                self.highlightingRules['multi_line_strings'][0][1]  # Получаем стиль для многострочных строк
            )
            
            if not in_multiline_single:
                in_multiline_double = self.match_multiline(
                    text, 
                    self.highlightingRules['multi_line_strings'][1][0],  # Получаем второй разделитель
                    2, 
                    self.highlightingRules['multi_line_strings'][1][1]  # Получаем стиль для многострочных строк
                )

    def match_multiline(self, text, delimiter, in_state, style):
        if self.previousBlockState() == in_state:
            start = 0
        else:
            match = delimiter.match(text)  # Получаем совпадение
            if match.hasMatch():
                start = match.capturedStart()
            else:
                start = -1

        while start >= 0:
            # Ищем следующее совпадение
            match = delimiter.match(text, start)
            if match.hasMatch():
                end = match.capturedEnd()
                length = end - start
                self.setFormat(start, length, style)
                start = end  # Переход к следующему символу после совпадения
            else:
                self.setCurrentBlockState(in_state)  # Сохраняем состояние блока
                break  # Выход из цикла, если больше нет совпадений

        return self.currentBlockState() == in_state


    def onContentsChange(self, position, charsRemoved, charsAdded):
        if charsAdded > 0:
            self.rehighlight()

class StandartCompleter(QCompleter):
    insertText = QtCore.pyqtSignal(str)

    def __init__(self, parent: QtWidgets.QTextEdit):
        QCompleter.__init__(self, parent)
        self.model = QStringListModel(self)
        self.setModel(self.model)
        self.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.highlighted.connect(self.setHighlighted)

    def setHighlighted(self, text):
        self.lastSelected = text

    def getSelected(self):
        return self.lastSelected

    def updateModel(self, text: str):
        words = list(set(text.split()))
        self.model.setStringList(words)
    
    def updateCompletions(self, completions):
        if completions:
            self.model.setStringList(completions)
            self.complete()
        else:
            self.model.setStringList([])

class TextEdit(QtWidgets.QTextEdit):
    def __init__(self, mw):
        super().__init__()

        self.change_event = False

        self.mw = mw
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)
        self.setShortcutEnabled(False)

        self.minimap = MiniMap(self)
        self.minimap.setTextEdit(self)

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.addWidget(self)

        self.minimapScrollArea = QtWidgets.QScrollArea()
        self.minimapScrollArea.setWidget(self.minimap)
        self.minimapScrollArea.setFixedWidth(150)
        self.minimapScrollArea.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        # self.minimapScrollArea.customContextMenuRequested.connect(self.minimap.contextMenu)
        self.minimapScrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.minimapScrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.layout.addWidget(self.minimapScrollArea)

        self.completer = StandartCompleter(self)
        self.completer.setWidget(self)
        self.completer.insertText.connect(self.insertCompletion)

        self.highLighter = StandartHighlighter(self.document())
        self.highLighter.setDocument(self.document())

    def safeSetText(self, text):
        self.change_event = True
        self.setText(text)
        self.mw.api.activeWindow.signals.textChanged.emit()
        self.highLighter.rehighlight()
        self.change_event = False

    def contextMenu(self, pos):
        self.mw.textContextMenu.exec(self.mapToGlobal(pos))

    def insertCompletion(self, completion):
        tc = self.textCursor()
        extra = (len(completion) - len(self.completer.completionPrefix()))
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)
        self.completer.popup().hide()

    def focusInEvent(self, event):
        if self.completer and not self.textCursor().hasSelection():
            self.completer.setWidget(self)
        QtWidgets.QTextEdit.focusInEvent(self, event)

    def keyPressEvent(self, event):
        tc = self.textCursor()
        if event.key() in {
            Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down,
            Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt
        } or event.modifiers() in {Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.ShiftModifier}:
            self.mw.keyPressEvent(event)
            return
        else:
            # self.mw.keyPressEvent(event)
            QtWidgets.QTextEdit.keyPressEvent(self, event)
        self.mw.api.activeWindow.activeView.setSaved(False)
        if event.key() == Qt.Key.Key_Tab and self.completer.popup().isVisible():
            self.completer.insertText.emit(self.completer.getSelected())
            self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            return
        self.completer.updateModel(self.toPlainText())

        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        cr = self.cursorRect()

        if len(tc.selectedText()) > 0 and event.text().isprintable():
            self.completer.setCompletionPrefix(tc.selectedText())
            popup = self.completer.popup()
            popup.setCurrentIndex(self.completer.completionModel().index(0, 0))

            cr.setWidth(self.completer.popup().sizeHintForColumn(0)
                        + self.completer.popup().verticalScrollBar().sizeHint().width())
            self.completer.complete(cr)
        else:
            self.completer.popup().hide()

    # def textEdited(self, text):
    #     cursor_position = self.line_edit.cursorPosition()
    #     line = self.line_edit.text().splitlines()[0]  # Берем первую строку
    #     column = cursor_position  # Используем текущую позицию курсора
    #
    #     # Получаем дополнения из Jedi
    #     completions = self.jedi_completer.get_completions(line, column)
    #
    #     # Обновляем completer
    #     self.completer.update_completions(completions)

class TabBar(QtWidgets.QTabBar):
    def __init__(self, tabwidget):
        super().__init__()
        self.tabWidget = tabwidget
        self.savedStates = []
        self.setObjectName("tabBar")
        self.setMovable(True)
        self.setTabsClosable(True)

    def setTabSaved(self, tab, saved):
        if not tab in [i.get("tab") for i in self.savedStates]:
            self.savedStates.append({"tab": tab, "saved": saved})
        else:
            next((i for i in self.savedStates if i.get("tab") == tab), {})["saved"] = saved
        self.updateTabStyle(next((i for i in self.savedStates if i.get("tab") == tab), {}))

    def updateTabStyle(self, info):
        if info.get("tab"):
            idx = self.tabWidget.indexOf(info.get('tab'))
            if idx != -1:
                if info.get("saved"):
                    self.setStyleSheet(f"QTabBar::tab:selected {{ border-bottom: 2px solid white; }} QTabBar::tab:nth-child({idx+1}) {{ background-color: white; }}")
                else:
                    self.setStyleSheet(f"QTabBar::tab:selected {{ border-bottom: 2px solid yellow; }} QTabBar::tab:nth-child({idx+1}) {{ background-color: yellow; }}")

class TabWidget (QtWidgets.QTabWidget):
    def __init__ (self, MainWindow=None, parent=None):
        super(TabWidget, self).__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.closeTab)
        self.MainWindow = MainWindow
        self.moveRange = None
        self.setObjectName("tabWidget")
        self.setMovable(True)
        self.tabbar = TabBar(self)
        self.setTabBar(self.tabbar)
        self.currentChanged.connect(self.onCurrentChanged)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.cmRequest)

    def cmRequest(self, pos):
        self.MainWindow.tabBarContextMenu.exec(self.mapToGlobal(pos))

    def onCurrentChanged(self, index):
        current_tab = self.currentWidget()
        self.tabbar.updateTabStyle({"tab": current_tab, "saved": self.isSaved(current_tab)})

    def isSaved(self, tab):
        return any(i.get("tab") == tab and i.get("saved") for i in self.tabbar.savedStates)

    def setMovable(self, movable):
        if movable == self.isMovable():
            return
        QtWidgets.QTabWidget.setMovable(self, movable)
        if movable:
            self.tabBar().installEventFilter(self)
        else:
            self.tabBar().removeEventFilter(self)

    def eventFilter(self, source, event):
        if source == self.tabBar():
            if event.type() == QtCore.QEvent.MouseButtonPress and event.buttons() == QtCore.Qt.MouseButton.LeftButton:
                QtCore.QTimer.singleShot(0, self.setMoveRange)
            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                self.moveRange = None
            elif event.type() == QtCore.QEvent.MouseMove and self.moveRange is not None:
                if event.x() < self.moveRange[0] or event.x() > self.tabBar().width() - self.moveRange[1]:
                    return True
        return QtWidgets.QTabWidget.eventFilter(self, source, event)

    def setMoveRange(self):
        tabRect = self.tabBar().tabRect(self.currentIndex())
        pos = self.tabBar().mapFromGlobal(QtGui.QCursor.pos())
        self.moveRange = pos.x() - tabRect.left(), tabRect.right() - pos.x()

    def closeTab(self, currentIndex):
        if currentIndex >= 0:
            self.setCurrentIndex(currentIndex)
            tab = self.currentWidget()
            if not self.isSaved(tab):
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("VarTexter2 - Exiting")
                dlg.setText("File is unsaved. Do you want to save it?")
                dlg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No | QtWidgets.QMessageBox.StandardButton.Cancel)

                yesButton = dlg.button(QtWidgets.QMessageBox.StandardButton.Yes)
                yesButton.setObjectName("tabSaveYes")
                noButton = dlg.button(QtWidgets.QMessageBox.StandardButton.No)
                noButton.setObjectName("tabSaveNo")
                cancelButton = dlg.button(QtWidgets.QMessageBox.StandardButton.Cancel)
                cancelButton.setObjectName("tabSaveCancel")

                dlg.setDefaultButton(cancelButton)
                
                # dlg.setStyleSheet("QtWidgets.QMessageBox { background-color: black; } QLabel { color: white; }")
                
                result = dlg.exec()

                if result == QtWidgets.QMessageBox.StandardButton.Yes:
                    self.MainWindow.api.activeWindow.runCommand({"command": "saveFile", "args": tab.file})
                    tab.deleteLater()
                    self.removeTab(currentIndex)
                    self.MainWindow.api.activeWindow.signals.tabClosed.emit(currentIndex, tab.file)
                elif result == QtWidgets.QMessageBox.StandardButton.No:
                    tab.deleteLater()
                    self.removeTab(currentIndex)
                    self.MainWindow.api.activeWindow.signals.tabClosed.emit(currentIndex, tab.file)
                elif result == QtWidgets.QMessageBox.StandardButton.Cancel:
                    pass
            else:
                tab.deleteLater()
                self.removeTab(currentIndex)
                self.MainWindow.api.activeWindow.signals.tabClosed.emit(currentIndex, tab.file)

class PackageManager(QtWidgets.QDialog):
    def __init__(self, window, packagesDir):
        super().__init__(window)
        self.window = window
        self.packagesDir = packagesDir
        self.tempDir = os.getenv("TEMP")

        self.setObjectName("PackageManager")
        self.resize(800, 600)
        self.mainLayout = QtWidgets.QVBoxLayout(self)

        self.tabWidget = QtWidgets.QTabWidget(parent=self)
        self.tabWidget.setTabPosition(QtWidgets.QTabWidget.TabPosition.West)
        self.tabWidget.setObjectName("tabWidget")

        self.createPluginTab()
        self.createThemeTab()

        self.tabWidget.addTab(self.pluginTab, "Plugins")
        self.tabWidget.addTab(self.themeTab, "Themes")
        self.mainLayout.addWidget(self.tabWidget)
        self.setLayout(self.mainLayout)

    def createPluginTab(self):
        self.pluginTab = QtWidgets.QWidget()
        self.l = QtWidgets.QVBoxLayout(self.pluginTab)
        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.l.addWidget(self.scrollArea)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.scrollAreaLayout = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents)
        return self.pluginTab

    def createThemeTab(self):
        self.themeTab = QtWidgets.QWidget()
        self.l2 = QtWidgets.QVBoxLayout(self.themeTab)
        self.scrollArea2 = QtWidgets.QScrollArea()
        self.scrollArea2.setWidgetResizable(True)
        self.scrollAreaWidgetContents2 = QtWidgets.QWidget()
        self.l2.addWidget(self.scrollArea2)
        self.scrollArea2.setWidget(self.scrollAreaWidgetContents2)
        self.scrollAreaLayout2 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents2)
        return self.themeTab

    def addCard(self, l, c, url, name):
        widget = QtWidgets.QWidget(parent=c)
        widget.setMaximumSize(QtCore.QSize(16777215, 100))
        cardLayout = QtWidgets.QHBoxLayout(widget)

        cardTextLayout = QtWidgets.QVBoxLayout()
        nameLbl = QtWidgets.QLabel(name)
        repoLbl = QtWidgets.QLabel(f"<html><head/><body><p><span style=\" font-weight:600; font-style:italic; color:#383838;\">{url}</span></p></body></html>")
        descriptLbl = QtWidgets.QLabel("This is a description of the Plugin")

        cardTextLayout.addWidget(nameLbl)
        cardTextLayout.addWidget(repoLbl)
        cardTextLayout.addWidget(descriptLbl)
        
        cardLayout.addLayout(cardTextLayout)

        pushButton = QtWidgets.QPushButton("Download", parent=widget)
        pushButton.clicked.connect(lambda: self.install(url))
        cardLayout.addWidget(pushButton)

        l.addWidget(widget)

    def install(self, url, site="github"):
        try:
            tempdirName = self.tempname(8)
            path = os.path.join(self.tempDir or os.path.dirname(__file__), tempdirName)
            os.makedirs(path)

            filePath = os.path.join(path, "package.zip")
            if site == "github":
                urllib.request.urlretrieve(url + "/zipball/master", filePath)
            else:
                urllib.request.urlretrieve(url, filePath)

            with zipfile.ZipFile(filePath, 'r') as f:
                f.extractall(path)
            os.remove(filePath)

            extracted_dir = next(
                os.path.join(path, d) for d in os.listdir(path)
                if os.path.isdir(os.path.join(path, d))
            )

            finalPackageDir = os.path.join(self.packagesDir, url.split("/")[-1])
            os.makedirs(self.packagesDir, exist_ok=True)

            shutil.move(extracted_dir, finalPackageDir)
            shutil.rmtree(path)

            self.checkReqs(finalPackageDir)
        except Exception as e:
            print(e)

    def tempname(self, n):
        return "vt-" + str(uuid.uuid4())[:n + 1] + "-install"

    def installModule(self, packages: str):
        import pip
        pip.main(["install", packages])

    def checkReqs(self, data):
        for url in data:
            if not os.path.isdir(os.path.join(self.packagesDir, url.split("/")[-1])):
                self.install(url)

    def uninstall(self, name):
        dir_path = os.path.join(self.packagesDir, name)
        if os.path.isdir(dir_path):
            shutil.rmtree(dir_path)

    def search(self, name):
        dir_path = os.path.join(self.packagesDir, name)
        return dir_path if os.path.isdir(dir_path) else ""

    def updateRepos(self):
        update_url = "http://127.0.0.1:8000/update"
        zip_path = os.path.join(self.window.cacheDir, "plugins.zip")
        urllib.request.urlretrieve(update_url, zip_path)

        with zipfile.ZipFile(zip_path, 'r') as f:
            f.extractall(self.window.cacheDir)
        os.remove(zip_path)

        self.processPlugins()
        self.processThemes()

    def processPlugins(self):
        plugins_dir = os.path.join(self.window.cacheDir, "plugins")
        for pl in os.listdir(plugins_dir):
            with open(os.path.join(plugins_dir, pl), "r") as f:
                try:
                    data = json.load(f)
                    if all(k in data for k in ("apiVersion", "repo", "name")):
                        if "platform" in data and self.window.api.platform() not in data["platform"]:
                            continue
                        if "requirements" in data:
                            try: self.checkReqs(data["requirements"])
                            except: pass
                        if "modules" in data:
                            try: self.installModule(" ".join(data["modules"]))
                            except: pass
                        self.addCard(self.scrollAreaLayout, self.scrollAreaWidgetContents, data["repo"], name=data["name"])            
                except Exception as e:
                    self.window.api.activeWindow.setLogMsg(f"Error processing plugin {pl}: {e}")

    def processThemes(self):
        themes_dir = os.path.join(self.window.cacheDir, "themes")
        for th in os.listdir(themes_dir):
            with open(os.path.join(themes_dir, th), "r") as f:
                try:
                    data = json.load(f)
                    if all(k in data for k in ("repo", "name")): 
                        self.addCard(self.scrollAreaLayout2, self.scrollAreaWidgetContents2, data["repo"], name=data["name"])            
                except Exception as e:
                    self.window.api.App.setLogMsg(f"Error processing theme {th}: {e}")
