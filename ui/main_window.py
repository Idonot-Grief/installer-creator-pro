"""
Main application window for Installer Creator Pro
"""

import os
import sys
import shutil
import subprocess
from typing import List
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QTableWidget,
    QTableWidgetItem, QListWidget, QListWidgetItem, QTextEdit,
    QLineEdit, QPushButton, QLabel, QFileDialog, QMessageBox,
    QGroupBox, QFormLayout, QCheckBox, QRadioButton, QButtonGroup,
    QComboBox, QProgressBar, QStatusBar, QMenuBar, QToolBar,
    QMenu, QInputDialog, QHeaderView, QAbstractItemView,
    QDialog, QDialogButtonBox, QScrollArea, QTextBrowser,
    QTextEdit, QPlainTextEdit, QSpinBox, QFrame, QToolButton,
    QGridLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QIcon, QFont, QTextCursor, QAction, QDesktopServices

from core.models import ProjectConfig, FileEntry, ScriptElement
from core.project_manager import ProjectManager
from core.generator import InstallerGeneratorThread
from ui.dialogs import (
    ScriptElementDialog, ShortcutDialog, RegistryDialog,
    DependencyDialog, AboutDialog
)
from utils.helpers import format_size, is_binary_file, validate_project

class FileScannerThread(QThread):
    """Thread for scanning files"""
    progress = pyqtSignal(int, str)
    file_found = pyqtSignal(dict)
    finished = pyqtSignal(list)
    
    def __init__(self, directory: str, patterns: List[str], recursive: bool = True):
        super().__init__()
        self.directory = directory
        self.patterns = patterns
        self.recursive = recursive
        self.files = []
    
    def run(self):
        try:
            total_files = 0
            if self.recursive:
                # Count total files first for progress
                for root, dirs, files in os.walk(self.directory):
                    total_files += len(files)
                
                processed = 0
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
                                self.file_found.emit(file_info)
                                self.files.append(file_info)
                        
                        processed += 1
                        if processed % 10 == 0:
                            progress = int((processed / total_files) * 100)
                            self.progress.emit(progress, f"Scanning... {processed}/{total_files}")
            else:
                items = os.listdir(self.directory)
                total_files = len(items)
                for i, item in enumerate(items):
                    full_path = os.path.join(self.directory, item)
                    if os.path.isfile(full_path):
                        for pattern in self.patterns:
                            if item.endswith(tuple(pattern.split(';'))):
                                file_info = {
                                    'path': full_path,
                                    'relative': item,
                                    'size': os.path.getsize(full_path),
                                    'modified': os.path.getmtime(full_path)
                                }
                                self.file_found.emit(file_info)
                                self.files.append(file_info)
                    
                    progress = int((i / total_files) * 100)
                    self.progress.emit(progress, f"Scanning... {i}/{total_files}")
            
            self.finished.emit(self.files)
            
        except Exception as e:
            self.progress.emit(0, f"Error scanning: {str(e)}")

