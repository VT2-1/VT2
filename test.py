from PyQt6 import QtCore, QtWidgets
import os

class MyApp:
    def __init__(self):
        self.translator = QtCore.QTranslator()

    def loadTranslations(self, qm_file_path):
        if os.path.isfile(qm_file_path):
            if self.translator.load(qm_file_path):
                QtCore.QCoreApplication.installTranslator(self.translator)
                print(f"Loaded translation from {qm_file_path}")
            else:
                print("Failed to load translation.")
        else:
            print(f"Translation file not found: {qm_file_path}")

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowTitle(QtCore.QCoreApplication.translate("MainWindow", "My Application"))
        MainWindow.resize(800, 600)

        menu_bar = MainWindow.menuBar()
        file_menu = menu_bar.addMenu(QtCore.QCoreApplication.translate("MainMenu", "File"))
        file_menu.addAction(QtCore.QCoreApplication.translate("MainMenu", "New file"))

# Пример использования
app = QtWidgets.QApplication([])

my_app = MyApp()

# Загрузка .qm файла (укажите полный путь к вашему .qm файлу)
my_app.loadTranslations("ru.qm")

# Создание основного окна
window = QtWidgets.QMainWindow()
my_app.setupUi(window)

window.show()
app.exec()
