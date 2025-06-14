import functools
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QCompleter
from PySide6.QtCore import QStringListModel, Qt, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtSql import QSqlDatabase, QSqlQuery

import sys, io, uuid

class Logger:
    def __init__(self, window):
        self._log = ""
        self.__window = window
        
        self._stdout_backup = sys.stdout
        self._log_stream = io.StringIO()
        sys.stdout = self
        self._file = None

    def setFile(self, file):
        self._file = file

    @property
    def log(self):
        return self._log

    @log.setter
    def log(self, value):
        self._log = value
        if self._file: self._file.write("\n"+value)
        self.__window.api.activeWindow.signals.logWrited.emit(value)

    def write(self, message):
        if message:
            try:
                if self.__window.logStdout:
                    self.__window.api.activeWindow.setLogMsg(f"stdout: {message}")
                    if self._file: self._file.write("\n"+message)
                    self.__window.api.activeWindow.signals.logWrited.emit(message)
            except: pass
            if self._stdout_backup:
                self._stdout_backup.write(message)

    def flush(self):
        pass

    def close(self):
        sys.stdout = self._stdout_backup
        self._log_stream.close()

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

    @Slot()
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

    @Slot()
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
        self.multi_line_rules = []
        self.additData = []

    def addHighlightingRule(self, category, rule):
        if category == "multi_line_strings":
            self.multi_line_rules.append(rule)
        else:
            self.highlightingRules[category] = rule

    def addHighlightingData(self, data):
        self.additData = data

    def highlightBlock(self, text):
        block_start_line = self.document().findBlockByNumber(self.currentBlock().blockNumber()).blockNumber()

        for category, rule in self.highlightingRules.items():
            text_format = self.createTextFormat(rule)
            for pattern in rule['pattern']:
                regex = QtCore.QRegularExpression(pattern)
                match = regex.globalMatch(text)
                while match.hasNext():
                    match_item = match.next()
                    start_pos = match_item.capturedStart()
                    length = match_item.capturedLength()
                    self.setFormat(start_pos, length, text_format)

        if self.additData:
            for data in self.additData:
                if data['line'] == block_start_line:
                    start_pos, end_pos = data['pos']
                    text_format = QtGui.QTextCharFormat()
                    
                    if 'color' in data:
                        text_format.setForeground(QtGui.QColor(data['color']))
                    if 'bg' in data:
                        text_format.setBackground(QtGui.QColor(data['bg']))
                    if 'weight' in data:
                        if data['weight'] == 'bold':
                            text_format.setFontWeight(QtGui.QFont.Weight.Bold)
                        elif data['weight'] == 'italic':
                            text_format.setFontItalic(True)

                    # Устанавливаем формат подсветки на определенные участки
                    self.setFormat(start_pos, end_pos - start_pos, text_format)

        self.setCurrentBlockState(0)

        for rule in self.multi_line_rules:
            self.applyMultilineHighlighting(text, rule)


    def createTextFormat(self, rule):
        """
        Создает QTextCharFormat на основе правила.
        :param rule: Словарь с параметрами форматирования.
        :return: QTextCharFormat.
        """
        text_format = QtGui.QTextCharFormat()
        if 'color' in rule:
            text_format.setForeground(QtGui.QColor(rule['color']))
        if 'bg' in rule:
            text_format.setBackground(QtGui.QColor(rule['bg']))
        if 'weight' in rule:
            if rule['weight'] == 'bold':
                text_format.setFontWeight(QtGui.QFont.Weight.Bold)
            elif rule['weight'] == 'italic':
                text_format.setFontItalic(True)
        return text_format

    def applyMultilineHighlighting(self, text, rule):
        """
        Применяет подсветку для многострочных строк.
        :param text: Текст блока.
        :param rule: Словарь с параметрами (start, end, style).
        """
        start_delim = QtCore.QRegularExpression(rule['start'])
        end_delim = QtCore.QRegularExpression(rule['end'])
        text_format = self.createTextFormat(rule)

        if self.previousBlockState() == 1:
            start = 0
            match = end_delim.match(text)
            if match.hasMatch():
                end = match.capturedEnd()
                self.setFormat(start, end - start, text_format)
                self.setCurrentBlockState(0)
            else:
                self.setFormat(start, len(text), text_format)
                self.setCurrentBlockState(1)
            return

        match = start_delim.match(text)
        while match.hasMatch():
            start = match.capturedStart()
            match = end_delim.match(text, start + 1)
            if match.hasMatch():
                end = match.capturedEnd()
                self.setFormat(start, end - start, text_format)
                self.setCurrentBlockState(0)
            else:
                self.setFormat(start, len(text) - start, text_format)
                self.setCurrentBlockState(1)

    def rehighlightBlock(self, block):
        """
        Переподсвечивает определенный блок.
        :param block: QTextBlock для обработки.
        """
        cursor = QtGui.QTextCursor(block)
        self.highlightBlock(cursor.block().text())


