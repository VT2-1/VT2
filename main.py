from ui import MainWindow, QtWidgets
from api import VtAPI

import sys
import traceback

def main():
    app = QtWidgets.QApplication(sys.argv)
    api = VtAPI(app)
    MainWindow(api)
    return app.exec()

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise
