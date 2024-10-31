import chardet
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QTextEdit, QFileDialog

class FileReaderThread(QThread):
    # Сигнал для передачи считанных данных в основной поток
    line_read = pyqtSignal(str)

    def __init__(self, file_path: str, buffer_size: int = 1024, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.buffer_size = buffer_size  # Размер буфера чтения для постепенного добавления
        self._is_running = True

    def run(self):
        # Определение кодировки файла
        with open(self.file_path, 'rb') as f:
            raw_data = f.read(1024)  # Примерное чтение первых 1024 байт для анализа
            encoding_info = chardet.detect(raw_data)
            encoding = encoding_info.get('encoding', 'utf-8')

        # Постепенное чтение файла с определенной кодировкой
        with open(self.file_path, 'r', encoding=encoding) as f:
            while self._is_running:
                chunk = f.read(self.buffer_size*3)
                if not chunk:
                    break
                self.line_read.emit(chunk)  # Отправка данных в основной поток
                self.msleep(7)  # Задержка для эффекта постепенного добавления

    def stop(self):
        self._is_running = False

# Класс основного окна, содержащего QTextEdit и запускающего поток чтения
class FileLoader(QTextEdit):
    def __init__(self, file_path: str):
        super().__init__()
        self.file_reader_thread = FileReaderThread(file_path)
        self.file_reader_thread.line_read.connect(self.append_text)
        self.file_reader_thread.start()

    @pyqtSlot(str)
    def append_text(self, text: str):
        self.moveCursor(self.textCursor().MoveOperation.End)
        self.insertPlainText(text)

    def closeEvent(self, event):
        # Остановка потока при закрытии окна
        self.file_reader_thread.stop()
        self.file_reader_thread.wait()
        event.accept()

from PyQt6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
file_path = r'C:\Users\Trash\Downloads\wikipedia-logotype-of-earth-puzzle-svgrepo-com.svg'
file_loader = FileLoader(file_path)
file_loader.show()
sys.exit(app.exec())
