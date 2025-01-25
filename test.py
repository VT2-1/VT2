from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QFrame, QSplitter, QTabWidget
)
from PySide6.QtCore import Qt, QPropertyAnimation


class SideMenu(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VSCode-like Side Menu")

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Splitter to separate side menu and tab widget
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.main_layout.addWidget(self.splitter)

        # Left panel: Icon bar
        self.icon_frame = QFrame()
        self.icon_frame.setFixedWidth(50)
        self.icon_frame.setStyleSheet("background-color: #2D2D2D;")

        self.icon_layout = QVBoxLayout(self.icon_frame)
        self.icon_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_layout.setSpacing(0)

        self.lastWidth = 0

        # Add icons
        self.buttons = []
        for i in range(4):
            btn = QPushButton(f"Tab {i+1}")
            btn.setCheckable(True)
            btn.setStyleSheet("color: white; background: none; border: none; padding: 10px;")
            btn.clicked.connect(lambda _, idx=i: self.switch_tab(idx))
            self.icon_layout.addWidget(btn)
            self.buttons.append(btn)

        # Filler to push icons to the top
        self.icon_layout.addStretch()

        # Right panel: Content for tabs
        self.content_frame = QFrame()
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: #3C3F41;")
        for i in range(4):
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.addWidget(QPushButton(f"Content for Tab {i+1}"))
            tab_layout.setContentsMargins(10, 10, 10, 10)
            self.content_stack.addWidget(tab)

        self.content_layout.addWidget(self.content_stack)

        # Add left and right panels to splitter
        self.splitter.addWidget(self.icon_frame)
        self.splitter.addWidget(self.content_frame)
        self.splitter.setSizes([50, 950])  # Set initial sizes: icons fixed, content flexible

        # Animation for hiding content
        self.is_hidden = False

    def switch_tab(self, index):
        self.content_stack.setCurrentIndex(index)
        for btn in self.buttons:
            btn.setChecked(False)
        self.buttons[index].setChecked(True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_B and event.modifiers() == Qt.ControlModifier:
            self.toggle_tabs()

    def toggle_tabs(self):
        if not self.is_hidden:
            self.lastWidth = self.content_frame.width()
            self.splitter.setSizes([50, 0])  # Set initial sizes: icons fixed, content flexible
        else:
            self.splitter.setSizes([50, self.lastWidth])  # Set initial sizes: icons fixed, content flexible
        self.is_hidden = not self.is_hidden

if __name__ == "__main__":
    app = QApplication([])
    window = SideMenu()
    window.show()
    app.exec()
