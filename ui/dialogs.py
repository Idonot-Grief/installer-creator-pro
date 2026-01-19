"""
Dialog classes for Installer Creator Pro
"""

import json
import uuid
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QTextEdit, QCheckBox, QDialogButtonBox, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QAbstractItemView,
    QLabel, QSpinBox, QRadioButton, QButtonGroup, QFileDialog,
    QTabWidget, QWidget, QGroupBox, QTextBrowser
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from core.models import (
    ScriptElement, ScriptElementType, ShortcutConfig,
    RegistryEntry, Dependency, FileEntry
)

class ScriptElementDialog(QDialog):
    """Dialog for editing script elements"""
    def __init__(self, element: Optional[ScriptElement] = None, parent=None):
        super().__init__(parent)
        self.element = element
        self.setWindowTitle("Script Element Editor" if element else "Add Script Element")
        self.setMinimumWidth(500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Name
        self.name_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)
        
        # Type
        self.type_combo = QComboBox()
        for elem_type in ScriptElementType:
            self.type_combo.addItem(elem_type.value.replace('_', ' ').title(), elem_type)
        form.addRow("Type:", self.type_combo)
        
        # Parameters
        self.params_edit = QTextEdit()
        self.params_edit.setPlaceholderText('{\n  "key": "value"\n}')
        form.addRow("Parameters (JSON):", self.params_edit)
        
        # Enabled
        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(True)
        form.addRow("", self.enabled_check)
        
        # Critical
        self.critical_check = QCheckBox("Critical (stop on failure)")
        form.addRow("", self.critical_check)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Load existing data
        if self.element:
            self.load_element()
    
    def load_element(self):
        """Load element data into form"""
        self.name_edit.setText(self.element.name)
        
        index = self.type_combo.findData(self.element.type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        
        if self.element.parameters:
            self.params_edit.setPlainText(json.dumps(self.element.parameters, indent=2))
        
        self.enabled_check.setChecked(self.element.enabled)
        self.critical_check.setChecked(self.element.critical)
    
    def get_element(self) -> ScriptElement:
        """Get script element from form data"""
        name = self.name_edit.text().strip()
        if not name:
            name = f"Script Element {uuid.uuid4().hex[:4]}"
        
        elem_type = self.type_combo.currentData()
        
        params_text = self.params_edit.toPlainText().strip()
        parameters = {}
        if params_text:
            try:
                parameters = json.loads(params_text)
            except json.JSONDecodeError:
                pass
        
        return ScriptElement(
            type=elem_type,
            name=name,
            parameters=parameters,
            enabled=self.enabled_check.isChecked(),
            critical=self.critical_check.isChecked()
        )

class ShortcutDialog(QDialog):
    """Dialog for editing shortcuts"""
    def __init__(self, shortcut: Optional[ShortcutConfig] = None, parent=None):
        super().__init__(parent)
        self.shortcut = shortcut
        self.setWindowTitle("Edit Shortcut" if shortcut else "Add Shortcut")
        self.setMinimumWidth(400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Name
        self.name_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)
        
        # Target
        self.target_edit = QLineEdit()
        form.addRow("Target:", self.target_edit)
        
        # Working directory
        self.working_dir_edit = QLineEdit()
        form.addRow("Working Directory:", self.working_dir_edit)
        
        # Arguments
        self.args_edit = QLineEdit()
        form.addRow("Arguments:", self.args_edit)
        
        # Icon
        self.icon_edit = QLineEdit()
        form.addRow("Icon (optional):", self.icon_edit)
        
        # Location
        self.location_combo = QComboBox()
        self.location_combo.addItems(["Desktop", "Start Menu", "Both"])
        form.addRow("Location:", self.location_combo)
        
        # Description
        self.desc_edit = QLineEdit()
        form.addRow("Description:", self.desc_edit)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Load existing data
        if self.shortcut:
            self.load_shortcut()
    
    def load_shortcut(self):
        """Load shortcut data into form"""
        self.name_edit.setText(self.shortcut.name)
        self.target_edit.setText(self.shortcut.target)
        self.working_dir_edit.setText(self.shortcut.working_dir)
        self.args_edit.setText(self.shortcut.arguments)
        self.icon_edit.setText(self.shortcut.icon)
        
        location_map = {
            "desktop": "Desktop",
            "start_menu": "Start Menu",
            "both": "Both"
        }
        location_text = location_map.get(self.shortcut.location, "Desktop")
        index = self.location_combo.findText(location_text)
        if index >= 0:
            self.location_combo.setCurrentIndex(index)
        
        self.desc_edit.setText(self.shortcut.description)
    
    def get_shortcut(self) -> ShortcutConfig:
        """Get shortcut from form data"""
        location_map = {
            "Desktop": "desktop",
            "Start Menu": "start_menu",
            "Both": "both"
        }
        
        return ShortcutConfig(
            name=self.name_edit.text().strip(),
            target=self.target_edit.text().strip(),
            working_dir=self.working_dir_edit.text().strip(),
            arguments=self.args_edit.text().strip(),
            icon=self.icon_edit.text().strip(),
            location=location_map.get(self.location_combo.currentText(), "desktop"),
            description=self.desc_edit.text().strip()
        )

class RegistryDialog(QDialog):
    """Dialog for editing registry entries"""
    def __init__(self, reg_entry: Optional[RegistryEntry] = None, parent=None):
        super().__init__(parent)
        self.reg_entry = reg_entry
        self.setWindowTitle("Edit Registry Entry" if reg_entry else "Add Registry Entry")
        self.setMinimumWidth(500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Hive
        self.hive_combo = QComboBox()
        self.hive_combo.addItems([
            "HKEY_CLASSES_ROOT",
            "HKEY_CURRENT_USER",
            "HKEY_LOCAL_MACHINE",
            "HKEY_USERS",
            "HKEY_CURRENT_CONFIG"
        ])
        form.addRow("Hive:", self.hive_combo)
        
        # Key
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Software\\MyCompany\\MyApp")
        form.addRow("Key:", self.key_edit)
        
        # Value name
        self.value_name_edit = QLineEdit()
        self.value_name_edit.setPlaceholderText("(Default) for default value")
        form.addRow("Value Name:", self.value_name_edit)
        
        # Value type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["REG_SZ", "REG_DWORD", "REG_BINARY", "REG_MULTI_SZ", "REG_EXPAND_SZ"])
        form.addRow("Value Type:", self.type_combo)
        
        # Value data
        self.value_edit = QLineEdit()
        form.addRow("Value Data:", self.value_edit)
        
        # Action
        self.action_combo = QComboBox()
        self.action_combo.addItems(["Create", "Delete", "Modify"])
        form.addRow("Action:", self.action_combo)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Load existing data
        if self.reg_entry:
            self.load_registry()
    
    def load_registry(self):
        """Load registry data into form"""
        index = self.hive_combo.findText(self.reg_entry.hive)
        if index >= 0:
            self.hive_combo.setCurrentIndex(index)
        
        self.key_edit.setText(self.reg_entry.key)
        self.value_name_edit.setText(self.reg_entry.value_name)
        
        index = self.type_combo.findText(self.reg_entry.value_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        
        self.value_edit.setText(str(self.reg_entry.value_data))
        
        action_text = self.reg_entry.action.capitalize()
        index = self.action_combo.findText(action_text)
        if index >= 0:
            self.action_combo.setCurrentIndex(index)
    
    def get_registry_entry(self) -> RegistryEntry:
        """Get registry entry from form data"""
        return RegistryEntry(
            hive=self.hive_combo.currentText(),
            key=self.key_edit.text().strip(),
            value_name=self.value_name_edit.text().strip(),
            value_type=self.type_combo.currentText(),
            value_data=self.value_edit.text().strip(),
            action=self.action_combo.currentText().lower()
        )

class DependencyDialog(QDialog):
    """Dialog for editing dependencies"""
    def __init__(self, dependency: Optional[Dependency] = None, parent=None):
        super().__init__(parent)
        self.dependency = dependency
        self.setWindowTitle("Edit Dependency" if dependency else "Add Dependency")
        self.setMinimumWidth(500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Name
        self.name_edit = QLineEdit()
        form.addRow("Name:", self.name_edit)
        
        # Version
        self.version_edit = QLineEdit()
        form.addRow("Version:", self.version_edit)
        
        # Installer path
        self.installer_edit = QLineEdit()
        form.addRow("Installer Path:", self.installer_edit)
        
        # Check command
        self.check_edit = QLineEdit()
        self.check_edit.setPlaceholderText("python --version")
        form.addRow("Check Command:", self.check_edit)
        
        # Required
        self.required_check = QCheckBox("Required")
        self.required_check.setChecked(True)
        form.addRow("", self.required_check)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Load existing data
        if self.dependency:
            self.load_dependency()
    
    def load_dependency(self):
        """Load dependency data into form"""
        self.name_edit.setText(self.dependency.name)
        self.version_edit.setText(self.dependency.version)
        self.installer_edit.setText(self.dependency.installer_path)
        self.check_edit.setText(self.dependency.check_command)
        self.required_check.setChecked(self.dependency.required)
    
    def get_dependency(self) -> Dependency:
        """Get dependency from form data"""
        return Dependency(
            name=self.name_edit.text().strip(),
            version=self.version_edit.text().strip(),
            installer_path=self.installer_edit.text().strip(),
            check_command=self.check_edit.text().strip(),
            required=self.required_check.isChecked()
        )

class AboutDialog(QDialog):
    """About dialog"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Installer Creator Pro")
        self.setFixedSize(400, 300)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("Installer Creator Pro")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        version = QLabel("Version 2.0.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        
        desc = QLabel(
            "Professional installer creation tool\\n"
            "Create Windows installers with PyQt6 and PyInstaller"
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        features = QLabel(
            "• Customizable installer UI\\n"
            "• File and directory deployment\\n"
            "• Registry modifications\\n"
            "• Shortcut creation\\n"
            "• Dependency checking\\n"
            "• Silent installation support"
        )
        layout.addWidget(features)
        
        layout.addStretch()
        
        copyright_label = QLabel("© 2024 Installer Creator Pro")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright_label)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)