class StandartCompleter(QCompleter):
    insertText = QtCore.Signal(str)

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

class LineNumberArea(QtWidgets.QWidget):
    def __init__(self, text_edit):
        super().__init__(text_edit)
        self.text_edit = text_edit
        self.text_edit.viewport().installEventFilter(self)
        self.text_edit.verticalScrollBar().valueChanged.connect(self.update)
        self.text_edit.textChanged.connect(self.update)
        self.font = self.text_edit.font()

        self.update_width()

    def update_width(self):
        """Updates the width of the line number area."""
        block_count = self.text_edit.document().blockCount()
        digits = len(str(max(1, block_count)))
        font_metrics = QtGui.QFontMetrics(self.font)
        self.setFixedWidth(10 + font_metrics.horizontalAdvance("9") * digits)

    def paintEvent(self, event):
        """Paint line numbers."""
        painter = QtGui.QPainter(self)

        block = self.text_edit.document().begin()
        block_number = block.blockNumber()
        top = -self.text_edit.verticalScrollBar().value()
        font_metrics = QtGui.QFontMetrics(self.text_edit.font())

        while block.isValid():
            block_geometry = self.text_edit.document().documentLayout().blockBoundingRect(block)
            block_top = int(block_geometry.translated(0, top).top())
            block_bottom = block_top + int(block_geometry.height())

            if block_top > event.rect().bottom():
                break

            if block_bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(
                    0,
                    block_top,
                    self.width(),
                    font_metrics.height(),
                    QtCore.Qt.AlignRight,
                    number,
                )

            block = block.next()
            block_number += 1

    def eventFilter(self, obj, event):
        """Handle events from the text edit viewport."""
        if obj == self.text_edit.viewport() and event.type() == QtCore.QEvent.Paint:
            self.update()
        return super().eventFilter(obj, event)

class TextEdit(QtWidgets.QTextEdit):
    def __init__(self, mw):
        super().__init__()

        self.change_event = False

        self.mw = mw
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)
        self.setShortcutEnabled(False)
        self.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.WidgetWidth)

        self.minimap = MiniMap(self)
        self.minimap.setTextEdit(self)
        self.line_number_area = LineNumberArea(self)

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.addWidget(self.line_number_area)
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

        self.textChanged.connect(self.update_line_number_width)

    def update_line_number_width(self):
        self.line_number_area.update_width()

    def update_line_number_area(self):
        self.line_number_area.update()

    def applyAdditionalHighlighting(self):
        cursor = self.textCursor()
        cursor.select(QtGui.QTextCursor.Document)  # Выбираем весь документ
        text = cursor.selectedText()  # Получаем весь текст из документа

        self.highLighter.highlightBlock(text)

    def safeSetText(self, text, cursor=None):
        self.change_event = True
        if not cursor:
            self.setText(text)
        else:
            cursor.insertText(text)
        self.mw.api.activeWindow.signals.textChanged.emit()
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

    @functools.lru_cache
    def textLen(self): return len(self.toPlainText())

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        tc = self.textCursor()
        if event.modifiers() in {Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.ShiftModifier}:
            action = self.mw.keyPressEvent(event)
            if action:
                event.accept()
                return
            else:
                QtWidgets.QTextEdit.keyPressEvent(self, event)
        else:
            QtWidgets.QTextEdit.keyPressEvent(self, event)
            self.mw.api.activeWindow.activeView.setSaved(False)
        self.textLen.cache_clear()
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
        self.MainWindow = MainWindow
        self.api = MainWindow.api
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

    def cAddTab(self):
        self.tab = QtWidgets.QWidget()
        self.tab.file = None
        self.tab.canSave = None
        self.tab.canEdit = None
        self.tabBar().setTabSaved(self.tab, True)
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
        self.api.activeWindow.addView(newView)

        self.addTab(self.tab, "")
        self.api.activeWindow.setTab(-1)
        self.api.activeWindow.focus(newView)

        self.api.activeWindow.signals.tabCreated.emit()

    def closeTab(self, tab):
        currentIndex = self.indexOf(tab)
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
                    self.MainWindow.api.activeWindow.runCommand({"command": "SaveFileCommand", "args": [tab.file]})
                    self.MainWindow.api.activeWindow.signals.tabClosed.emit(self.MainWindow.api.activeWindow.activeView)
                    self.MainWindow.api.activeWindow.delView(self.MainWindow.api.activeWindow.activeView)
                    tab.deleteLater()
                    self.removeTab(currentIndex)
                elif result == QtWidgets.QMessageBox.StandardButton.No:
                    self.MainWindow.api.activeWindow.signals.tabClosed.emit(  self.MainWindow.api.activeWindow.activeView)
                    self.MainWindow.api.activeWindow.delView(self.MainWindow.api.activeWindow.activeView)
                    tab.deleteLater()
                    self.removeTab(currentIndex)
                elif result == QtWidgets.QMessageBox.StandardButton.Cancel:
                    pass
            else:
                self.MainWindow.api.activeWindow.signals.tabClosed.emit(self.MainWindow.api.activeWindow.activeView)
                self.MainWindow.api.activeWindow.delView(self.MainWindow.api.activeWindow.activeView)
                tab.deleteLater()
                self.removeTab(currentIndex)