class FileSelectionDialog(QDialog):
    """Dialog for selecting files from scan results"""
    def __init__(self, files: List[dict], parent=None):
        super().__init__(parent)
        self.files = files
        self.setWindowTitle("Select Files to Add")
        self.setMinimumSize(600, 400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # File list
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        
        for file_info in self.files:
            size = format_size(file_info['size'])
            text = f"{file_info['relative']} ({size})"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, file_info)
            item.setCheckState(Qt.CheckState.Checked)
            self.file_list.addItem(item)
        
        layout.addWidget(self.file_list)
        
        # Select all/none buttons
        select_buttons = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        select_buttons.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self.select_none)
        select_buttons.addWidget(select_none_btn)
        
        select_buttons.addStretch()
        layout.addLayout(select_buttons)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def select_all(self):
        """Select all files"""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setCheckState(Qt.CheckState.Checked)
    
    def select_none(self):
        """Deselect all files"""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
    
    def get_selected_files(self) -> List[dict]:
        """Get selected files"""
        selected = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                file_info = item.data(Qt.ItemDataRole.UserRole)
                selected.append(file_info)
        return selected

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.project = ProjectConfig()
        self.current_file = None
        self.generator_thread = None
        self.scanner_thread = None
        self.recent_projects = []
        
        self.init_ui()
        self.update_title()
        self.load_recent_projects()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Installer Creator Pro")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create tool bar
        self.create_tool_bar()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Project tree
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabel("Project Structure")
        self.project_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        left_layout.addWidget(self.project_tree)
        
        # File operations buttons
        file_buttons = QHBoxLayout()
        add_file_btn = QPushButton("Add File")
        add_file_btn.clicked.connect(self.add_file)
        file_buttons.addWidget(add_file_btn)
        
        add_dir_btn = QPushButton("Add Directory")
        add_dir_btn.clicked.connect(self.add_directory)
        file_buttons.addWidget(add_dir_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self.remove_item)
        file_buttons.addWidget(remove_btn)
        
        left_layout.addLayout(file_buttons)
        splitter.addWidget(left_panel)
        
        # Right panel - Tabs
        self.right_tabs = QTabWidget()
        splitter.addWidget(self.right_tabs)
        splitter.setSizes([300, 1100])
        
        # Create tabs
        self.create_project_tab()
        self.create_files_tab()
        self.create_scripts_tab()
        self.create_shortcuts_tab()
        self.create_registry_tab()
        self.create_dependencies_tab()
        self.create_build_tab()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Log output
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setVisible(False)
        main_layout.addWidget(self.log_text)
    
    def create_menu_bar(self):
        """Create the menu bar"""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        new_action = QAction("New Project", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open Project", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction("Save Project", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save Project As", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # Recent projects submenu
        self.recent_menu = file_menu.addMenu("Recent Projects")
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menu_bar.addMenu("Edit")
        
        preferences_action = QAction("Preferences", self)
        preferences_action.triggered.connect(self.show_preferences)
        edit_menu.addAction(preferences_action)
        
        # Build menu
        build_menu = menu_bar.addMenu("Build")
        
        generate_action = QAction("Generate Installer", self)
        generate_action.setShortcut("F5")
        generate_action.triggered.connect(self.generate_installer)
        build_menu.addAction(generate_action)
        
        test_action = QAction("Test Installer", self)
        test_action.setShortcut("F6")
        test_action.triggered.connect(self.test_installer)
        build_menu.addAction(test_action)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("Tools")
        
        scan_action = QAction("Scan for Files", self)
        scan_action.triggered.connect(self.scan_for_files)
        tools_menu.addAction(scan_action)
        
        validate_action = QAction("Validate Project", self)
        validate_action.triggered.connect(self.validate_project_dialog)
        tools_menu.addAction(validate_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        
        docs_action = QAction("Documentation", self)
        docs_action.triggered.connect(self.show_documentation)
        help_menu.addAction(docs_action)
        
        examples_action = QAction("Examples", self)
        examples_action.triggered.connect(self.show_examples)
        help_menu.addAction(examples_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_tool_bar(self):
        """Create the tool bar"""
        tool_bar = QToolBar()
        tool_bar.setMovable(False)
        self.addToolBar(tool_bar)
        
        # New project
        new_action = QAction(QIcon.fromTheme("document-new"), "New", self)
        new_action.triggered.connect(self.new_project)
        tool_bar.addAction(new_action)
        
        # Open project
        open_action = QAction(QIcon.fromTheme("document-open"), "Open", self)
        open_action.triggered.connect(self.open_project)
        tool_bar.addAction(open_action)
        
        # Save project
        save_action = QAction(QIcon.fromTheme("document-save"), "Save", self)
        save_action.triggered.connect(self.save_project)
        tool_bar.addAction(save_action)
        
        tool_bar.addSeparator()
        
        # Add file
        add_file_action = QAction(QIcon.fromTheme("document-new"), "Add File", self)
        add_file_action.triggered.connect(self.add_file)
        tool_bar.addAction(add_file_action)
        
        # Add directory
        add_dir_action = QAction(QIcon.fromTheme("folder-new"), "Add Directory", self)
        add_dir_action.triggered.connect(self.add_directory)
        tool_bar.addAction(add_dir_action)
        
        tool_bar.addSeparator()
        
        # Generate installer
        generate_action = QAction(QIcon.fromTheme("system-run"), "Generate", self)
        generate_action.triggered.connect(self.generate_installer)
        tool_bar.addAction(generate_action)
        
        tool_bar.addSeparator()
        
        # Scan for files
        scan_action = QAction(QIcon.fromTheme("edit-find"), "Scan", self)
        scan_action.triggered.connect(self.scan_for_files)
        tool_bar.addAction(scan_action)
    
    def create_project_tab(self):
        """Create project configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Basic information
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout(basic_group)
        
        self.name_edit = QLineEdit(self.project.name)
        self.name_edit.textChanged.connect(self.update_project_from_ui)
        basic_layout.addRow("Project Name:", self.name_edit)
        
        self.version_edit = QLineEdit(self.project.version)
        self.version_edit.textChanged.connect(self.update_project_from_ui)
        basic_layout.addRow("Version:", self.version_edit)
        
        self.author_edit = QLineEdit(self.project.author)
        self.author_edit.textChanged.connect(self.update_project_from_ui)
        basic_layout.addRow("Author:", self.author_edit)
        
        self.company_edit = QLineEdit(self.project.company)
        self.company_edit.textChanged.connect(self.update_project_from_ui)
        basic_layout.addRow("Company:", self.company_edit)
        
        self.desc_edit = QTextEdit(self.project.description)
        self.desc_edit.textChanged.connect(self.update_project_from_ui)
        self.desc_edit.setMaximumHeight(80)
        basic_layout.addRow("Description:", self.desc_edit)
        
        content_layout.addWidget(basic_group)
        
        # Installation settings
        install_group = QGroupBox("Installation Settings")
        install_layout = QFormLayout(install_group)
        
        self.install_dir_edit = QLineEdit(self.project.default_install_dir)
        self.install_dir_edit.textChanged.connect(self.update_project_from_ui)
        install_layout.addRow("Default Install Directory:", self.install_dir_edit)
        
        self.output_dir_edit = QLineEdit(self.project.output_dir)
        self.output_dir_edit.textChanged.connect(self.update_project_from_ui)
        browse_output_btn = QPushButton("Browse...")
        browse_output_btn.clicked.connect(lambda: self.browse_directory(self.output_dir_edit))
        output_hbox = QHBoxLayout()
        output_hbox.addWidget(self.output_dir_edit)
        output_hbox.addWidget(browse_output_btn)
        install_layout.addRow("Output Directory:", output_hbox)
        
        self.icon_path_edit = QLineEdit(self.project.icon_path)
        self.icon_path_edit.textChanged.connect(self.update_project_from_ui)
        browse_icon_btn = QPushButton("Browse...")
        browse_icon_btn.clicked.connect(lambda: self.browse_file(self.icon_path_edit, "Select Icon", "Icon files (*.ico)"))
        icon_hbox = QHBoxLayout()
        icon_hbox.addWidget(self.icon_path_edit)
        icon_hbox.addWidget(browse_icon_btn)
        install_layout.addRow("Installer Icon:", icon_hbox)
        
        self.admin_check = QCheckBox("Require Administrator Privileges")
        self.admin_check.setChecked(self.project.require_admin)
        self.admin_check.stateChanged.connect(self.update_project_from_ui)
        install_layout.addRow("", self.admin_check)
        
        self.uninstaller_check = QCheckBox("Create Uninstaller")
        self.uninstaller_check.setChecked(self.project.create_uninstaller)
        self.uninstaller_check.stateChanged.connect(self.update_project_from_ui)
        install_layout.addRow("", self.uninstaller_check)
        
        self.silent_check = QCheckBox("Enable Silent Installation")
        self.silent_check.setChecked(self.project.silent_mode)
        self.silent_check.stateChanged.connect(self.update_project_from_ui)
        install_layout.addRow("", self.silent_check)
        
        content_layout.addWidget(install_group)
        
        # License settings
        license_group = QGroupBox("License Agreement")
        license_layout = QFormLayout(license_group)
        
        self.license_check = QCheckBox("Show License Agreement")
        self.license_check.setChecked(self.project.license_enabled)
        self.license_check.stateChanged.connect(self.update_project_from_ui)
        license_layout.addRow("", self.license_check)
        
        self.license_file_edit = QLineEdit(self.project.license_file)
        self.license_file_edit.textChanged.connect(self.update_project_from_ui)
        browse_license_btn = QPushButton("Browse...")
        browse_license_btn.clicked.connect(lambda: self.browse_file(self.license_file_edit, "Select License File", "Text files (*.txt *.md)"))
        license_file_hbox = QHBoxLayout()
        license_file_hbox.addWidget(self.license_file_edit)
        license_file_hbox.addWidget(browse_license_btn)
        license_layout.addRow("License File:", license_file_hbox)
        
        self.license_text_edit = QTextEdit(self.project.license_text)
        self.license_text_edit.textChanged.connect(self.update_project_from_ui)
        self.license_text_edit.setMaximumHeight(150)
        license_layout.addRow("License Text:", self.license_text_edit)
        
        content_layout.addWidget(license_group)
        
        # UI customization
        ui_group = QGroupBox("UI Customization")
        ui_layout = QFormLayout(ui_group)
        
        self.ui_style_combo = QComboBox()
        self.ui_style_combo.addItems(["default", "dark", "light", "custom"])
        self.ui_style_combo.setCurrentText(self.project.installer_style)
        self.ui_style_combo.currentTextChanged.connect(self.update_project_from_ui)
        ui_layout.addRow("Installer Style:", self.ui_style_combo)
        
        self.installer_title_edit = QLineEdit(self.project.installer_title)
        self.installer_title_edit.textChanged.connect(self.update_project_from_ui)
        ui_layout.addRow("Installer Title:", self.installer_title_edit)
        
        self.custom_css_edit = QTextEdit(self.project.custom_css)
        self.custom_css_edit.textChanged.connect(self.update_project_from_ui)
        self.custom_css_edit.setPlaceholderText("Custom CSS styles for the installer UI")
        self.custom_css_edit.setMaximumHeight(100)
        ui_layout.addRow("Custom CSS:", self.custom_css_edit)
        
        content_layout.addWidget(ui_group)
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        self.right_tabs.addTab(tab, "Project")
    
    def create_files_tab(self):
        """Create files management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # File list with search
        search_hbox = QHBoxLayout()
        search_label = QLabel("Search:")
        self.file_search_edit = QLineEdit()
        self.file_search_edit.setPlaceholderText("Search files...")
        self.file_search_edit.textChanged.connect(self.filter_files_list)
        search_hbox.addWidget(search_label)
        search_hbox.addWidget(self.file_search_edit)
        layout.addLayout(search_hbox)
        
        # File table
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(["Source Path", "Install Path", "Type", "Compress", "Size"])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.files_table)
        
        # File operations buttons
        file_buttons = QHBoxLayout()
        
        add_file_btn = QPushButton("Add File")
        add_file_btn.clicked.connect(self.add_file)
        file_buttons.addWidget(add_file_btn)
        
        add_dir_btn = QPushButton("Add Directory")
        add_dir_btn.clicked.connect(self.add_directory)
        file_buttons.addWidget(add_dir_btn)
        
        remove_file_btn = QPushButton("Remove Selected")
        remove_file_btn.clicked.connect(self.remove_selected_files)
        file_buttons.addWidget(remove_file_btn)
        
        scan_files_btn = QPushButton("Scan Directory")
        scan_files_btn.clicked.connect(self.scan_for_files)
        file_buttons.addWidget(scan_files_btn)
        
        file_buttons.addStretch()
        layout.addLayout(file_buttons)
        
        self.right_tabs.addTab(tab, "Files")
    
    def create_scripts_tab(self):
        """Create scripts tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Script elements list
        self.scripts_list = QListWidget()
        layout.addWidget(self.scripts_list)
        
        # Script operations buttons
        script_buttons = QHBoxLayout()
        
        add_script_btn = QPushButton("Add Script Element")
        add_script_btn.clicked.connect(self.add_script_element)
        script_buttons.addWidget(add_script_btn)
        
        edit_script_btn = QPushButton("Edit Selected")
        edit_script_btn.clicked.connect(self.edit_script_element)
        script_buttons.addWidget(edit_script_btn)
        
        remove_script_btn = QPushButton("Remove Selected")
        remove_script_btn.clicked.connect(self.remove_selected_scripts)
        script_buttons.addWidget(remove_script_btn)
        
        move_up_btn = QPushButton("Move Up")
        move_up_btn.clicked.connect(self.move_script_up)
        script_buttons.addWidget(move_up_btn)
        
        move_down_btn = QPushButton("Move Down")
        move_down_btn.clicked.connect(self.move_script_down)
        script_buttons.addWidget(move_down_btn)
        
        script_buttons.addStretch()
        layout.addLayout(script_buttons)
        
        self.right_tabs.addTab(tab, "Scripts")
    
    def create_shortcuts_tab(self):
        """Create shortcuts tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Shortcuts table
        self.shortcuts_table = QTableWidget()
        self.shortcuts_table.setColumnCount(6)
        self.shortcuts_table.setHorizontalHeaderLabels(["Name", "Target", "Location", "Working Dir", "Arguments", "Description"])
        self.shortcuts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.shortcuts_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.shortcuts_table)
        
        # Shortcut operations buttons
        shortcut_buttons = QHBoxLayout()
        
        add_shortcut_btn = QPushButton("Add Shortcut")
        add_shortcut_btn.clicked.connect(self.add_shortcut)
        shortcut_buttons.addWidget(add_shortcut_btn)
        
        edit_shortcut_btn = QPushButton("Edit Selected")
        edit_shortcut_btn.clicked.connect(self.edit_shortcut)
        shortcut_buttons.addWidget(edit_shortcut_btn)
        
        remove_shortcut_btn = QPushButton("Remove Selected")
        remove_shortcut_btn.clicked.connect(self.remove_selected_shortcuts)
        shortcut_buttons.addWidget(remove_shortcut_btn)
        
        shortcut_buttons.addStretch()
        layout.addLayout(shortcut_buttons)
        
        self.right_tabs.addTab(tab, "Shortcuts")
    
    def create_registry_tab(self):
        """Create registry settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Registry table
        self.registry_table = QTableWidget()
        self.registry_table.setColumnCount(6)
        self.registry_table.setHorizontalHeaderLabels(["Hive", "Key", "Value Name", "Type", "Value", "Action"])
        self.registry_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.registry_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.registry_table)
        
        # Registry operations buttons
        registry_buttons = QHBoxLayout()
        
        add_registry_btn = QPushButton("Add Registry Entry")
        add_registry_btn.clicked.connect(self.add_registry_entry)
        registry_buttons.addWidget(add_registry_btn)
        
        edit_registry_btn = QPushButton("Edit Selected")
        edit_registry_btn.clicked.connect(self.edit_registry_entry)
        registry_buttons.addWidget(edit_registry_btn)
        
        remove_registry_btn = QPushButton("Remove Selected")
        remove_registry_btn.clicked.connect(self.remove_selected_registry)
        registry_buttons.addWidget(remove_registry_btn)
        
        registry_buttons.addStretch()
        layout.addLayout(registry_buttons)
        
        self.right_tabs.addTab(tab, "Registry")
    
    def create_dependencies_tab(self):
        """Create dependencies tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Dependencies table
        self.dependencies_table = QTableWidget()
        self.dependencies_table.setColumnCount(5)
        self.dependencies_table.setHorizontalHeaderLabels(["Name", "Version", "Installer Path", "Check Command", "Required"])
        self.dependencies_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.dependencies_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.dependencies_table)
        
        # Dependency operations buttons
        dep_buttons = QHBoxLayout()
        
        add_dep_btn = QPushButton("Add Dependency")
        add_dep_btn.clicked.connect(self.add_dependency)
        dep_buttons.addWidget(add_dep_btn)
        
        edit_dep_btn = QPushButton("Edit Selected")
        edit_dep_btn.clicked.connect(self.edit_dependency)
        dep_buttons.addWidget(edit_dep_btn)
        
        remove_dep_btn = QPushButton("Remove Selected")
        remove_dep_btn.clicked.connect(self.remove_selected_dependencies)
        dep_buttons.addWidget(remove_dep_btn)
        
        dep_buttons.addStretch()
        layout.addLayout(dep_buttons)
        
        self.right_tabs.addTab(tab, "Dependencies")
    
    def create_build_tab(self):
        """Create build settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # PyInstaller settings
        pyinstaller_group = QGroupBox("PyInstaller Settings")
        pyinstaller_layout = QFormLayout(pyinstaller_group)
        
        self.onefile_radio = QRadioButton("One File (Single Executable)")
        self.onefile_radio.setChecked(self.project.onefile)
        self.onefile_radio.toggled.connect(self.update_project_from_ui)
        
        self.onedir_radio = QRadioButton("One Directory")
        self.onedir_radio.setChecked(not self.project.onefile)
        self.onedir_radio.toggled.connect(self.update_project_from_ui)
        
        mode_group = QButtonGroup()
        mode_group.addButton(self.onefile_radio)
        mode_group.addButton(self.onedir_radio)
        
        mode_hbox = QHBoxLayout()
        mode_hbox.addWidget(self.onefile_radio)
        mode_hbox.addWidget(self.onedir_radio)
        pyinstaller_layout.addRow("Output Mode:", mode_hbox)
        
        self.console_check = QCheckBox("Console Application")
        self.console_check.setChecked(self.project.console)
        self.console_check.stateChanged.connect(self.update_project_from_ui)
        pyinstaller_layout.addRow("", self.console_check)
        
        self.compression_combo = QComboBox()
        self.compression_combo.addItems(["upx", "lzma2", "none"])
        self.compression_combo.setCurrentText(self.project.compression)
        self.compression_combo.currentTextChanged.connect(self.update_project_from_ui)
        pyinstaller_layout.addRow("Compression:", self.compression_combo)
        
        layout.addWidget(pyinstaller_group)
        
        # Code signing
        signing_group = QGroupBox("Code Signing")
        signing_layout = QFormLayout(signing_group)
        
        self.sign_check = QCheckBox("Sign Installer")
        self.sign_check.setChecked(self.project.sign_installer)
        self.sign_check.stateChanged.connect(self.update_project_from_ui)
        signing_layout.addRow("", self.sign_check)
        
        self.cert_path_edit = QLineEdit(self.project.certificate_path)
        self.cert_path_edit.textChanged.connect(self.update_project_from_ui)
        browse_cert_btn = QPushButton("Browse...")
        browse_cert_btn.clicked.connect(lambda: self.browse_file(self.cert_path_edit, "Select Certificate", "Certificate files (*.pfx *.p12)"))
        cert_hbox = QHBoxLayout()
        cert_hbox.addWidget(self.cert_path_edit)
        cert_hbox.addWidget(browse_cert_btn)
        signing_layout.addRow("Certificate:", cert_hbox)
        
        self.cert_pass_edit = QLineEdit(self.project.certificate_password)
        self.cert_pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.cert_pass_edit.textChanged.connect(self.update_project_from_ui)
        signing_layout.addRow("Password:", self.cert_pass_edit)
        
        self.timestamp_edit = QLineEdit(self.project.timestamp_server)
        self.timestamp_edit.textChanged.connect(self.update_project_from_ui)
        signing_layout.addRow("Timestamp Server:", self.timestamp_edit)
        
        layout.addWidget(signing_group)
        
        # Advanced settings
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QFormLayout(advanced_group)
        
        self.hidden_imports_edit = QTextEdit()
        self.hidden_imports_edit.setPlainText("\n".join(self.project.hidden_imports))
        self.hidden_imports_edit.textChanged.connect(self.update_project_from_ui)
        self.hidden_imports_edit.setMaximumHeight(80)
        advanced_layout.addRow("Hidden Imports:", self.hidden_imports_edit)
        
        self.exclude_modules_edit = QTextEdit()
        self.exclude_modules_edit.setPlainText("\n".join(self.project.exclude_modules))
        self.exclude_modules_edit.textChanged.connect(self.update_project_from_ui)
        self.exclude_modules_edit.setMaximumHeight(80)
        advanced_layout.addRow("Exclude Modules:", self.exclude_modules_edit)
        
        layout.addWidget(advanced_group)
        
        # Generate button
        self.generate_btn = QPushButton("Generate Installer")
        self.generate_btn.clicked.connect(self.generate_installer)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.generate_btn)
        
        layout.addStretch()
        
        self.right_tabs.addTab(tab, "Build")
    
    # Update methods
    def update_project_from_ui(self):
        """Update project configuration from UI"""
        # Basic information
        self.project.name = self.name_edit.text()
        self.project.version = self.version_edit.text()
        self.project.author = self.author_edit.text()
        self.project.company = self.company_edit.text()
        self.project.description = self.desc_edit.toPlainText()
        
        # Installation settings
        self.project.default_install_dir = self.install_dir_edit.text()
        self.project.output_dir = self.output_dir_edit.text()
        self.project.icon_path = self.icon_path_edit.text()
        self.project.require_admin = self.admin_check.isChecked()
        self.project.create_uninstaller = self.uninstaller_check.isChecked()
        self.project.silent_mode = self.silent_check.isChecked()
        
        # License settings
        self.project.license_enabled = self.license_check.isChecked()
        self.project.license_file = self.license_file_edit.text()
        self.project.license_text = self.license_text_edit.toPlainText()
        
        # UI customization
        self.project.installer_style = self.ui_style_combo.currentText()
        self.project.installer_title = self.installer_title_edit.text()
        self.project.custom_css = self.custom_css_edit.toPlainText()
        
        # PyInstaller settings
        self.project.onefile = self.onefile_radio.isChecked()
        self.project.console = self.console_check.isChecked()
        self.project.compression = self.compression_combo.currentText()
        
        # Code signing
        self.project.sign_installer = self.sign_check.isChecked()
        self.project.certificate_path = self.cert_path_edit.text()
        self.project.certificate_password = self.cert_pass_edit.text()
        self.project.timestamp_server = self.timestamp_edit.text()
        
        # Advanced settings
        hidden_text = self.hidden_imports_edit.toPlainText().strip()
        self.project.hidden_imports = [i.strip() for i in hidden_text.split('\n') if i.strip()]
        
        exclude_text = self.exclude_modules_edit.toPlainText().strip()
        self.project.exclude_modules = [i.strip() for i in exclude_text.split('\n') if i.strip()]
        
        self.project.modified = self.project.modified
        self.update_title()
    
    def update_title(self):
        """Update window title"""
        modified = "*" if self.project.modified > self.project.created else ""
        filename = os.path.basename(self.current_file) if self.current_file else "Untitled"
        self.setWindowTitle(f"Installer Creator Pro - {filename}{modified}")
    
    def update_tree_view(self):
        """Update project tree view"""
        self.project_tree.clear()
        
        # Add files
        files_item = QTreeWidgetItem(["Files"])
        for file_entry in self.project.files:
            icon = "📁" if file_entry.is_directory else "📄"
            item = QTreeWidgetItem([f"{icon} {file_entry.install_path}"])
            item.setData(0, Qt.ItemDataRole.UserRole, ("file", file_entry))
            files_item.addChild(item)
        self.project_tree.addTopLevelItem(files_item)
        
        # Add scripts
        scripts_item = QTreeWidgetItem(["Scripts"])
        for script in self.project.script_elements:
            icon = "⚙️" if script.enabled else "⚙️❌"
            item = QTreeWidgetItem([f"{icon} {script.name}"])
            item.setData(0, Qt.ItemDataRole.UserRole, ("script", script))
            scripts_item.addChild(item)
        self.project_tree.addTopLevelItem(scripts_item)
        
        # Add shortcuts
        shortcuts_item = QTreeWidgetItem(["Shortcuts"])
        for shortcut in self.project.shortcuts:
            item = QTreeWidgetItem([f"🔗 {shortcut.name}"])
            item.setData(0, Qt.ItemDataRole.UserRole, ("shortcut", shortcut))
            shortcuts_item.addChild(item)
        self.project_tree.addTopLevelItem(shortcuts_item)
        
        # Add registry entries
        registry_item = QTreeWidgetItem(["Registry"])
        for reg_entry in self.project.registry_entries:
            item = QTreeWidgetItem([f"🔧 {reg_entry.key}\\{reg_entry.value_name}"])
            item.setData(0, Qt.ItemDataRole.UserRole, ("registry", reg_entry))
            registry_item.addChild(item)
        self.project_tree.addTopLevelItem(registry_item)
        
        # Add dependencies
        dependencies_item = QTreeWidgetItem(["Dependencies"])
        for dep in self.project.dependencies:
            icon = "📦" if dep.required else "📦❓"
            item = QTreeWidgetItem([f"{icon} {dep.name}"])
            item.setData(0, Qt.ItemDataRole.UserRole, ("dependency", dep))
            dependencies_item.addChild(item)
        self.project_tree.addTopLevelItem(dependencies_item)
        
        self.project_tree.expandAll()
    
    def update_files_table(self):
        """Update files table"""
        self.files_table.setRowCount(len(self.project.files))
        
        for i, file_entry in enumerate(self.project.files):
            # Source path
            src_item = QTableWidgetItem(file_entry.source_path)
            src_item.setData(Qt.ItemDataRole.UserRole, file_entry)
            self.files_table.setItem(i, 0, src_item)
            
            # Install path
            install_item = QTableWidgetItem(file_entry.install_path)
            self.files_table.setItem(i, 1, install_item)
            
            # Type
            type_text = "Directory" if file_entry.is_directory else "File"
            type_item = QTableWidgetItem(type_text)
            self.files_table.setItem(i, 2, type_item)
            
            # Compress
            compress_item = QTableWidgetItem("Yes" if file_entry.compress else "No")
            self.files_table.setItem(i, 3, compress_item)
            
            # Size
            if not file_entry.is_directory and os.path.exists(file_entry.source_path):
                size = os.path.getsize(file_entry.source_path)
                size_text = format_size(size)
            else:
                size_text = "-"
            size_item = QTableWidgetItem(size_text)
            self.files_table.setItem(i, 4, size_item)
    
    def update_scripts_list(self):
        """Update scripts list"""
        self.scripts_list.clear()
        for script in self.project.script_elements:
            icon = "✓ " if script.enabled else "✗ "
            item_text = f"{icon}{script.name} ({script.type.value})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, script)
            self.scripts_list.addItem(item)
    
    def update_shortcuts_table(self):
        """Update shortcuts table"""
        self.shortcuts_table.setRowCount(len(self.project.shortcuts))
        
        for i, shortcut in enumerate(self.project.shortcuts):
            # Name
            name_item = QTableWidgetItem(shortcut.name)
            name_item.setData(Qt.ItemDataRole.UserRole, shortcut)
            self.shortcuts_table.setItem(i, 0, name_item)
            
            # Target
            self.shortcuts_table.setItem(i, 1, QTableWidgetItem(shortcut.target))
            
            # Location
            location_map = {
                "desktop": "Desktop",
                "start_menu": "Start Menu",
                "both": "Both"
            }
            location_text = location_map.get(shortcut.location, shortcut.location)
            self.shortcuts_table.setItem(i, 2, QTableWidgetItem(location_text))
            
            # Working directory
            self.shortcuts_table.setItem(i, 3, QTableWidgetItem(shortcut.working_dir))
            
            # Arguments
            self.shortcuts_table.setItem(i, 4, QTableWidgetItem(shortcut.arguments))
            
            # Description
            self.shortcuts_table.setItem(i, 5, QTableWidgetItem(shortcut.description))
    
    def update_registry_table(self):
        """Update registry table"""
        self.registry_table.setRowCount(len(self.project.registry_entries))
        
        for i, reg_entry in enumerate(self.project.registry_entries):
            # Hive
            self.registry_table.setItem(i, 0, QTableWidgetItem(reg_entry.hive))
            
            # Key
            key_item = QTableWidgetItem(reg_entry.key)
            key_item.setData(Qt.ItemDataRole.UserRole, reg_entry)
            self.registry_table.setItem(i, 1, key_item)
            
            # Value name
            self.registry_table.setItem(i, 2, QTableWidgetItem(reg_entry.value_name))
            
            # Type
            self.registry_table.setItem(i, 3, QTableWidgetItem(reg_entry.value_type))
            
            # Value
            value_text = str(reg_entry.value_data)
            if len(value_text) > 50:
                value_text = value_text[:47] + "..."
            self.registry_table.setItem(i, 4, QTableWidgetItem(value_text))
            
            # Action
            self.registry_table.setItem(i, 5, QTableWidgetItem(reg_entry.action.capitalize()))
    
    def update_dependencies_table(self):
        """Update dependencies table"""
        self.dependencies_table.setRowCount(len(self.project.dependencies))
        
        for i, dep in enumerate(self.project.dependencies):
            # Name
            name_item = QTableWidgetItem(dep.name)
            name_item.setData(Qt.ItemDataRole.UserRole, dep)
            self.dependencies_table.setItem(i, 0, name_item)
            
            # Version
            self.dependencies_table.setItem(i, 1, QTableWidgetItem(dep.version))
            
            # Installer path
            self.dependencies_table.setItem(i, 2, QTableWidgetItem(dep.installer_path))
            
            # Check command
            self.dependencies_table.setItem(i, 3, QTableWidgetItem(dep.check_command))
            
            # Required
            required_item = QTableWidgetItem("Yes" if dep.required else "No")
            self.dependencies_table.setItem(i, 4, required_item)
    
    # File operations
    def add_file(self):
        """Add file to project"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Files to Add", "", "All Files (*)"
        )
        
        for file_path in file_paths:
            if os.path.exists(file_path):
                # Ask for install path
                install_path, ok = QInputDialog.getText(
                    self, "Install Path",
                    f"Enter install path for {os.path.basename(file_path)}:",
                    text=os.path.basename(file_path)
                )
                
                if ok and install_path:
                    file_entry = FileEntry(
                        source_path=file_path,
                        install_path=install_path,
                        is_binary=is_binary_file(file_path)
                    )
                    self.project.files.append(file_entry)
        
        self.update_tree_view()
        self.update_files_table()
    
    def add_directory(self):
        """Add directory to project"""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory to Add")
        
        if dir_path and os.path.exists(dir_path):
            # Ask for install path
            install_path, ok = QInputDialog.getText(
                self, "Install Path",
                f"Enter install path for {os.path.basename(dir_path)}:",
                text=os.path.basename(dir_path)
            )
            
            if ok and install_path:
                # Add directory entry
                dir_entry = FileEntry(
                    source_path=dir_path,
                    install_path=install_path,
                    is_directory=True
                )
                self.project.files.append(dir_entry)
                
                # Optionally add all files in directory
                reply = QMessageBox.question(
                    self, "Add Files",
                    "Add all files in this directory recursively?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    for root, dirs, files in os.walk(dir_path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, dir_path)
                            file_install_path = os.path.join(install_path, rel_path)
                            
                            file_entry = FileEntry(
                                source_path=full_path,
                                install_path=file_install_path,
                                is_binary=is_binary_file(full_path)
                            )
                            self.project.files.append(file_entry)
        
        self.update_tree_view()
        self.update_files_table()
    
    def remove_selected_files(self):
        """Remove selected files from table"""
        selected_rows = set()
        for item in self.files_table.selectedItems():
            selected_rows.add(item.row())
        
        # Remove in reverse order
        for row in sorted(selected_rows, reverse=True):
            if row < len(self.project.files):
                self.project.files.pop(row)
        
        self.update_tree_view()
        self.update_files_table()
    
    def filter_files_list(self):
        """Filter files list based on search text"""
        search_text = self.file_search_edit.text().lower()
        
        for row in range(self.files_table.rowCount()):
            show = False
            for col in range(self.files_table.columnCount()):
                item = self.files_table.item(row, col)
                if item and search_text in item.text().lower():
                    show = True
                    break
            self.files_table.setRowHidden(row, not show)
    
    # Script operations
    def add_script_element(self):
        """Add new script element"""
        dialog = ScriptElementDialog()
        if dialog.exec():
            try:
                element = dialog.get_element()
                self.project.script_elements.append(element)
                self.update_tree_view()
                self.update_scripts_list()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to add script: {str(e)}")
    
    def edit_script_element(self):
        """Edit selected script element"""
        selected_items = self.scripts_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a script element to edit")
            return
        
        item = selected_items[0]
        script = item.data(Qt.ItemDataRole.UserRole)
        
        dialog = ScriptElementDialog(script)
        if dialog.exec():
            try:
                new_script = dialog.get_element()
                # Update the script in the list
                index = self.project.script_elements.index(script)
                self.project.script_elements[index] = new_script
                self.update_tree_view()
                self.update_scripts_list()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to edit script: {str(e)}")
    
    def remove_selected_scripts(self):
        """Remove selected scripts"""
        selected_items = self.scripts_list.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            script = item.data(Qt.ItemDataRole.UserRole)
            if script in self.project.script_elements:
                self.project.script_elements.remove(script)
        
        self.update_tree_view()
        self.update_scripts_list()
    
    def move_script_up(self):
        """Move selected script up in list"""
        selected_items = self.scripts_list.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        script = item.data(Qt.ItemDataRole.UserRole)
        index = self.project.script_elements.index(script)
        
        if index > 0:
            self.project.script_elements[index], self.project.script_elements[index-1] = \
                self.project.script_elements[index-1], self.project.script_elements[index]
            self.update_scripts_list()
            self.scripts_list.setCurrentRow(index-1)
    
    def move_script_down(self):
        """Move selected script down in list"""
        selected_items = self.scripts_list.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        script = item.data(Qt.ItemDataRole.UserRole)
        index = self.project.script_elements.index(script)
        
        if index < len(self.project.script_elements) - 1:
            self.project.script_elements[index], self.project.script_elements[index+1] = \
                self.project.script_elements[index+1], self.project.script_elements[index]
            self.update_scripts_list()
            self.scripts_list.setCurrentRow(index+1)
    
    # Shortcut operations
    def add_shortcut(self):
        """Add new shortcut"""
        dialog = ShortcutDialog()
        if dialog.exec():
            shortcut = dialog.get_shortcut()
            self.project.shortcuts.append(shortcut)
            self.update_tree_view()
            self.update_shortcuts_table()
    
    def edit_shortcut(self):
        """Edit selected shortcut"""
        selected_items = self.shortcuts_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a shortcut to edit")
            return
        
        row = selected_items[0].row()
        shortcut = self.shortcuts_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        dialog = ShortcutDialog(shortcut)
        if dialog.exec():
            new_shortcut = dialog.get_shortcut()
            # Update the shortcut in the list
            index = self.project.shortcuts.index(shortcut)
            self.project.shortcuts[index] = new_shortcut
            self.update_tree_view()
            self.update_shortcuts_table()
    
    def remove_selected_shortcuts(self):
        """Remove selected shortcuts"""
        selected_rows = set()
        for item in self.shortcuts_table.selectedItems():
            selected_rows.add(item.row())
        
        # Remove in reverse order
        for row in sorted(selected_rows, reverse=True):
            if row < len(self.project.shortcuts):
                self.project.shortcuts.pop(row)
        
        self.update_tree_view()
        self.update_shortcuts_table()
    
    # Registry operations
    def add_registry_entry(self):
        """Add new registry entry"""
        dialog = RegistryDialog()
        if dialog.exec():
            reg_entry = dialog.get_registry_entry()
            self.project.registry_entries.append(reg_entry)
            self.update_tree_view()
            self.update_registry_table()
    
    def edit_registry_entry(self):
        """Edit selected registry entry"""
        selected_items = self.registry_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a registry entry to edit")
            return
        
        row = selected_items[0].row()
        reg_entry = self.registry_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        
        dialog = RegistryDialog(reg_entry)
        if dialog.exec():
            new_reg_entry = dialog.get_registry_entry()
            # Update the registry entry in the list
            index = self.project.registry_entries.index(reg_entry)
            self.project.registry_entries[index] = new_reg_entry
            self.update_tree_view()
            self.update_registry_table()
    
    def remove_selected_registry(self):
        """Remove selected registry entries"""
        selected_rows = set()
        for item in self.registry_table.selectedItems():
            selected_rows.add(item.row())
        
        # Remove in reverse order
        for row in sorted(selected_rows, reverse=True):
            if row < len(self.project.registry_entries):
                self.project.registry_entries.pop(row)
        
        self.update_tree_view()
        self.update_registry_table()
    
    # Dependency operations
    def add_dependency(self):
        """Add new dependency"""
        dialog = DependencyDialog()
        if dialog.exec():
            dep = dialog.get_dependency()
            self.project.dependencies.append(dep)
            self.update_tree_view()
            self.update_dependencies_table()
    
    def edit_dependency(self):
        """Edit selected dependency"""
        selected_items = self.dependencies_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a dependency to edit")
            return
        
        row = selected_items[0].row()
        dep = self.dependencies_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        dialog = DependencyDialog(dep)
        if dialog.exec():
            new_dep = dialog.get_dependency()
            # Update the dependency in the list
            index = self.project.dependencies.index(dep)
            self.project.dependencies[index] = new_dep
            self.update_tree_view()
            self.update_dependencies_table()
    
    def remove_selected_dependencies(self):
        """Remove selected dependencies"""
        selected_rows = set()
        for item in self.dependencies_table.selectedItems():
            selected_rows.add(item.row())
        
        # Remove in reverse order
        for row in sorted(selected_rows, reverse=True):
            if row < len(self.project.dependencies):
                self.project.dependencies.pop(row)
        
        self.update_tree_view()
        self.update_dependencies_table()
    
    # Project operations
    def new_project(self):
        """Create new project"""
        if self.check_unsaved_changes():
            self.project = ProjectConfig()
            self.current_file = None
            self.update_ui_from_project()
            self.update_title()
    
    def open_project(self):
        """Open existing project"""
        if self.check_unsaved_changes():
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Open Project", "", "Installer Project Files (*.icproj)"
            )
            
            if file_path:
                try:
                    self.project = ProjectManager.load_project(file_path)
                    self.current_file = file_path
                    self.update_ui_from_project()
                    self.add_to_recent_projects(file_path)
                    self.status_bar.showMessage(f"Project loaded: {file_path}", 3000)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load project:\n{str(e)}")
    
    def save_project(self):
        """Save project"""
        if self.current_file:
            try:
                ProjectManager.save_project(self.current_file, self.project)
                self.status_bar.showMessage(f"Project saved: {self.current_file}", 3000)
                self.update_title()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project:\n{str(e)}")
        else:
            self.save_project_as()
    
    def save_project_as(self):
        """Save project as new file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "Installer Project Files (*.icproj)"
        )
        
        if file_path:
            if not file_path.endswith('.icproj'):
                file_path += '.icproj'
            
            try:
                ProjectManager.save_project(file_path, self.project)
                self.current_file = file_path
                self.add_to_recent_projects(file_path)
                self.status_bar.showMessage(f"Project saved: {file_path}", 3000)
                self.update_title()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project:\n{str(e)}")
    
    def check_unsaved_changes(self) -> bool:
        """Check for unsaved changes"""
        if self.project.modified > self.project.created:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Save them now?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.save_project()
                return True
            elif reply == QMessageBox.StandardButton.No:
                return True
            else:
                return False
        
        return True
    
    def update_ui_from_project(self):
        """Update UI from project configuration"""
        # Basic information
        self.name_edit.setText(self.project.name)
        self.version_edit.setText(self.project.version)
        self.author_edit.setText(self.project.author)
        self.company_edit.setText(self.project.company)
        self.desc_edit.setPlainText(self.project.description)
        
        # Installation settings
        self.install_dir_edit.setText(self.project.default_install_dir)
        self.output_dir_edit.setText(self.project.output_dir)
        self.icon_path_edit.setText(self.project.icon_path)
        self.admin_check.setChecked(self.project.require_admin)
        self.uninstaller_check.setChecked(self.project.create_uninstaller)
        self.silent_check.setChecked(self.project.silent_mode)
        
        # License settings
        self.license_check.setChecked(self.project.license_enabled)
        self.license_file_edit.setText(self.project.license_file)
        self.license_text_edit.setPlainText(self.project.license_text)
        
        # UI customization
        self.ui_style_combo.setCurrentText(self.project.installer_style)
        self.installer_title_edit.setText(self.project.installer_title)
        self.custom_css_edit.setPlainText(self.project.custom_css)
        
        # PyInstaller settings
        self.onefile_radio.setChecked(self.project.onefile)
        self.onedir_radio.setChecked(not self.project.onefile)
        self.console_check.setChecked(self.project.console)
        self.compression_combo.setCurrentText(self.project.compression)
        
        # Code signing
        self.sign_check.setChecked(self.project.sign_installer)
        self.cert_path_edit.setText(self.project.certificate_path)
        self.cert_pass_edit.setText(self.project.certificate_password)
        self.timestamp_edit.setText(self.project.timestamp_server)
        
        # Advanced settings
        self.hidden_imports_edit.setPlainText("\n".join(self.project.hidden_imports))
        self.exclude_modules_edit.setPlainText("\n".join(self.project.exclude_modules))
        
        # Update all views
        self.update_tree_view()
        self.update_files_table()
        self.update_scripts_list()
        self.update_shortcuts_table()
        self.update_registry_table()
        self.update_dependencies_table()
    
    # Recent projects
    def load_recent_projects(self):
        """Load recent projects"""
        self.recent_projects = ProjectManager.load_recent_projects()
        self.update_recent_menu()
    
    def update_recent_menu(self):
        """Update recent projects menu"""
        self.recent_menu.clear()
        
        for project_path in self.recent_projects:
            action = QAction(os.path.basename(project_path), self)
            action.setData(project_path)
            action.triggered.connect(lambda checked, path=project_path: self.open_recent_project(path))
            self.recent_menu.addAction(action)
    
    def open_recent_project(self, file_path):
        """Open recent project"""
        if self.check_unsaved_changes():
            try:
                self.project = ProjectManager.load_project(file_path)
                self.current_file = file_path
                self.update_ui_from_project()
                self.add_to_recent_projects(file_path)
                self.status_bar.showMessage(f"Project loaded: {file_path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load project:\n{str(e)}")
    
    def add_to_recent_projects(self, file_path):
        """Add project to recent list"""
        if file_path in self.recent_projects:
            self.recent_projects.remove(file_path)
        
        self.recent_projects.insert(0, file_path)
        self.recent_projects = self.recent_projects[:10]
        
        ProjectManager.save_recent_projects(self.recent_projects)
        self.update_recent_menu()
    
    # Installer generation
    def generate_installer(self):
        """Generate the installer"""
        self.update_project_from_ui()
        
        # Validate project
        is_valid, errors, warnings = validate_project(self.project)
        
        if not is_valid:
            error_msg = "Validation failed:\n\n" + "\n".join(errors)
            if warnings:
                error_msg += "\n\nWarnings:\n" + "\n".join(warnings)
            QMessageBox.critical(self, "Validation Failed", error_msg)
            return
        
        if warnings:
            warning_msg = "Validation warnings:\n\n" + "\n".join(warnings)
            reply = QMessageBox.question(
                self, "Validation Warnings",
                warning_msg + "\n\nContinue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        if not self.project.output_dir:
            QMessageBox.warning(self, "Warning", "Please specify output directory")
            return
        
        # Create output directory
        os.makedirs(self.project.output_dir, exist_ok=True)
        
        # Check if PyInstaller is installed
        try:
            import PyInstaller
        except ImportError:
            QMessageBox.critical(self, "Error", 
                "PyInstaller is not installed. Please install it with:\n"
                "pip install pyinstaller")
            return
        
        # Check for UPX if compression is enabled
        if self.project.compression == "upx":
            upx_path = shutil.which("upx")
            if not upx_path:
                reply = QMessageBox.question(
                    self, "UPX Not Found",
                    "UPX compression is enabled but UPX is not found in PATH.\n"
                    "Installation will continue without UPX compression.\n"
                    "Continue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
        
        # Disable generate button during build
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log_text.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Clear log
        self.log_text.clear()
        
        # Start generation in thread
        self.generator_thread = InstallerGeneratorThread(
            self.project,
            self.project.output_dir
        )
        self.generator_thread.progress.connect(self.update_progress)
        self.generator_thread.log_message.connect(self.update_log)
        self.generator_thread.finished.connect(self.generation_finished)
        self.generator_thread.start()
    
    def update_progress(self, value: int, message: str):
        """Update progress bar"""
        self.progress_bar.setValue(value)
        self.status_bar.showMessage(message)
    
    def update_log(self, message: str):
        """Update log text"""
        self.log_text.append(message)
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
        
        # Auto-scroll
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def generation_finished(self, message: str, success: bool):
        """Handle generation completion"""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        
        if success:
            self.log_text.append("=== GENERATION SUCCESSFUL ===")
            self.status_bar.showMessage("Installer generated successfully", 5000)
            
            # Offer to open output directory
            if os.path.exists(self.project.output_dir):
                reply = QMessageBox.question(
                    self, "Success",
                    f"Installer created successfully!\n\n"
                    f"Open output directory?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    if sys.platform == "win32":
                        os.startfile(self.project.output_dir)
                    elif sys.platform == "darwin":
                        subprocess.run(["open", self.project.output_dir])
                    else:
                        subprocess.run(["xdg-open", self.project.output_dir])
        else:
            self.log_text.append("=== GENERATION FAILED ===")
            self.log_text.append(f"Error: {message}")
            
            # Show error dialog
            error_dialog = QDialog(self)
            error_dialog.setWindowTitle("Generation Failed")
            error_dialog.setMinimumWidth(600)
            error_dialog.setMinimumHeight(400)
            
            layout = QVBoxLayout(error_dialog)
            
            title = QLabel("<h3>Installer Generation Failed</h3>")
            layout.addWidget(title)
            
            error_text = QTextEdit()
            error_text.setPlainText(message)
            error_text.setReadOnly(True)
            layout.addWidget(error_text)
            
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(error_dialog.reject)
            layout.addWidget(buttons)
            
            error_dialog.exec()
            
            self.status_bar.showMessage("Failed to generate installer", 5000)
    
    def test_installer(self):
        """Test the generated installer"""
        if not self.project.output_dir or not os.path.exists(self.project.output_dir):
            QMessageBox.warning(self, "Error", "No output directory specified or installer not generated yet")
            return
        
        # Find the installer
        installer_pattern = f"{self.project.name.replace(' ', '_')}_Setup.exe"
        installer_path = None
        
        for file in os.listdir(self.project.output_dir):
            if file.endswith("_Setup.exe"):
                installer_path = os.path.join(self.project.output_dir, file)
                break
        
        if not installer_path or not os.path.exists(installer_path):
            QMessageBox.warning(self, "Error", "Installer not found. Generate it first.")
            return
        
        # Ask for test mode
        reply = QMessageBox.question(
            self, "Test Installer",
            "This will run the installer in test mode.\n"
            "Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                subprocess.Popen([installer_path, "/?"])
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to run installer:\n{str(e)}")
    
    # Tools
    def scan_for_files(self):
        """Scan directory for files"""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory to Scan")
        
        if dir_path:
            # Ask for file patterns
            patterns, ok = QInputDialog.getText(
                self, "File Patterns",
                "Enter file patterns to scan (separated by semicolons):",
                text="*.exe;*.dll;*.py;*.txt;*.md"
            )
            
            if ok and patterns:
                # Create progress dialog
                progress_dialog = QProgressDialog("Scanning files...", "Cancel", 0, 100, self)
                progress_dialog.setWindowTitle("Scanning")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                
                # Start scanner thread
                self.scanner_thread = FileScannerThread(dir_path, patterns.split(';'))
                self.scanner_thread.progress.connect(progress_dialog.setValue)
                self.scanner_thread.file_found.connect(self.on_file_found)
                self.scanner_thread.finished.connect(
                    lambda files: progress_dialog.close() or self.on_scan_finished(files)
                )
                
                self.scanner_thread.start()
                progress_dialog.exec()
    
    def on_file_found(self, file_info):
        """Handle file found during scan"""
        # Could be used to update progress
        pass
    
    def on_scan_finished(self, files):
        """Handle scan completion"""
        if files:
            # Ask which files to add
            dialog = FileSelectionDialog(files, self)
            if dialog.exec():
                selected_files = dialog.get_selected_files()
                
                # Add selected files to project
                base_dir = os.path.dirname(files[0]['path']) if files else ''
                for file_info in selected_files:
                    rel_path = file_info['relative']
                    file_entry = FileEntry(
                        source_path=file_info['path'],
                        install_path=rel_path,
                        is_binary=is_binary_file(file_info['path'])
                    )
                    self.project.files.append(file_entry)
                
                self.update_tree_view()
                self.update_files_table()
                
                self.status_bar.showMessage(f"Added {len(selected_files)} files", 3000)
    
    def validate_project_dialog(self):
        """Show project validation dialog"""
        self.update_project_from_ui()
        is_valid, errors, warnings = validate_project(self.project)
        
        if errors:
            message = "Validation failed:\n\n" + "\n".join(errors)
            if warnings:
                message += "\n\nWarnings:\n" + "\n".join(warnings)
            QMessageBox.critical(self, "Validation Failed", message)
        elif warnings:
            message = "Validation completed with warnings:\n\n" + "\n".join(warnings)
            QMessageBox.warning(self, "Validation Warnings", message)
        else:
            QMessageBox.information(self, "Validation", "Project configuration is valid")
    
    # Helpers
    def browse_directory(self, line_edit):
        """Browse for directory"""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            line_edit.setText(dir_path)
    
    def browse_file(self, line_edit, title, filter):
        """Browse for file"""
        file_path, _ = QFileDialog.getOpenFileName(self, title, "", filter)
        if file_path:
            line_edit.setText(file_path)
    
    def on_tree_item_double_clicked(self, item):
        """Handle tree item double click"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            item_type, item_data = data
            
            if item_type == "file":
                # Select file in table
                for row in range(self.files_table.rowCount()):
                    table_item = self.files_table.item(row, 0)
                    if table_item and table_item.data(Qt.ItemDataRole.UserRole) == item_data:
                        self.files_table.selectRow(row)
                        self.files_table.scrollToItem(table_item)
                        break
            
            elif item_type == "script":
                # Select script in list
                for i in range(self.scripts_list.count()):
                    list_item = self.scripts_list.item(i)
                    if list_item.data(Qt.ItemDataRole.UserRole) == item_data:
                        self.scripts_list.setCurrentItem(list_item)
                        self.scripts_list.scrollToItem(list_item)
                        break
    
    def remove_item(self):
        """Remove selected item from tree"""
        selected_items = self.project_tree.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if data:
            item_type, item_data = data
            
            if item_type == "file":
                if item_data in self.project.files:
                    self.project.files.remove(item_data)
            
            elif item_type == "script":
                if item_data in self.project.script_elements:
                    self.project.script_elements.remove(item_data)
            
            elif item_type == "shortcut":
                if item_data in self.project.shortcuts:
                    self.project.shortcuts.remove(item_data)
            
            elif item_type == "registry":
                if item_data in self.project.registry_entries:
                    self.project.registry_entries.remove(item_data)
            
            elif item_type == "dependency":
                if item_data in self.project.dependencies:
                    self.project.dependencies.remove(item_data)
            
            self.update_tree_view()
            self.update_files_table()
            self.update_scripts_list()
            self.update_shortcuts_table()
            self.update_registry_table()
            self.update_dependencies_table()
    
    # Menu actions
    def show_preferences(self):
        """Show preferences dialog"""
        QMessageBox.information(self, "Preferences", "Preferences dialog will be implemented in a future version")
    
    def show_documentation(self):
        """Show documentation"""
        QDesktopServices.openUrl(QUrl("https://github.com/Idonot-Grief/installer-creator-pro"))
    
    def show_examples(self):
        """Show examples"""
        QMessageBox.information(self, "Examples", "Example projects will be available in a future version")
    
    def show_about(self):
        """Show about dialog"""
        dialog = AboutDialog(self)
        dialog.exec()