from PySide6 import QtWidgets, QtGui, QtCore
from typing import *


highlighting_rules = {
    'keywords': {
        'pattern': [r'\b%s\b' % w for w in [
            'and', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'exec', 'finally',
            'for', 'from', 'global', 'if', 'import', 'in',
            'is', 'lambda', 'not', 'or', 'pass', 'print',
            'raise', 'return', 'try', 'while', 'yield',
            'None', 'True', 'False',
        ]],
        'color': '#C87832',
        'weight': 'bold',
    },
    'operators': {
        'pattern': [r'%s' % o for o in [
            '=', '==', '!=', '<', '<=', '>', '>=',  # Comparison
            r'\+', '-', r'\*', '/', '//', r'\%', r'\*\*',  # Arithmetic
            r'\+=', '-=', r'\*=', '/=', r'\%=',  # In-place
            r'\^', r'\|', r'\&', r'\~', r'>>', r'<<',  # Bitwise
        ]],
        'color': '#969696',
    },
    'braces': {
        'pattern': [r'%s' % b for b in ['\{', '\}', '\(', '\)', '\[', '\]']],
        'color': '#A9A9A9',
    },
    'strings': {
        'pattern': [
            r'"[^"\\]*(\\.[^"\\]*)*"',  # Double-quoted strings
            r"'[^'\\]*(\\.[^'\\]*)*'",   # Single-quoted strings
        ],
        'color': '#146E64',
    },
    "multi_line_strings": {
        'start': r'"""',
        'end': r'"""',
        'color': '#1E786E',
    },
    'self': {
        'pattern': [r'\bself\b'],
        'color': '#96558C',
        'weight': 'italic',
    },
    'defclass': {
        'pattern': [
            r'\bdef\b\s*(\w+)',  # Function definition
            r'\bclass\b\s*(\w+)',  # Class definition
        ],
        'bg': 'transparent',
        'color': '#DCDCFF',
        'weight': 'bold',
    },
    'comments': {
        'pattern': [r'#[^\n]*'],  # Comments
        'bg': 'transparent',
        'color': '#808080',
    },
    'numbers': {
        'pattern': [
            r'\b[+-]?[0-9]+[lL]?\b',  # Integer literals
            r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b',  # Hexadecimal literals
            r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b',  # Float literals
        ],
        'bg': 'transparent',
        'color': '#6496BE',
    },
}

class Region:
    def __init__(self, block: QtGui.QTextBlock):
        self.block = block
    
    def begin(self):
        return self.block.position()
    
    def end(self):
        return self.block.position() + self.block.length()-1
    
    def line(self):
        return self.block.blockNumber()+1
    
    def size(self):
        return self.block.length()-1

    def text(self) -> str:
        return self.block.text()
    
class SyntaxHL(QtGui.QSyntaxHighlighter):
    def __init__(self, textEdit):
        self.textEdit: QtWidgets.QPlainTextEdit = textEdit
        super().__init__(self.textEdit.document())

        self.mLRules = []
        self.highlightRules = {}
        self.additData = []

    def setHLRule(self, name, rule):
        if name == "multi_line_strings":
            self.mLRules.append(rule)
        if "pattern" in rule:
            self.highlightRules[name] = {}
            self.highlightRules[name]["patterns"] = []
            for pattern in rule["pattern"]:
                self.highlightRules[name]["patterns"].append(QtCore.QRegularExpression(pattern))

            text_format = QtGui.QTextCharFormat()
            if 'color' in rule:
                text_format.setForeground(QtGui.QColor(rule['color']))
            if 'bg' in rule:
                text_format.setBackground(QtGui.QColor(rule['bg']))
            if 'weight' in rule:
                if rule['weight'] == 'bold':
                    text_format.setFontWeight(QtGui.QFont.Weight.Bold)
                elif rule['weight'] == 'italic':
                    text_format.setFontItalic(True)
            self.highlightRules[name]["format"] = text_format

    def highlightBlock(self, region: Region):
        if isinstance(region, Region):
            text = region.text()
            start_offset = region.begin()

            for cat, rule in self.highlightRules.items():
                regexes = rule["patterns"]
                for regex in regexes:
                    match_iterator = regex.globalMatch(text)
                    while match_iterator.hasNext():
                        match_item = match_iterator.next()
                        if match_item is None:
                            continue

                        start_pos = match_item.capturedStart() + start_offset
                        length = match_item.capturedLength()

                        # Apply the formatting
                        self.setFormat(start_pos, length, rule["format"])

            self.setCurrentBlockState(0)
            self.textEdit.viewport().update()  # Force the widget to update

class TextEdit(QtWidgets.QTextEdit):
    textEdited = QtCore.Signal(Region, int)
    def __init__(self):
        super().__init__()
        self.textChanged.connect(self.on_text_changed)
        self.textEdited.connect(self.onTextEdited)

        self.highlighter = SyntaxHL(self)

    def on_text_changed(self):
        cursor = self.textCursor()
        region = Region(cursor.block())
        pos = cursor.positionInBlock()
        self.textEdited.emit(region, pos)

    @QtCore.Slot(Region, int)
    def onTextEdited(self, region: Region, pos: int):
        self.highlighter.highlightBlock(region)

    def regions(self) -> list[Region]:
        first_block = self.firstVisibleBlock()
        viewport_rect = self.viewport().rect()
        cursor = self.cursorForPosition(QtCore.QPoint(0, viewport_rect.bottom()))
        last_block_number = cursor.blockNumber()
        regions = []
        block = first_block
        while block.isValid() and block.blockNumber() <= last_block_number:
            regions.append(Region(block))
            block = block.next()
        return regions

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.textEdit = TextEdit()
        self.setCentralWidget(self.textEdit)
        self.setFixedHeight(40)

        for n, v in highlighting_rules.items():
            self.textEdit.highlighter.setHLRule(n, v)

app = QtWidgets.QApplication([])
w = MainWindow()
w.show()
import sys
sys.exit(app.exec())