class Tag(QtWidgets.QWidget):
    def __init__(self, text, onClose, api=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.api = api
        self.onClose = onClose
        self.setObjectName("fileTag")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)

        self.label = QtWidgets.QLabel(f"#{text}")
        self.label.setObjectName("tagLabel")
        layout.addWidget(self.label)

        self.closeButton = QtWidgets.QPushButton()
        self.closeButton.setObjectName("tagCloseButton")
        self.closeButton.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self.closeButton.setMaximumSize(15, 15)
        self.closeButton.clicked.connect(lambda checked: self.api.activeWindow.runCommand({"command": "RemoveTagCommand", "kwargs": {"tag": self.text, "show": False}}))
        layout.addWidget(self.closeButton)

    def mouseDoubleClickEvent(self, a0):
        self.api.activeWindow.runCommand({"command": "GetFilesForTagCommand", "kwargs": {"tag": self.text}})

    def closeTag(self):
        self.onClose(self.text)

class TagContainer(QtWidgets.QFrame):
    def __init__(self, parent=None, api=None):
        super().__init__(parent)
        self.tags = []
        self.visibleTags = 3
        self.moreMenu = None

        self.api=api

        self.tagLayout = QtWidgets.QHBoxLayout(self)
        self.tagLayout.setContentsMargins(0, 0, 0, 0)
        self.tagLayout.setSpacing(5)

        self.moreButton = QtWidgets.QToolButton()
        self.moreButton.setObjectName("moreTagsButton")
        self.moreButton.setFixedSize(20, 20)
        self.moreButton.clicked.connect(self.showMoreTags)
        self.moreButton.setVisible(False)
        self.tagLayout.addWidget(self.moreButton)

        self.addTagButton = QtWidgets.QPushButton()
        self.addTagButton.setText("+")
        self.addTagButton.setObjectName("addTagButton")
        self.addTagButton.setFixedSize(20, 20)
        self.addTagButton.clicked.connect(lambda: self.api.activeWindow.runCommand({"command": "AddTagCommand"}))
        self.tagLayout.addWidget(self.addTagButton)

    def addTag(self, text):
        if text in self.tags:
            return

        self.tags.append(text)
        tagWidget = Tag(text, self.removeTag, api=self.api)
        tagWidget.setObjectName("fileTag")
        self.tagLayout.insertWidget(self.tagLayout.count() - 2, tagWidget)
        self.updateTagsDisplay()

    def clear(self):
        for i in range(self.tagLayout.count()):
            widget = self.tagLayout.itemAt(i).widget()
            if widget.objectName() == "fileTag": widget.deleteLater()

    def removeTag(self, text, show=False):
        self.tags.remove(text)
        for i in range(self.tagLayout.count() - 2):
            widget = self.tagLayout.itemAt(i).widget()
            if widget and widget.text == text:
                widget.deleteLater()
                break

        self.updateTagsDisplay()
        if self.moreMenu:
            self.moreMenu.close()
        if show:
            self.showMoreTags()

    def updateTagsDisplay(self):
        for i in range(self.tagLayout.count() - 2):
            widget = self.tagLayout.itemAt(i).widget()
            if widget:
                widget.setVisible(i < self.visibleTags)
        self.moreButton.setVisible(len(self.tags) > self.visibleTags)

    def showMoreTags(self):
        self.moreMenu = QtWidgets.QMenu()
        for tag in self.tags:
            actionWidget = QtWidgets.QWidgetAction(self.moreMenu)
            actionWidget.setObjectName("menuTagAction")
            tagWidget = QtWidgets.QWidget()
            tagWidget.setObjectName("menuTag")
            tagLayout = QtWidgets.QHBoxLayout(tagWidget)
            tagLayout.setContentsMargins(5, 0, 5, 0)
            
            label = QtWidgets.QLabel(tag)
            label.setObjectName("menuTagLabel")
            tagLayout.addWidget(label)
            
            closeButton = QtWidgets.QPushButton()
            closeButton.setObjectName("tagCloseButton")
            closeButton.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TitleBarCloseButton))
            closeButton.setMaximumSize(15, 15)
            closeButton.clicked.connect(lambda checked, t=tag: self.api.activeWindow.runCommand({"command": "RemoveTagCommand", "kwargs": {"tag": t, "show": True}}))
            tagLayout.addWidget(closeButton)
            
            actionWidget.setDefaultWidget(tagWidget)
            self.moreMenu.addAction(actionWidget)
        
        self.moreMenu.exec(self.moreButton.mapToGlobal(QtCore.QPoint(0, self.moreButton.height())))

