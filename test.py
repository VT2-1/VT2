import sys
from PyQt6 import QtWidgets, QtCore
import platform

class MyAPI:
    def __init__(self):
        self.app = QtWidgets.QApplication.instance()
        print(self.app)
        self.windows = []
        self.active_window = None

    class Window:
        def __init__(self, api, views=None, active_view=None, qmwclass: QtWidgets.QMainWindow=None):
            self.__api = api
            self.__mw = qmwclass
            self.views = views or []
            self.active_view = active_view

            self.__api.windows.append(self)

        def new_file(self):
            """Создаёт новое пустое окно."""
            self.__mw.addTab()
            tab = self.__mw.tabWidget.currentWidget()
        
        def open_file(self, file_path):
            """Имитация открытия файла."""
            print(f"Opening file: {file_path}")
        
        def active_view(self):
            return self.active_view
        
        def views(self):
            return self.views
        
        def focus_view(self, view):
            self.active_view = view
        
        def run_command(self, command_name, args={}):
            """Запускает команду."""
            print(f"Running command: {command_name} with args: {args}")
        
        def show_quick_panel(self, items, on_select, on_highlight=None, flags=0, selected_index=-1):
            """Показывает панель быстрого выбора."""
            print(f"Showing quick panel with items: {items}")
        
        def show_input_panel(self, prompt, initial_text, on_done, on_change=None, on_cancel=None):
            """Показывает панель ввода."""
            print(f"Showing input panel with prompt: {prompt} and initial text: {initial_text}")

    class View:
        def __init__(self, api, window, qwclass=None, text="", syntax_file=None, file_name=None, read_only=False):
            self.__api = api
            self.window = window
            self.__tab = qwclass
            self.text = text
            self.syntax_file = syntax_file
            self.file_name = file_name
            self.read_only = read_only

        def window(self):
            return self.window

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

        def begin_edit(self):
            pass

        def end_edit(self):
            pass

        def find(self, pattern, start_point, flags=0):
            pass

        def find_all(self, pattern, flags=0):
            pass

        def set_syntax_file(self, syntax_file_path):
            self.syntax_file = syntax_file_path

        def settings(self):
            pass

        def file_name(self):
            return self.file_name

        def is_dirty(self):
            pass

        def is_read_only(self):
            return self.read_only

        def show_popup(self, content, flags=0, location=-1, max_width=320, max_height=240, on_navigate=None, on_hide=None):
            self.content = content
            self.flags = flags
            self.location = location
            self.max_width = max_width
            self.max_height = max_height
            self.on_navigate = on_navigate
            self.on_hide = on_hide

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

    class Plugin:
        class TextCommand:
            def __init__(self, view):
                self.view = view

            def run(self, edit):
                pass
            
            def is_enabled(self):
                pass
            
            def is_visible(self):
                pass
            
            def description(self):
                pass

        class WindowCommand:
            def __init__(self, window):
                self.window = window

            def run(self):
                pass
            
            def is_enabled(self):
                pass
            
            def is_visible(self):
                pass
            
            def description(self):
                pass

        class ApplicationCommand:
            def __init__(self):
                pass

            def run(self):
                pass
            
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
            if not isinstance(other, MyAPI.Point):
                raise ValueError("The other must be an instance of Point.")
            return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

        def __str__(self):
            """Строковое представление точки."""
            return f"Point({self.x}, {self.y})"

        def __eq__(self, other):
            """Сравнение двух точек."""
            if isinstance(other, MyAPI.Point):
                return self.x == other.x and self.y == other.y
            return False

    def active_window(self) -> Window:
        """Возвращает текущее активное окно (экземпляр Window)."""
        return self.active_window

    def windows(self):
        """Возвращает список всех открытых окон."""
        return self.windows

    def load_settings(self, name):
        """Загружает настройки из файла .sublime-settings."""
        pass  # Загружаем настройки из файла

    def save_settings(self, name):
        """Сохраняет настройки в файл .sublime-settings."""
        pass  # Сохраняем настройки в файл

    def message_dialog(self, string):
        """Показывает диалоговое окно с сообщением."""
        QtWidgets.QMessageBox.information(None, "Message", string)

    def error_message(self, string):
        """Показывает диалоговое окно с ошибкой."""
        QtWidgets.QMessageBox.critical(None, "Error", string)

    def ok_cancel_dialog(self, string, ok_title="OK"):
        """Показывает диалоговое окно с кнопками 'OK' и 'Отмена'."""
        result = QtWidgets.QMessageBox.question(None, "Confirmation", string,
                                       QtWidgets.QMessageBox.StandardButton.Ok | QtWidgets.QMessageBox.StandardButton.Cancel,
                                       QtWidgets.QMessageBox.StandardButton.Cancel)
        return result == QtWidgets.QMessageBox.StandardButton.Ok

    def yes_no_cancel_dialog(self, string):
        """Показывает диалог с вариантами 'Да', 'Нет' и 'Отмена'."""
        result = QtWidgets.QMessageBox.question(None, "Confirmation", string,
                                       QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No | QtWidgets.QMessageBox.StandardButton.Cancel,
                                       QtWidgets.QMessageBox.StandardButton.Cancel)
        if result == QtWidgets.QMessageBox.StandardButton.Yes:
            return "yes"
        elif result == QtWidgets.QMessageBox.StandardButton.No:
            return "no"
        else:
            return "cancel"

    def status_message(self, string):
        """Показывает сообщение в строке состояния."""
        print(f"Status: {string}")  # В реальном приложении можно использовать виджет состояния

    def set_timeout(self, function, delay):
        """Запускает функцию через определенное время (в миллисекундах)."""
        QtCore.QTimer.singleShot(delay, function)

    def set_timeout_async(self, function, delay):
        """Асинхронный аналог set_timeout."""
        self.set_timeout(function, delay)

    def score_selector(self, location, scope):
        """Возвращает числовую оценку соответствия между областью синтаксиса (scope) и текстом в location."""
        return 100  # Имитация оценки

    def version(self):
        """Возвращает версию Sublime Text."""
        return "4.0"  # Имитация версии

    def platform(self):
        """Возвращает платформу ('windows', 'osx', 'linux')."""
        return sys.platform

    def arch(self):
        """Возвращает архитектуру ('x86', 'x64', 'amd64')."""
        if sys.maxsize > 2**32:
            if platform.system() == "Windows":
                return "x64"
            else:
                return "amd64"
        else:
            return "x86"

    def packages_path(self):
        """Возвращает путь к каталогу 'Packages'."""
        return "/path/to/packages"  # Указать актуальный путь

    def installed_packages_path(self):
        """Возвращает путь к каталогу 'Installed Packages'."""
        return "/path/to/installed/packages"  # Указать актуальный путь
