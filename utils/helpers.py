"""
Utility functions for Installer Creator Pro
"""

import os
import re
from typing import List, Tuple

def format_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {units[i]}"

def is_binary_file(file_path: str) -> bool:
    """Check if a file is binary"""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\0' in chunk
    except:
        return False

def validate_project(project) -> Tuple[bool, List[str], List[str]]:
    """
    Validate project configuration
    
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    errors = []
    warnings = []
    
    # Check required fields
    if not project.name or not project.name.strip():
        errors.append("Project name is required")
    
    if not project.version or not project.version.strip():
        errors.append("Version is required")
    
    if not project.output_dir:
        errors.append("Output directory is required")
    else:
        # Check if output directory is writable
        if os.path.exists(project.output_dir):
            try:
                test_file = os.path.join(project.output_dir, ".test_write")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except:
                errors.append("Output directory is not writable")
    
    # Check if icon exists
    if project.icon_path and not os.path.exists(project.icon_path):
        warnings.append(f"Icon file not found: {project.icon_path}")
    
    # Check if license file exists
    if project.license_enabled and project.license_file and not os.path.exists(project.license_file):
        warnings.append(f"License file not found: {project.license_file}")
    
    # Check if certificate exists for signing
    if project.sign_installer and project.certificate_path and not os.path.exists(project.certificate_path):
        warnings.append(f"Certificate file not found: {project.certificate_path}")
    
    # Check if files exist
    for file_entry in project.files:
        if not file_entry.is_directory and not os.path.exists(file_entry.source_path):
            warnings.append(f"File not found: {file_entry.source_path}")
    
    # Check for valid version format
    if project.version:
        version_pattern = r'^\d+(\.\d+)*$'
        if not re.match(version_pattern, project.version):
            warnings.append(f"Version format should be like '1.0.0': {project.version}")
    
    # Check default install directory
    if project.default_install_dir:
        if '{name}' not in project.default_install_dir:
            warnings.append("Default install directory should contain {name} placeholder")
    
    is_valid = len(errors) == 0
    
    return is_valid, errors, warnings

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe use"""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Ensure not empty
    if not filename:
        filename = "unnamed"
    
    return filename

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)