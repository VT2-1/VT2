from PyQt6.QtWidgets import QApplication, QTextEdit
from PyQt6.QtGui import QKeySequence, QKeyEvent
from PyQt6.QtCore import Qt

class CustomTextEdit(QTextEdit):
    def __init__(self):
        super().__init__()

    def keyPressEvent(self, event: QKeyEvent):
        # Проверяем хоткеи и выполняем свои действия
        if event.matches(QKeySequence.StandardKey.Copy):
            self.custom_copy()
        elif event.matches(QKeySequence.StandardKey.Paste):
            self.custom_paste()
        elif event.matches(QKeySequence.StandardKey.Cut):
            self.custom_cut()
        elif event.matches(QKeySequence.StandardKey.Undo):
            self.custom_undo()
        elif event.matches(QKeySequence.StandardKey.Redo):
            self.custom_redo()
        else:
            # Если комбинация не совпала, обрабатываем событие стандартным образом
            super().keyPressEvent(event)

    # Свои методы для действий
    def custom_copy(self):
        print("Custom Copy Action Triggered")

    def custom_paste(self):
        print("Custom Paste Action Triggered")

    def custom_cut(self):
        print("Custom Cut Action Triggered")

    def custom_undo(self):
        print("Custom Undo Action Triggered")

    def custom_redo(self):
        print("Custom Redo Action Triggered")

app = QApplication([])
text_edit = CustomTextEdit()
text_edit.setPlainText("Попробуйте скопировать, вставить или отменить изменения")
text_edit.show()
app.exec()
