from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import QProcess
import os

class TerminalWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Script Runner")

        self.run_button = QPushButton("Run Python Script", self)
        self.run_button.clicked.connect(self.run_python_script)

        layout = QVBoxLayout()
        layout.addWidget(self.run_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.process = QProcess(self)

    def run_python_script(self):
        python_script_path = "ui.py"
        if os.name == 'nt':
            self.process.start("cmd.exe", ["/k", f"python {python_script_path} & pause"])
        else:
            self.process.start("x-terminal-emulator", ["-e", f"bash -c 'python3 {python_script_path}; read -p \"Press Enter to continue...\"'"])

app = QApplication([])
window = TerminalWindow()
window.show()
app.exec()
