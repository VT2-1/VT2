import json
from pathlib import Path

import pytest


def test_settings_file_has_platform_package_dirs():
    data = json.loads(Path("ui/Main.settings").read_text())
    assert "packageDirs" in data
    assert "packageDirss" not in data


@pytest.fixture(scope="session")
def qt_widgets():
    return pytest.importorskip(
        "PySide6.QtWidgets",
        reason="PySide6/Qt runtime dependencies are unavailable",
        exc_type=ImportError,
    )


@pytest.fixture(scope="session")
def app(qt_widgets):
    """Создаём глобальный экземпляр QApplication для всех тестов."""
    app = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])
    yield app
    app.quit()


@pytest.fixture
def api(app):
    """Создаём экземпляр VtAPI для тестов."""
    from api import VtAPI

    return VtAPI(app)


@pytest.fixture
def main_window(api, qtbot):
    """Создаём главное окно приложения."""
    from ui import MainWindow

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
    from api import VtAPI

    result = []

    class TestCommand(VtAPI.Plugin.ApplicationCommand):
        def run(self):
            result.append("Command Executed")
            return "Command Executed"

    main_window.api.activeWindow.registerCommandClass({"command": TestCommand})
    command = {"command": "TestCommand"}
    main_window.api.activeWindow.runCommand(command)
    assert result == ["Command Executed"]


def test_add_and_remove_tags(main_window):
    """Тестируем добавление и удаление тегов."""
    test_tag = "TestTag"
    test_file = "test.txt"

    main_window.api.activeWindow.activeView.addTag(test_file, test_tag)
    assert test_tag in main_window.api.activeWindow.activeView.getTags(test_file)
    main_window.api.activeWindow.activeView.removeTag(test_file, test_tag)
    assert test_tag not in main_window.api.activeWindow.activeView.getTags(test_file)
