import re
from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat, QFont
from PySide6.QtWidgets import QTextEdit, QApplication

class SyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document, highlighting_rules):
        super().__init__(document)
        self.highlighting_rules = highlighting_rules

    def highlightBlock(self, text):
        for category, rule in self.highlighting_rules.items():
            text_format = QTextCharFormat()
            text_format.setForeground(QColor(rule['color']))
            if 'weight' in rule:
                if rule['weight'] == 'bold':
                    text_format.setFontWeight(QFont.Weight.Bold)
                elif rule['weight'] == 'italic':
                    text_format.setFontItalic(True)
            
            if 'bg' in rule:
                text_format.setBackground(QColor(rule['bg']))
            
            for pattern in rule['pattern']:
                regex = QRegularExpression(pattern)
                match = regex.match(text)
                while match.hasMatch():
                    start_pos = match.capturedStart()
                    length = match.capturedLength()
                    self.setFormat(start_pos, length, text_format)
                    match = regex.match(text, start_pos + length)

# Пример использования:
highlighting_rules = {
    'keywords': {
        'pattern': [r'\b%s\b' % w for w in [
            'and', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'exec', 'finally', 'for', 'from', 'global', 'if', 'import', 'in',
            'is', 'lambda', 'not', 'or', 'pass', 'print',
            'raise', 'return', 'try', 'while', 'yield',
            'None', 'True', 'False',
        ]],
        'color': '#C87832',  # цвет для ключевых слов
        'weight': 'bold',
    },
    'operators': {
        'pattern': [r'%s' % o for o in [
            '=', '==', '!=', '<', '<=', '>', '>=',  # Comparison
            r'\+', '-', r'\*', '/', '//', r'\%', r'\*\*',  # Arithmetic
            r'\+=', '-=', r'\*=', '/=', r'\%=',  # In-place
            r'\^', r'\|', r'\&', r'\~', r'>>', r'<<',  # Bitwise
        ]],
        'color': '#969696',  # цвет для операторов
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
        'color': '#146E64',  # цвет для строк
    },
    'multiline': {  # Добавляем новое правило для многострочных строк
        'pattern': [
            r"'''.*?'''",  # Тройные одинарные кавычки
            r'""".*?"""',   # Тройные двойные кавычки
        ],
        'color': '#1E786E',
    },
    'self': {
        'pattern': [r'\bself\b'],
        'color': '#96558C',  # цвет для self
        'weight': 'italic',
    },
    'defclass': {
        'pattern': [
            r'\bdef\b\s*(\w+)',  # Function definition
            r'\bclass\b\s*(\w+)',  # Class definition
        ],
        'bg': 'transparent',
        'color': '#DCDCFF',  # цвет для определения функции/класса
        'weight': 'bold',
    },
    'comments': {
        'pattern': [r'#[^\n]*'],  # Comments
        'bg': 'transparent',
        'color': '#808080',  # цвет для комментариев
    },
    'numbers': {
        'pattern': [
            r'\b[+-]?[0-9]+[lL]?\b',  # Integer literals
            r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b',  # Hexadecimal literals
            r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b',  # Float literals
        ],
        'bg': 'transparent',
        'color': '#6496BE',  # цвет для чисел
    },
}

app = QApplication([])

# Пример создания QTextEdit с подсветкой синтаксиса
text_edit = QTextEdit()
syntax_highlighter = SyntaxHighlighter(text_edit.document(), highlighting_rules)
text_edit.setPlainText("""def my_function():
    # This is a comment
    if x == 5:
        print("Hello, World!")
    else:
        return 42
""")

text_edit.show()
app.exec()
