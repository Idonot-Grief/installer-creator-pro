#!/usr/bin/env python3
"""
Installer Creator Pro - Launch File
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Check for required dependencies
def check_dependencies():
    """Check if required packages are installed"""
    missing = []
    
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        missing.append("PyQt6 (install with: pip install PyQt6)")
    
    try:
        import PyInstaller
    except ImportError:
        print("Warning: PyInstaller is not installed. Installer generation will not work.")
        print("Install it with: pip install pyinstaller")
    
    if missing:
        print("Missing required dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print("\nPlease install missing dependencies and try again.")
        sys.exit(1)

# Check dependencies before importing UI modules
check_dependencies()

from PyQt6.QtWidgets import QApplication, QStyleFactory
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow

def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Installer Creator Pro")
    app.setOrganizationName("InstallerCreatorPro")
    app.setStyle("Fusion")
    
    # Set dark theme
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)
    
    # Set stylesheet
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
        }
        QTreeWidget, QListWidget, QTableWidget {
            background-color: #323232;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QHeaderView::section {
            background-color: #424242;
            color: #ffffff;
            padding: 5px;
            border: 1px solid #555555;
        }
        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #323232;
        }
        QTabBar::tab {
            background-color: #424242;
            color: #ffffff;
            padding: 8px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #2b2b2b;
            border-bottom: 2px solid #4CAF50;
        }
        QGroupBox {
            border: 2px solid #555555;
            border-radius: 5px;
            margin-top: 10px;
            color: #ffffff;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QLineEdit, QTextEdit, QComboBox {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 3px;
        }
        QPushButton {
            background-color: #424242;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 5px 15px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #4a4a4a;
        }
        QPushButton:pressed {
            background-color: #3a3a3a;
        }
        QProgressBar {
            border: 1px solid #555555;
            border-radius: 3px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #4CAF50;
            border-radius: 2px;
        }
    """)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()