from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QCompleter
from PyQt6.QtCore import QStringListModel, Qt, pyqtSlot
from PyQt6.QtGui import QTextCursor
from PyQt6.QtSql import QSqlDatabase, QSqlQuery

from typing import List
import sqlite3

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

    def safeSetText(self, text, cursor=None):
        self.change_event = True
        if not cursor:
            self.setText(text)
        else:
            cursor.insertText(text)
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

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        tc = self.textCursor()
        if event.key() in {
            Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down,
            Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt
        } or event.modifiers() in {Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.ShiftModifier}:
            self.mw.keyPressEvent(event)
            event.accept()
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

class Tag(QtWidgets.QWidget):
    def __init__(self, text, onClose, api=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.api = api
        self.onClose = onClose
        self.setObjectName("fileTag")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        self.setStyleSheet("background-color: lightgrey; border-radius: 10px;")

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

    def getTagsForFile(self, filename: str) -> List[str]:
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

    def getFilesForTag(self, tag: str) -> List[str]:
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