class TagDB:
    def __init__(self, dbFile: str):
        self.dbFile = dbFile
        self.db = QSqlDatabase.addDatabase('QSQLITE')
        self.db.setDatabaseName(dbFile)
        if not self.db.open():
            print(f"Ошибка при подключении к базе данных: {self.db.lastError().text()}")
        else:
            self._createTables()

    def _createTables(self):
        query = QSqlQuery(self.db)
        query.prepare("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            filename TEXT UNIQUE NOT NULL
        )""")
        if not query.exec():
            print(f"Ошибка создания таблицы files: {query.lastError().text()}")
        
        query.prepare("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            tag TEXT NOT NULL
        )""")
        if not query.exec():
            print(f"Ошибка создания таблицы tags: {query.lastError().text()}")
        
        query.prepare("""
        CREATE TABLE IF NOT EXISTS file_tags (
            file_id INTEGER,
            tag_id INTEGER,
            FOREIGN KEY (file_id) REFERENCES files(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id),
            PRIMARY KEY (file_id, tag_id)
        )""")
        if not query.exec():
            print(f"Ошибка создания таблицы file_tags: {query.lastError().text()}")

    def addFile(self, filename: str):
        query = QSqlQuery(self.db)
        query.prepare("INSERT OR IGNORE INTO files (filename) VALUES (?)")
        query.addBindValue(filename)
        if not query.exec():
            print(f"Ошибка добавления файла: {query.lastError().text()}")

    def addTag(self, filename: str, tag: str):
        query = QSqlQuery(self.db)

        # Проверяем, существует ли файл в базе данных
        query.prepare("SELECT id FROM files WHERE filename = ?")
        query.addBindValue(filename)
        if not query.exec():
            print(f"Ошибка выполнения запроса: {query.lastError().text()}")
            return
        if query.next():
            fileId = query.value(0)
        else:
            # Добавляем файл, если его нет в базе
            self.addFile(filename)
            query.prepare("SELECT id FROM files WHERE filename = ?")
            query.addBindValue(filename)
            if not query.exec():
                print(f"Ошибка выполнения запроса: {query.lastError().text()}")
                return
            query.next()
            fileId = query.value(0)

        # Проверяем, существует ли тег в базе данных
        query.prepare("SELECT id FROM tags WHERE tag = ?")
        query.addBindValue(tag)
        if not query.exec():
            print(f"Ошибка выполнения запроса: {query.lastError().text()}")
            return
        if query.next():
            tagId = query.value(0)
        else:
            # Добавляем новый тег, если его нет в базе
            query.prepare("INSERT INTO tags (tag) VALUES (?)")
            query.addBindValue(tag)
            if not query.exec():
                print(f"Ошибка добавления тега: {query.lastError().text()}")
                return
            query.prepare("SELECT id FROM tags WHERE tag = ?")
            query.addBindValue(tag)
            if not query.exec():
                print(f"Ошибка выполнения запроса: {query.lastError().text()}")
                return
            query.next()
            tagId = query.value(0)

        # Добавляем связь между файлом и тегом
        query.prepare("INSERT OR IGNORE INTO file_tags (file_id, tag_id) VALUES (?, ?)")
        query.addBindValue(fileId)
        query.addBindValue(tagId)
        if not query.exec():
            print(f"Ошибка добавления связи: {query.lastError().text()}")

    def removeTag(self, filename: str, tag: str):
        query = QSqlQuery(self.db)

        # Находим ID файла
        query.prepare("SELECT id FROM files WHERE filename = ?")
        query.addBindValue(filename)
        if not query.exec():
            print(f"Ошибка выполнения запроса: {query.lastError().text()}")
            return
        if not query.next():
            return
        fileId = query.value(0)

        # Находим ID тега
        query.prepare("SELECT id FROM tags WHERE tag = ?")
        query.addBindValue(tag)
        if not query.exec():
            print(f"Ошибка выполнения запроса: {query.lastError().text()}")
            return
        if not query.next():
            return
        tagId = query.value(0)

        # Удаляем связь между файлом и тегом
        query.prepare("DELETE FROM file_tags WHERE file_id = ? AND tag_id = ?")
        query.addBindValue(fileId)
        query.addBindValue(tagId)
        if not query.exec():
            print(f"Ошибка удаления связи: {query.lastError().text()}")

    def getTagsForFile(self, filename: str):
        query = QSqlQuery(self.db)

        # Получаем ID файла
        query.prepare("SELECT id FROM files WHERE filename = ?")
        query.addBindValue(filename)
        if not query.exec():
            print(f"Ошибка выполнения запроса: {query.lastError().text()}")
            return []
        if query.next():
            fileId = query.value(0)
        else:
            self.addFile(filename)
            query.prepare("SELECT id FROM files WHERE filename = ?")
            query.addBindValue(filename)
            if not query.exec():
                print(f"Ошибка выполнения запроса: {query.lastError().text()}")
                return []
            query.next()
            fileId = query.value(0)

        query.prepare("""
        SELECT tags.tag FROM tags
        JOIN file_tags ON file_tags.tag_id = tags.id
        WHERE file_tags.file_id = ?
        """)
        query.addBindValue(fileId)
        if not query.exec():
            print(f"Ошибка выполнения запроса: {query.lastError().text()}")
            return []

        tags = []
        while query.next():
            tags.append(query.value(0))
        return tags

    def getFilesForTag(self, tag: str):
        query = QSqlQuery(self.db)

        query.prepare("SELECT id FROM tags WHERE tag = ?")
        query.addBindValue(tag)
        if not query.exec():
            print(f"Error executing query: {query.lastError().text()}")
            return []
        if query.next():
            tagId = query.value(0)
        else:
            print("Tag not found")
            return []

        query.prepare("""
        SELECT files.filename FROM files
        JOIN file_tags ON file_tags.file_id = files.id
        WHERE file_tags.tag_id = ?
        """)
        query.addBindValue(tagId)
        if not query.exec():
            print(f"Error executing query: {query.lastError().text()}")
            return []

        files = []
        while query.next():
            files.append(query.value(0))
        return files

