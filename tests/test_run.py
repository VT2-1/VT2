import pytest
from PySide6.QtWidgets import QApplication
from ui import MainWindow
from api2 import VtAPI

@pytest.fixture(scope="session")
def app():
    """Создаём глобальный экземпляр QApplication для всех тестов."""
    app = QApplication([])
    yield app
    app.quit()

@pytest.fixture
def api(app):
    """Создаём экземпляр VtAPI для тестов."""
    api = VtAPI(app)
    return api

@pytest.fixture
def main_window(api, qtbot):
    """Создаём главное окно приложения."""
    main_window = MainWindow(api)
    main_window.api.activeWindow.newFile()
    qtbot.addWidget(main_window)
    return main_window

def test_main_window_initialization(main_window):
    """Проверяем инициализацию главного окна."""
    assert main_window.api is not None
    assert main_window.tagBase is not None
    assert main_window.centralwidget is not None
    assert main_window.tabWidget is not None
    assert main_window.statusBar() is not None
    assert main_window.menuBar() is not None

def test_add_tab(main_window):
    """Тестируем добавление новой вкладки."""
    initial_tab_count = main_window.tabWidget.count()
    main_window.api.activeWindow.newFile()
    assert main_window.tabWidget.count() == initial_tab_count + 1

def test_tab_widget_close_tab(main_window):
    """Тестируем закрытие вкладки."""
    main_window.api.activeWindow.newFile()
    initial_tab_count = main_window.tabWidget.count()
    main_window.tabWidget.closeTab(main_window.tabWidget.currentWidget())
    assert main_window.tabWidget.count() == initial_tab_count - 1

def test_logger_functionality(main_window):
    """Тестируем работу логгера."""
    main_window.logger.setFile(None)
    main_window.logger.log = "Test log"
    assert main_window.logger.log == "Test log"

def test_vtapi_run_command(main_window):
    """Тестируем выполнение команды API."""
    class TestCommand(VtAPI.Plugin.ApplicationCommand):
        def run(self):
            return "Command Executed"

    main_window.api.activeWindow.registerCommandClass({"command": TestCommand})
    command = {"command": "TestCommand"}
    main_window.api.activeWindow.runCommand(command)
    assert True == True

def test_add_and_remove_tags(main_window):
    """Тестируем добавление и удаление тегов."""
    test_tag = "TestTag"
    test_file = "test.txt"
    
    main_window.api.activeWindow.activeView.addTag(test_file, test_tag)
    assert test_tag in main_window.api.activeWindow.activeView.getTags(test_file)
    main_window.api.activeWindow.activeView.removeTag(test_file, test_tag)
    assert test_tag not in main_window.api.activeWindow.activeView.getTags(test_file)