from typing import List, Optional, Any, Required

class QApplication():
    def __init__(self): """PyQt6.QtWidgets.QApplication"""

class QMainWindow():
    def __init__(self): """PyQt6.QtWidgets.QMainWindow"""

class QObject():
    def __init__(self): """PyQt6.QtCore.QObject"""

class QFileSystemModel():
    def __init__(self): """PyQt6.QtGui.QFileSystemModel"""

class QAction():
    def __init__(self): """PyQt6.QtGui.QAction"""

class QTextCursor():
    def __init__(self): """PyQt6.QtGui.QTextCursor"""

class QWidget():
    def __init__(self): """PyQt6.QtWidgets.QWidget"""

class QDialog():
    def __init__(self): """PyQt6.QtWidgets.QDialog"""

class QLayout():
    def __init__(self): """PyQt6.QtWidgets.QLayout"""

class QDockWidget():
    def __init__(self): """PyQt6.QtWidgets.QDockWidget"""

class QTabWidget():
    def __init__(self): """PyQt6.QtWidgets.QTabWidget"""

class QToolBar():
    def __init__(self): """PyQt6.QtWidgets.QToolBar"""

class QThread():
    def __init__(self): """PyQt6.QtCore.QThread"""

class QProcess():
    def __init__(self): """PyQt6.QtCore.QProcess"""

def pyqtSignal(*args): """QtCore.pyqtSignal"""