class StatusBar(QtWidgets.QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.animList = []  # Список символов для анимации
        self.currentElement = 0  # Текущий индекс анимации
        self.fontt = QtGui.QFont("Arial")
        self.fontt.setPointSize(10)
        self.setFont(self.fontt)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.updateAnimation)

        self.animLabel = QtWidgets.QLabel("", self)
        self.animLabel.setObjectName("animLabel")

        self.msgLabel = QtWidgets.QLabel("", self)
        self.msgLabel.setObjectName("msgLabel")

        self.encodingLabel = QtWidgets.QLabel("UTF-8", self)
        self.encodingLabel.setObjectName("encodingLabel")

        self.addWidget(self.animLabel)
        self.addWidget(self.msgLabel)
        self.addPermanentWidget(self.encodingLabel)

        self.msgTimer = QtCore.QTimer(self)
        self.msgTimer.timeout.connect(self.clearStatusMessage)

    def showStatusMessage(self, text, timeout=0):
        self.msgLabel.setText(text)
        if timeout > 0:
            self.msgTimer.start(timeout)

    def clearStatusMessage(self):
        self.msgLabel.setText("")
        self.msgTimer.stop()

    def currentStatusMessage(self):
        return self.msgLabel.text()

    def setEncoding(self, text):
        self.encodingLabel.setText(text)

    def getEncoding(self):
        return self.encodingLabel.text()

    def startAnimation(self, interval=500):
        if self.animList:
            self.timer.start(interval)

    def stopAnimation(self):
        self.timer.stop()
        self.animLabel.clear()

    def setAnimationList(self, lst):
        self.animList = lst

    def updateAnimation(self):
        if self.animList:
            self.currentElement = (self.currentElement + 1) % len(self.animList)
            self.animLabel.setText(self.animList[self.currentElement])
