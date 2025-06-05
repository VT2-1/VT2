from ui import MainWindow, QtWidgets
from api import VtAPI

import sys

def main():
    sys.path.insert(0, ".")
    app = QtWidgets.QApplication(sys.argv)
    api = VtAPI(app)
    w = MainWindow(api)
    sys.exit(app.exec())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)