"""
Core module for Installer Creator Pro
"""

from .models import (
    ScriptElementType, ScriptElement, ShortcutConfig,
    RegistryEntry, FileEntry, Dependency, ProjectConfig
)
from .project_manager import ProjectManager
from .generator import InstallerGeneratorThread

__all__ = [
    'ScriptElementType',
    'ScriptElement',
    'ShortcutConfig',
    'RegistryEntry',
    'FileEntry',
    'Dependency',
    'ProjectConfig',
    'ProjectManager',
    'InstallerGeneratorThread'
]