class VtAPI:
    def __init__(self, app: Optional["QApplication"] = None) -> None:
        """## API stubs for VT2"""
        self.STATEFILE: dict = {}
        self.INFO: str
        self.WARNING: str
        self.ERROR: str
    class Window:
        """Окно и управление им"""
        def __init__(self, api: "VtAPI", id: str, views: Optional[List['VtAPI.View']] = None, activeView: Optional['VtAPI.View'] = None) -> None:
            """Инициализация для использования
```
w = Window(api, wId, [View(api, w)])
w.focus(w.views[0])
api.addWindow(w)
```
            """
            self.views: List['VtAPI.View']
            self.activeView: Optional['VtAPI.View']
            self.model: QFileSystemModel
            self.id = id
        def newFile(self) -> 'VtAPI.View': """Создаёт новую вкладку"""
        def openFiles(self, files: List[str]) -> None: """Открывает файл(ы) (Запускает стандартную привязанную команду OpenFileCommand)"""
        def saveFile(self, view: Optional['VtAPI.View'] = None, dlg: bool = False) -> None: """Сохраняет текст вкладки (Запускает стандартную привязанную команду SaveFileCommand)"""
        def activeView(self) -> 'VtAPI.View': """Получает активную вкладку"""
        def views(self) -> List['VtAPI.View']: """Получает список вкладок как View"""
        def state(self) -> dict: """Получает состояние окна"""
        @property
        def signals(self) -> 'VtAPI.Signals': """Получает класс Signals со всеми сигналами окна (Изоляция в отдельный класс для красоты и читаемости кода)"""
        def setTitle(self, s: str) -> None: """Устанавливает заголовок окна"""
        def focus(self, view: 'VtAPI.View') -> None: """Устанавливает вкладку по View"""
        def registerCommandClass(self, data: dict) -> None: """Регистрирует команду по её классу {'command': ExampleCommandClass} (Новая рабочая конструкция для регистрации команды из плагина)"""
        def registerCommand(self, data: dict) -> None: """Регистрирует команду по ее названию {'command': 'ExampleCommand'}"""
        def runCommand(self, command: dict) -> None: """Запускает команду (передача информации в формате JSON)"""
        def addToolBar(self, items: List[QAction], flags: List[int] = []) -> None: """Добавляет ToolBar по списку PyQt6.QtGui.QAction"""
        def getCommand(self, name: str) -> Optional[dict]: """Ищет команду в загруженных командах. Возвращает полну. информацию в виде словаря"""
        def getTheme(self) -> str: """Получает тему окна"""
        def setTheme(self, theme: str) -> None: """Устанавливает тему для окна"""
        def getLog(self) -> str: """Получает лог окна"""
        def setLogMsg(self, msg: str, t: str = "") -> None: """Записывает сообщение в лог, можно устанавливать разные цвета"""
        def getTreeModel(self) -> QFileSystemModel: """Получает FileSystemModel окна"""
        def getModelElement(self, i: int) -> str: """Отладочная функция для получения имени выбранного элемента в TreeWidget"""
        def setTreeWidgetDir(self, dir: str) -> QFileSystemModel: """Устанавливает папку в TreeWidget"""
        def setTab(self, i: int) -> None: """Устанавливает вкладку по индексу"""
        def updateMenu(self, menu: str, data: dict) -> None: """Обновляет меню по его id и новым данным в формате JSON"""
        def addDockWidget(self, areas: int, dock: 'VtAPI.Widgets.DockWidget') -> None: """Устанавливает DockWidget в области"""
        def showDialog(self, content: QLayout, flags: int = 0, location: int = -1, width: int = 320, height: int = 240, on_navigate: Optional[callable] = None, on_hide: Optional[callable] = None) -> None: """Создает Dialog по Layout"""
        def isDockWidget(self, area: int) -> Optional[QDockWidget]: """Проверяет существует ли DockWidget в области"""
        def statusMessage(self, text: str, timeout: Optional[int] = None) -> None: """Устанавливает сообщение в статусбаре"""
    class View:
        """Вкладка и управление ей"""
        def __init__(self, api: "VtAPI", window: 'VtAPI.Window') -> None:
            """Инициализация для использования
```
w = Window(api, wId)
view = View(api, w)
w.addView(view)
w.focus(view)
api.addWindow(w)
```
            """
            self.api: VtAPI
            self.id: Optional[str]
            self.tagBase: Optional[object]
        def id(self) -> Optional[str]: """Получает id вкладки (для отладки)"""
        def update(self) -> None: """Обновляет вкладку (активируется event на смену вкладки)"""
        def tabIndex(self) -> int: """Получает индекс вкладки в TabWidget (для отладки)"""
        def close(self) -> None: """Закрывает вкладку"""
        def window(self) -> 'VtAPI.Window': """Получает окно в котором находится вкладка"""
        def getTitle(self) -> str: """Получает название вкладки"""
        def setTitle(self, text: str) -> None: """Установить название вкладки (Нежелательно изменять для вкладок с открытыми файлами)"""
        def getText(self) -> str: """Получает текст вкладки"""
        def getHtml(self) -> str: """Получает текст вкладки в формате HTML """
        def setText(self, text: str) -> str: """Устанавливает текст для вкладки. Примечание, текст вкладки заменяется а не вставляется. Для вставки испольховать insert"""
        def getFile(self) -> Optional[str]: """Получает файл в который сохраняется текст вкладки"""
        def setFile(self, file: str) -> str: """Устанавливает файл в который сохраняется текст вкладки"""
        def getCanSave(self) -> bool: """Проверяет можно ли сохранять текст вкладки как файл"""
        def setCanSave(self, b: bool) -> bool: """Устанавливает можно ли сохранять текст вкладки как файл"""
        def getCanEdit(self) -> bool: """Старорежимная функция, полностью идентична isReadOnly"""
        def isReadOnly(self) -> bool: """Проверяет является ли текст вкладки редактируемым"""
        def setReadOnly(self, b: bool) -> bool: """Устанавливает будет ли текст вкладки редактируемым"""
        def getEncoding(self) -> str: """Получает кодировку вкладки"""
        def setEncoding(self, enc: str) -> str: """Устанавливает кодировку для текста вкладка
        ## !!!Оно не работает, по стандарту везде идёт utf-8. Только в плагинах возможны изменения но их нет. Вроде"""
        def getSaved(self) -> bool: """Получает сохранена ли вкладка"""
        def setSaved(self, b: bool) -> bool: """Устанавливает сохранена ли вкладка"""
        def size(self) -> int: """Возвращает длинну текста"""
        def substr(self, region: 'VtAPI.Region') -> str: """Извлекает текст из региона и возвращает его как строку"""
        def insert(self, string: str, point: Optional['VtAPI.Point'] = None) -> None: """Вставляет текст в точке"""
        def erase(self, region: 'VtAPI.Region') -> None: """Очищает регион"""
        def replace(self, region: 'VtAPI.Region', string: str) -> None: """Заменяет текст в регионе на другой"""
        def undo(self) -> None: """На одно действие назад"""
        def redo(self) -> None: """На одно действие вперед"""
        def cut(self) -> None: """Вырезает текст"""
        def copy(self) -> None: """Копирует текст"""
        def paste(self) -> None: """Вставляет текст"""
        def selectAll(self) -> None: """Выделяет весь текст"""
        def setSyntax(self, data: Optional[dict] = None, path: Optional[str] = None) -> None: """Функция которая позволяет загрузить файл с правилами синтаксиса (в JSON виде) по его пути"""
        def isDirty(self) -> bool: """Проверяет был ли изменен текст"""
        def getTextSelection(self) -> str: """Получает выделенный текст"""
        def getTextCursor(self) -> QTextCursor: """Получает позицию курсора"""
        def setTextSelection(self, region: "VtAPI.Region") -> None: """Устанавливает выделение текста по региону"""
        def getCompletePos(self) -> tuple[str, int, int]: """Функция необходима для работы автодополнения"""
        def setCompleteList(self, lst: list) -> None: """Устанавливает список для автодополнения"""
        def setHighlighter(self, hl: dict) -> None: """
Устанавливает правила для подсветки синтаксиса

## Пример подсветки синтаксиса для Python (PythonSyntax Plugin v 1.0)
    ```        
    def format(color, style=''):
        _color = QtGui.QColor()
        if type(color) is not str:
            _color.setRgb(color[0], color[1], color[2])
        else:
            _color.setNamedColor(color)

        _format = QtGui.QTextCharFormat()
        _format.setForeground(_color)
        if 'bold' in style:
            _format.setFontWeight(QtGui.QFont.Weight.Bold)
        if 'italic' in style:
            _format.setFontItalic(True)

        return _format

    STYLES = {
        'keyword': format([200, 120, 50], 'bold'),
        'operator': format([150, 150, 150]),
        'brace': format('darkGray'),
        'defclass': format([220, 220, 255], 'bold'),
        'string': format([20, 110, 100]),
        'string2': format([30, 120, 110]),
        'comment': format([128, 128, 128]),
        'self': format([150, 85, 140], 'italic'),
        'numbers': format([100, 150, 190]),
    }

    python_highlighter_rules = {
        'keywords': [
            r'\b%s\b' % w for w in [
                'and', 'assert', 'break', 'class', 'continue', 'def',
                'del', 'elif', 'else', 'except', 'exec', 'finally',
                'for', 'from', 'global', 'if', 'import', 'in',
                'is', 'lambda', 'not', 'or', 'pass', 'print',
                'raise', 'return', 'try', 'while', 'yield',
                'None', 'True', 'False',
            ]
        ],
        'operators': [
            r'%s' % o for o in [
                '=', '==', '!=', '<', '<=', '>', '>=',  # Comparison
                r'\+', '-', r'\*', '/', '//', r'\%', r'\*\*',  # Arithmetic
                r'\+=', '-=', r'\*=', '/=', r'\%=',  # In-place
                r'\^', r'\|', r'\&', r'\~', r'>>', r'<<',  # Bitwise
            ]
        ],
        'braces': [
            r'%s' % b for b in ['\{', '\}', '\(', '\)', '\[', '\]']
        ],
        'string': [
            r'"[^"\\]*(\\.[^"\\]*)*"',  # Double-quoted strings
            r"'[^'\\]*(\\.[^'\\]*)*'",   # Single-quoted strings
        ],
        'multi_line_strings': [ ],
        'self': [
            r'\bself\b',
        ],
        'defclass': [
            r'\bdef\b\s*(\w+)',  # Function definition
            r'\bclass\b\s*(\w+)',  # Class definition
        ],
        'comment': [
            r'#[^\n]*',  # Comments
        ],
        'numbers': [
            r'\b[+-]?[0-9]+[lL]?\b',  # Integer literals
            r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b',  # Hexadecimal literals
            r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b',  # Float literals
        ]
    }

    highlighting_rules = {
        'keywords': [(QtCore.QRegularExpression(rule), 0, STYLES['keyword']) for rule in python_highlighter_rules['keywords']],
        'operators': [(QtCore.QRegularExpression(rule), 0, STYLES['operator']) for rule in python_highlighter_rules['operators']],
        'braces': [(QtCore.QRegularExpression(rule), 0, STYLES['brace']) for rule in python_highlighter_rules['braces']],
        'strings': [(QtCore.QRegularExpression(rule), 0, STYLES['string']) for rule in python_highlighter_rules['string']],
        'multi_line_strings': [(QtCore.QRegularExpression(rule), 0, STYLES['string2']) for rule in python_highlighter_rules['multi_line_strings']],
        'self': [(QtCore.QRegularExpression(rule), 0, STYLES['self']) for rule in python_highlighter_rules['self']],
        'defclass': [(QtCore.QRegularExpression(rule), 1, STYLES['defclass']) for rule in python_highlighter_rules['defclass']],
        'comments': [(QtCore.QRegularExpression(rule), 0, STYLES['comment']) for rule in python_highlighter_rules['comment']],
        'numbers': [(QtCore.QRegularExpression(rule), 0, STYLES['numbers']) for rule in python_highlighter_rules['numbers']],
    }
    ```
            """
        def rehighlite(self) -> None: """Перезагружает подсветку синтаксиса"""
        def setMmapHidden(self, b: bool) -> None: """Скрывает миникарту"""
        def isMmapHidden(self) -> bool: """Проверяет скрыта ли миникарта"""
        def initTagFile(self, path: str) -> None: """Добавляет файл в БД с хэштегами"""
        def getTags(self, path: str) -> list: """Получает хэштеги файла"""
        def addTag(self, path: str, tag: str) -> None: """Добавляет хэштег файлу"""
        def removeTag(self, path: Optional[str] = None, tag: Optional[str] = None, show: bool = False) -> None: """Удаляет хэштег файла"""
        def getTagFiles(self, tag: str) -> list: """Получает все файлы с хэштегом %s"""
    class Selection:
        def __init__(self, regions: Optional[List['VtAPI.Region']] = None) -> None: """Задается список регионов выделения"""
        def clear(self) -> None: """Очищает все регионы в текущем выделении"""
        def add(self, region: 'VtAPI.Region') -> None: """Добавляет новый регион в текущее выделение."""
        def subtract(self, region: 'VtAPI.Region') -> None: """Удаляет указанный регион из текущего выделения."""
        def contains(self, point: 'VtAPI.Point') -> bool: """Проверяет наличие точки в выделении"""
        def text(self, view: 'VtAPI.View', region: 'VtAPI.Region') -> str: """Возвращает текст выделения"""
    class Region:
        def __init__(self, a: int, b: int) -> None: """Задаются границы региона"""
        def begin(self) -> int: """Получает начальную точку региона"""
        def end(self) -> int: """Получает конечную точку региона"""
        def contains(self, point: int) -> bool: """Проверяет наличие точки в регионе"""
    class Settings:
        """Устаревшая конструкция. Обновленная версия addKey, findKey"""
        def __init__(self, settings: Optional[dict] = None) -> None: """Задается список настроек в формате JSON"""
        def get(self, key: str, default: Optional[str] = None) -> Optional[str]: """Получить значение по ключу"""
        def set(self, key: str, value: str) -> None: """Установить значение по ключу"""
        def erase(self, key: str) -> None: """Очистить ключ"""
        def has(self, key: str) -> bool: """Проверить наличие ключа"""
    class Dialogs:
        """Тут все диалоговые окна которые можно использовать"""
        @staticmethod
        def infoMessage(string: Optional[str] = "Message", title: Optional[str] = "Dialog") -> None: ...
        @staticmethod
        def warningMessage(string: Optional[str] = "Message", title: Optional[str] = "Dialog") -> None: ...
        @staticmethod
        def errorMessage(string: Optional[str] = "Message", title: Optional[str] = "Dialog") -> None: ...
        @staticmethod
        def okCancelDialog(string: Optional[str] = "Message", title: Optional[str] = "Dialog") -> bool: ...
        @staticmethod
        def yesNoCancelDialog(string: Optional[str] = "Message", title: Optional[str] = "Dialog") -> str: ...
        @staticmethod
        def openFileDialog(title: Optional[str] = "Dialog") -> List[str]: ...
        @staticmethod
        def saveFileDialog(title: Optional[str] = "Dialog") -> str: ...
        @staticmethod
        def openDirDialog(title: Optional[str] = "Dialog") -> str: ...
        @staticmethod
        def inputDialog(title: Optional[str] = "Dialog") -> Optional[str]: ...
    class File:
        """Упрощение доступа к файлам"""
        def __init__(self, path: Optional[str] = None, encoding="utf-8"): ...
        def read(self, chunk=1024) -> List[str]: """Возвращает список состоящий из блоков текста, разюитого по длинне чанка"""
        def exists(self) -> bool: """Проверяет существует ли файл"""
        def create(self, rewrite=False) -> None: """Очищает/создает файл"""
    class Theme:
        """Файл темы"""
        def __init__(self, name: Optional[str] = None, path: Optional[str] = None): ...
        def use(self, window: "VtAPI.Window" = None) -> None: """Устанавливает тему для окна"""
        def exists(self) -> bool: """Проверяет существует ли тема"""
    class Plugin:
        """Все виды команд которые можно использовать"""
        class TextCommand:
            """Команда которую лучше использовать для взаимодействий в активном текстовом виджете"""
            def __init__(self, api: 'VtAPI', view: 'VtAPI.View') -> None: ...
            def run(self, edit: Any) -> None: ...
            def is_enabled(self) -> bool: ...
            def is_visible(self) -> bool: ...
            def description(self) -> str: ...
        class WindowCommand:
            """Команда которую лучше использовать для расширенного использования вкладок и окна"""
            def __init__(self, api: 'VtAPI', window: 'VtAPI.Window') -> None: ...
            def run(self) -> None: ...
            def is_enabled(self) -> bool: ...
            def is_visible(self) -> bool: ...
            def description(self) -> str: ...
        class ApplicationCommand:
            """Команда в которую можно использовать для чего угодно или использовать как базу для других типов команд"""
            def __init__(self, api: 'VtAPI') -> None: ...
            def run(self) -> None: ...
            def is_enabled(self) -> bool: ...
            def is_visible(self) -> bool: ...
            def description(self) -> str: ...
    class Point:
        """Редко используемая конструкция"""
        def __init__(self, x: int = 0, y: int = 0) -> None:
            self.x = x
            self.y = y
        def move(self, dx: int, dy: int) -> None: ...
        def distance_to(self, other: 'VtAPI.Point') -> float: ...
        def __str__(self) -> str: ...
        def __eq__(self, other: 'VtAPI.Point') -> bool: ...
    class Signals(QObject):
        """Класс с сигналами для окна"""
        tabClosed = pyqtSignal(object)
        tabCreated = pyqtSignal()
        tabChanged = pyqtSignal()
        textChanged = pyqtSignal()
        windowClosed = pyqtSignal()
        windowStarted = pyqtSignal()
        fileOpened = pyqtSignal(object)
        fileSaved = pyqtSignal(object)
        def __init__(self, w: QMainWindow) -> None: ...
        def addSignal(self, signalName: str, signalArgs: list) -> None: """Команда не работает и крашит приложение, т к PyQt6 не даёт привязывать pyqtSignal динамически"""
        def findSignal(self, signalName: str) -> pyqtSignal: """Ищет сигнал по названию"""
    class Widgets:
        """Тут описаны все дополнительные виджеты которые можно использовать (библиотека PyQt6 заблокирована для импорта)"""
        class DockWidget(QDockWidget):
            def __init__(self, parent: Optional[QWidget] = None) -> None: ...
            def parent(self) -> Optional[QWidget]: ...
            def window(self) -> Optional[QMainWindow]: ...
        class Dialog(QDialog):
            def __init__(self, parent: Optional[QWidget] = None) -> None: ...
            def parent(self) -> Optional[QWidget]: ...
            def window(self) -> Optional[QMainWindow]: ...
        class Thread(QThread):
            def __init__(self) -> None: ...
            def parent(self) -> Optional[QWidget]: ...
        class Process(QProcess):
            def __init__(self) -> None: ...
        class ToolBar(QToolBar):
            def __init__(self, *args, **kwargs): ...
        class Action(QAction):
            def __init__(self, *args, **kwargs): ...
    def activeWindow(self) -> 'Window': """Получает активное окно (активным окном считается последнее окно в котором находился курсор)"""
    def windows(self) -> List['Window']: """Получает список окон"""
    def addWindow(self, window: 'Window') -> None: """Добавляет окно"""
    def loadSettings(self, path: Optional[str] = None, pl: Optional[str] = None) -> dict: """Загружает настройки по файлу. Не работает и не нужно"""
    def saveSettings(self, data: dict, path: Optional[str] = None, pl: Optional[str] = None) -> None: """Сохраняет настройки в файл. Не работает и не нужно"""
    def importModule(self, name: str) -> Any: """Импортирует модуль по его названию"""
    def setTimeout(self, function: callable, delay: int) -> None: """Ставит таймер"""
    async def setTimeout_async(self, function: callable, delay: int) -> None: """Ставит асинхронный таймер"""
    def version(self) -> str: """Получает версию API"""
    def platform(self) -> str: """Получает название системы"""
    def arch(self) -> str: """Получает архитектуру системы"""
    def replaceConsts(self, data: dict, constants: dict) -> str: """Заменяет %переменные% их значениями в PATH"""
    def findKey(self, p: str, d: dict) -> Optional[str]: """Ищет ключ по пути через точку (key1.key2.key3)"""
    def addKey(self, p: str, value: str, d: dict) -> None: """Добавляет ключ и значение по пути через точку (key1.key2.key3)"""
    def replacePaths(self, data: str) -> str: """Устаревшая конструкция (вроде) но используется в package managerе"""
    def defineLocale(self) -> str: """Определяет язык системы"""
    def packagesPath(self) -> str: """Возвращает путь до папки с пакетами (Можно изменить в {app}/ui/Main.settings)"""