"""
Data models and enums for Installer Creator Pro
"""

import os
import sys
import json
import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

class ScriptElementType(Enum):
    INSTALL_FILE = "install_file"
    CREATE_DIR = "create_dir"
    CREATE_SHORTCUT = "create_shortcut"
    EXECUTE_COMMAND = "execute_command"
    SET_REGISTRY = "set_registry"
    CREATE_UNINSTALLER = "create_uninstaller"
    SHOW_LICENSE = "show_license"
    REQUIRE_ADMIN = "require_admin"
    CHECK_DISK_SPACE = "check_disk_space"
    DOWNLOAD_FILE = "download_file"
    CREATE_SERVICE = "create_service"
    SET_ENVIRONMENT = "set_environment"
    RUN_SCRIPT = "run_script"

@dataclass
class ScriptElement:
    """Represents an element in the installer script"""
    type: ScriptElementType
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    enabled: bool = True
    critical: bool = False
    
    def __post_init__(self):
        if not self.id:
            self.id = f"{self.type.value}_{uuid.uuid4().hex[:8]}"
    
    def __hash__(self):
        return hash((self.type.value, self.name, self.id))
    
    def __eq__(self, other):
        return self.id == other.id if isinstance(other, ScriptElement) else False
    
    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "name": self.name,
            "parameters": self.parameters,
            "id": self.id,
            "enabled": self.enabled,
            "critical": self.critical
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ScriptElement':
        return cls(
            type=ScriptElementType(data["type"]),
            name=data["name"],
            parameters=data.get("parameters", {}),
            id=data.get("id", str(uuid.uuid4())[:8]),
            enabled=data.get("enabled", True),
            critical=data.get("critical", False)
        )

@dataclass
class ShortcutConfig:
    """Configuration for a shortcut"""
    name: str
    target: str
    icon: str = ""
    working_dir: str = ""
    arguments: str = ""
    location: str = "desktop"
    description: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ShortcutConfig':
        return cls(**data)

@dataclass
class RegistryEntry:
    """Registry configuration"""
    hive: str = "HKEY_CURRENT_USER"
    key: str = ""
    value_name: str = ""
    value_type: str = "REG_SZ"
    value_data: Any = ""
    action: str = "create"
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RegistryEntry':
        return cls(**data)

