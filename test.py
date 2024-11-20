from PyQt6.QtWidgets import QApplication, QTextEdit, QWidget, QVBoxLayout, QPushButton
from PyQt6.QtGui import QFocusEvent
import sys

class CustomTextEdit(QTextEdit):
    def focusInEvent(self, event: QFocusEvent):
        super().focusInEvent(event)
        print("TextEdit gained focus")  # Проверяем, вызывается ли этот метод

    def focusOutEvent(self, event: QFocusEvent):
        super().focusOutEvent(event)
        print("TextEdit lost focus")  # Проверяем, вызывается ли этот метод

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        self.text_edit = CustomTextEdit(self)
        self.text_edit2 = QTextEdit(self)
        self.button = QPushButton("Focus TextEdit", self)
        self.button.clicked.connect(self.focus_text_edit)
        
        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addWidget(self.text_edit2)
        layout.addWidget(self.button)
        self.setLayout(layout)
    
    def focus_text_edit(self):
        self.text_edit.setFocus()  # Принудительно устанавливаем фокус на TextEdit
    def focusInEvent(self, a0):
        print("Window focused")
        return super().focusInEvent(a0)

app = QApplication(sys.argv)
window = MainWindow()
window.show()
window2 = MainWindow()
window2.show()
sys.exit(app.exec())