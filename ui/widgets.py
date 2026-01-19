"""
Custom widgets for Installer Creator Pro
"""

import re
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor
from PyQt6.QtCore import Qt

class JSONHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for JSON"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
        
        # Keyword format
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#D73A49"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        
        keywords = ["true", "false", "null"]
        for word in keywords:
            pattern = r'\b' + word + r'\b'
            self.highlighting_rules.append((pattern, keyword_format))
        
        # String format
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#032F62"))
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', string_format))
        
        # Number format
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#005CC5"))
        self.highlighting_rules.append((r'\b[0-9]+\b', number_format))
        
        # Property name format
        property_format = QTextCharFormat()
        property_format.setForeground(QColor("#24292E"))
        property_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"\s*:', property_format))
        
    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            expression = re.compile(pattern)
            for match in expression.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)

class FileScannerThread:
    """Thread-like file scanner (simplified version)"""
    def __init__(self, directory: str, patterns: list):
        self.directory = directory
        self.patterns = patterns
        self.files = []
    
    def scan(self):
        """Scan directory for files"""
        import os
        self.files = []
        
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                for pattern in self.patterns:
                    if file.endswith(tuple(pattern.split(';'))):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, self.directory)
                        file_info = {
                            'path': full_path,
                            'relative': rel_path,
                            'size': os.path.getsize(full_path),
                            'modified': os.path.getmtime(full_path)
                        }
                        self.files.append(file_info)
        
        return self.files