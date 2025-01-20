import heapq
from PySide6 import QtCore, QtWidgets

class SignalWithPriority(QtCore.QObject):
    """
    Custom signal with priority support.
    """
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._signal = QtCore.Signal(*args)
        self._queue = []
        self._timer = QtCore.QTimer(self)
        self._args = []
        self._kwargs = {}

    def connect(self, slot, priority=1):
        """
        Connects a slot to the signal with a specified priority.
        """
        self._queue.append((priority, slot))

    def emit(self, *args, **kwargs):
        """
        Emits the signal, calling all connected slots in order of priority.
        """
        while self._queue:
            priority, slot = max(self._queue)
            print(priority)
            self._queue.pop(self._queue.index(max(self._queue)))
            slot(*args, **kwargs)

# Example usage
class ExampleWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Signal with Priority Example")
        self.setGeometry(100, 100, 300, 200)

        # Create a custom signal with priority handling
        self.signal = SignalWithPriority(str)

        # Connect slots with different priorities
        self.signal.connect(self.on_first_slot, priority=1)
        self.signal.connect(self.on_second_slot, priority=10)

        # Button to emit signal
        self.button = QtWidgets.QPushButton("Emit Signal", self)
        self.button.clicked.connect(self.emit_signal)
        self.button.setGeometry(50, 50, 200, 50)

    def emit_signal(self):
        """Emit the custom signal when the button is clicked."""
        print("Emitting signal...")
        self.signal.emit("str")  # Emit the signal, triggering connected slots

    def on_first_slot(self, s):
        """Slot with higher priority (priority=2)."""
        print(f"First Slot (priority 2): {s}")

    def on_second_slot(self, s):
        """Slot with lower priority (priority=1)."""
        print(f"Second Slot (priority 1): {s}")


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = ExampleWindow()
    window.show()
    app.exec()