@dataclass
class FileEntry:
    """Represents a file in the project"""
    source_path: str
    install_path: str
    is_binary: bool = False
    is_directory: bool = False
    compress: bool = True
    hash: str = ""
    version: str = ""
    description: str = ""
    
    def __post_init__(self):
        if not self.hash and os.path.exists(self.source_path) and not self.is_directory:
            self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate SHA256 hash of the file"""
        if self.is_directory or not os.path.exists(self.source_path):
            return ""
        
        try:
            hash_sha256 = hashlib.sha256()
            with open(self.source_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except:
            return ""
    
    def to_dict(self) -> dict:
        return {
            "source_path": self.source_path,
            "install_path": self.install_path,
            "is_binary": self.is_binary,
            "is_directory": self.is_directory,
            "compress": self.compress,
            "hash": self.hash,
            "version": self.version,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FileEntry':
        return cls(**data)

@dataclass
class Dependency:
    """Software dependency"""
    name: str
    version: str = ""
    installer_path: str = ""
    check_command: str = ""
    required: bool = True
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Dependency':
        return cls(**data)

@dataclass
class ProjectConfig:
    """Project configuration"""
    name: str = "New Project"
    version: str = "1.0.0"
    author: str = ""
    company: str = ""
    description: str = ""
    copyright: str = ""
    icon_path: str = ""
    output_dir: str = ""
    default_install_dir: str = "%PROGRAMFILES%\\{name}"
    python_version: str = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    # Installer options
    require_admin: bool = True
    compression: str = "upx"
    license_enabled: bool = False
    license_text: str = ""
    license_file: str = ""
    create_uninstaller: bool = True
    silent_mode: bool = False
    overwrite_existing: bool = True
    
    # UI customization
    installer_title: str = "{name} Setup"
    installer_style: str = "default"
    background_color: str = ""
    text_color: str = ""
    button_color: str = ""
    custom_css: str = ""
    
    # PyInstaller options
    onefile: bool = True
    console: bool = False
    hidden_imports: List[str] = field(default_factory=list)
    additional_hooks: List[str] = field(default_factory=list)
    exclude_modules: List[str] = field(default_factory=list)
    
    # Script elements
    script_elements: List[ScriptElement] = field(default_factory=list)
    
    # Shortcuts
    shortcuts: List[ShortcutConfig] = field(default_factory=list)
    
    # Registry entries
    registry_entries: List[RegistryEntry] = field(default_factory=list)
    
    # Dependencies
    dependencies: List[Dependency] = field(default_factory=list)
    
    # Custom paths
    search_paths: List[str] = field(default_factory=list)
    
    # Files in the project
    files: List[FileEntry] = field(default_factory=list)
    
    # Advanced options
    sign_installer: bool = False
    certificate_path: str = ""
    certificate_password: str = ""
    timestamp_server: str = "http://timestamp.digicert.com"
    
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    modified: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "company": self.company,
            "description": self.description,
            "copyright": self.copyright,
            "icon_path": self.icon_path,
            "output_dir": self.output_dir,
            "default_install_dir": self.default_install_dir,
            "python_version": self.python_version,
            "require_admin": self.require_admin,
            "compression": self.compression,
            "license_enabled": self.license_enabled,
            "license_text": self.license_text,
            "license_file": self.license_file,
            "create_uninstaller": self.create_uninstaller,
            "silent_mode": self.silent_mode,
            "overwrite_existing": self.overwrite_existing,
            "installer_title": self.installer_title,
            "installer_style": self.installer_style,
            "background_color": self.background_color,
            "text_color": self.text_color,
            "button_color": self.button_color,
            "custom_css": self.custom_css,
            "onefile": self.onefile,
            "console": self.console,
            "hidden_imports": self.hidden_imports,
            "additional_hooks": self.additional_hooks,
            "exclude_modules": self.exclude_modules,
            "script_elements": [e.to_dict() for e in self.script_elements],
            "shortcuts": [s.to_dict() for s in self.shortcuts],
            "registry_entries": [r.to_dict() for r in self.registry_entries],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "search_paths": self.search_paths,
            "files": [f.to_dict() for f in self.files],
            "sign_installer": self.sign_installer,
            "certificate_path": self.certificate_path,
            "certificate_password": self.certificate_password,
            "timestamp_server": self.timestamp_server,
            "created": self.created,
            "modified": self.modified
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectConfig':
        files = [FileEntry.from_dict(f) for f in data.get("files", [])]
        script_elements = [ScriptElement.from_dict(e) for e in data.get("script_elements", [])]
        shortcuts = [ShortcutConfig.from_dict(s) for s in data.get("shortcuts", [])]
        registry_entries = [RegistryEntry.from_dict(r) for r in data.get("registry_entries", [])]
        dependencies = [Dependency.from_dict(d) for d in data.get("dependencies", [])]
        
        updated_data = data.copy()
        updated_data["files"] = files
        updated_data["script_elements"] = script_elements
        updated_data["shortcuts"] = shortcuts
        updated_data["registry_entries"] = registry_entries
        updated_data["dependencies"] = dependencies
        
        if "company" not in updated_data:
            updated_data["company"] = ""
        if "copyright" not in updated_data:
            updated_data["copyright"] = f"Copyright © {datetime.now().year}"
        if "create_uninstaller" not in updated_data:
            updated_data["create_uninstaller"] = True
        if "silent_mode" not in updated_data:
            updated_data["silent_mode"] = False
        if "overwrite_existing" not in updated_data:
            updated_data["overwrite_existing"] = True
        if "installer_title" not in updated_data:
            updated_data["installer_title"] = "{name} Setup"
        if "installer_style" not in updated_data:
            updated_data["installer_style"] = "default"
        
        return cls(**updated_data)