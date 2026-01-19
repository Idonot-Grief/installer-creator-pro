"""
Installer generation logic for Installer Creator Pro
"""
import os
import sys
import json
import tempfile
import shutil
import subprocess

from PyQt6.QtCore import QThread, pyqtSignal

from .models import ProjectConfig


class InstallerGeneratorThread(QThread):
    """Thread for generating installer"""
    progress = pyqtSignal(int, str)
    log_message = pyqtSignal(str)
    finished = pyqtSignal(str, bool)  # (message, success)

    def __init__(self, project: ProjectConfig, output_path: str):
        super().__init__()
        self.project = project
        self.output_path = output_path
        self.temp_dir = None

    def run(self):
        try:
            self.progress.emit(0, "Starting installer generation...")
            self.log_message.emit("=== Installer Generation Started ===")

            self.temp_dir = tempfile.mkdtemp(prefix="instgen_")
            self.progress.emit(5, f"Created temp directory: {self.temp_dir}")

            installer_code = self._generate_installer_script()
            installer_py = os.path.join(self.temp_dir, "installer.py")
            with open(installer_py, "w", encoding="utf-8") as f:
                f.write(installer_code)

            self.progress.emit(20, "Generated installer script")

            spec_content = self._generate_spec_file()
            spec_file = os.path.join(self.temp_dir, "installer.spec")
            with open(spec_file, "w", encoding="utf-8") as f:
                f.write(spec_content)

            self.progress.emit(35, "Generated PyInstaller spec")

            self._run_pyinstaller()

            self.progress.emit(100, "Installer build completed")
            self.log_message.emit("Installer generation successful")
            self.finished.emit(self.output_path, True)

        except Exception as e:
            msg = f"Installer generation failed: {e}"
            self.log_message.emit(f"ERROR: {msg}")
            self.finished.emit(msg, False)

        finally:
            # Clean up temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                    self.log_message.emit(f"Cleaned up temp directory: {self.temp_dir}")
                except Exception as e:
                    self.log_message.emit(f"Warning: Could not clean temp directory: {e}")

    def _run_pyinstaller(self):
        self.log_message.emit("Running PyInstaller...")
        self.progress.emit(40, "Running PyInstaller...")

        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "installer.spec",
        ]

        result = subprocess.run(
            cmd,
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
        )

        self.progress.emit(80, "PyInstaller finished, checking output...")

        if result.returncode != 0:
            self.log_message.emit(f"PyInstaller stderr: {result.stderr}")
            raise RuntimeError(f"PyInstaller failed: {result.stderr}")

        # Check what was actually generated in dist folder
        dist_dir = os.path.join(self.temp_dir, "dist")
        if not os.path.exists(dist_dir):
            raise FileNotFoundError(f"Dist directory not found: {dist_dir}")

        # List all files in dist directory
        dist_files = os.listdir(dist_dir)
        self.log_message.emit(f"Files in dist: {dist_files}")

        # Find the .exe file
        exe_files = [f for f in dist_files if f.endswith('.exe')]
        if not exe_files:
            raise FileNotFoundError(f"No .exe file found in {dist_dir}. Files present: {dist_files}")

        generated_exe = os.path.join(dist_dir, exe_files[0])
        self.log_message.emit(f"Found generated installer: {generated_exe}")

        # Ensure output directory exists
        output_dir = os.path.dirname(self.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        shutil.move(generated_exe, self.output_path)
        self.log_message.emit(f"Installer created → {self.output_path}")
        self.progress.emit(95, "Installer file moved to output location")

    def _generate_installer_script(self) -> str:
        name = self.project.name or "My Application"
        version = self.project.version
        description = self.project.description or ""

        # Use repr() to generate Python literals instead of JSON
        files_repr = repr([f.to_dict() for f in self.project.files])
        shortcuts_repr = repr([s.to_dict() for s in self.project.shortcuts])
        registry_repr = repr([r.to_dict() for r in self.project.registry_entries])
        scripts_repr = repr([e.to_dict() for e in self.project.script_elements])
        deps_repr = repr([d.to_dict() for d in self.project.dependencies])

        return f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import subprocess
import winreg
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QProgressBar, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

FILES_DATA = {files_repr}
SHORTCUTS = {shortcuts_repr}
REGISTRY_ENTRIES = {registry_repr}
SCRIPT_ELEMENTS = {scripts_repr}
DEPENDENCIES = {deps_repr}

PROJECT_NAME = {json.dumps(name)}
PROJECT_VERSION = {json.dumps(version)}
PROJECT_DESCRIPTION = {json.dumps(description)}

CREATE_UNINSTALLER = True


class InstallThread(QThread):
    """Worker thread for installation process"""
    progress = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, install_path):
        super().__init__()
        self.install_path = install_path

    def run(self):
        try:
            # Create install directory
            os.makedirs(self.install_path, exist_ok=True)
            self.progress.emit(10, "Created installation directory")

            # Install dependencies
            if DEPENDENCIES:
                self.progress.emit(20, "Installing dependencies...")
                for dep in DEPENDENCIES:
                    self._install_dependency(dep)

            # Copy files
            self.progress.emit(40, "Copying files...")
            for file_info in FILES_DATA:
                self._copy_file(file_info)

            # Create shortcuts
            self.progress.emit(60, "Creating shortcuts...")
            for shortcut in SHORTCUTS:
                self._create_shortcut(shortcut)

            # Apply registry entries
            self.progress.emit(70, "Applying registry entries...")
            for reg_entry in REGISTRY_ENTRIES:
                self._apply_registry(reg_entry)

            # Run post-install scripts
            self.progress.emit(80, "Running post-install scripts...")
            for script in SCRIPT_ELEMENTS:
                if script.get('event') == 'post_install':
                    self._run_script(script)

            # Create uninstaller
            if CREATE_UNINSTALLER:
                self.progress.emit(90, "Creating uninstaller...")
                self._create_uninstaller()

            self.progress.emit(100, "Installation complete!")
            self.finished_signal.emit(True, "Installation completed successfully!")

        except Exception as e:
            self.finished_signal.emit(False, f"Installation failed: {{str(e)}}")

    def _install_dependency(self, dep):
        """Install a dependency using pip or system command"""
        dep_type = dep.get('type', 'pip')
        name = dep.get('name', '')
        
        if dep_type == 'pip' and name:
            subprocess.run([sys.executable, '-m', 'pip', 'install', name], 
                         check=True, capture_output=True)

    def _copy_file(self, file_info):
        """Copy a file to the installation directory"""
        source = file_info.get('source', '')
        dest = file_info.get('destination', '')
        
        if not source or not dest:
            return
            
        dest_path = os.path.join(self.install_path, dest)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        if os.path.isfile(source):
            shutil.copy2(source, dest_path)
        elif os.path.isdir(source):
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            shutil.copytree(source, dest_path)

    def _create_shortcut(self, shortcut):
        """Create a Windows shortcut"""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            
            name = shortcut.get('name', '')
            target = shortcut.get('target', '')
            location = shortcut.get('location', 'desktop')
            
            if location == 'desktop':
                shortcut_path = os.path.join(os.path.expanduser('~'), 'Desktop', f"{{name}}.lnk")
            elif location == 'start_menu':
                shortcut_path = os.path.join(os.environ['APPDATA'], 
                                            'Microsoft', 'Windows', 'Start Menu', 
                                            'Programs', f"{{name}}.lnk")
            else:
                return
            
            target_path = os.path.join(self.install_path, target)
            link = shell.CreateShortCut(shortcut_path)
            link.Targetpath = target_path
            link.WorkingDirectory = os.path.dirname(target_path)
            link.save()
        except ImportError:
            pass  # win32com not available

    def _apply_registry(self, reg_entry):
        """Apply a registry entry"""
        try:
            root = reg_entry.get('root', 'HKEY_CURRENT_USER')
            key_path = reg_entry.get('key', '')
            value_name = reg_entry.get('name', '')
            value_data = reg_entry.get('value', '')
            value_type = reg_entry.get('type', 'REG_SZ')
            
            root_key = getattr(winreg, root, winreg.HKEY_CURRENT_USER)
            
            key = winreg.CreateKey(root_key, key_path)
            
            if value_type == 'REG_DWORD':
                winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, int(value_data))
            else:
                winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, str(value_data))
            
            winreg.CloseKey(key)
        except Exception:
            pass  # Silently fail on registry errors

    def _run_script(self, script):
        """Run a post-install script"""
        script_type = script.get('type', 'python')
        content = script.get('content', '')
        
        if script_type == 'python' and content:
            exec(content)
        elif script_type == 'cmd' and content:
            subprocess.run(content, shell=True, cwd=self.install_path)

    def _create_uninstaller(self):
        """Create an uninstaller executable"""
        uninstall_script = f\'\'\'
import os
import sys
import shutil
from PyQt6.QtWidgets import QApplication, QMessageBox

def uninstall():
    reply = QMessageBox.question(None, "Uninstall", 
                                "Are you sure you want to uninstall {{PROJECT_NAME}}?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    
    if reply == QMessageBox.StandardButton.Yes:
        try:
            install_dir = r"{{self.install_path}}"
            if os.path.exists(install_dir):
                shutil.rmtree(install_dir)
            QMessageBox.information(None, "Success", "Uninstallation complete!")
        except Exception as ex:
            QMessageBox.critical(None, "Error", f"Uninstallation failed: {{{{ex}}}}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    uninstall()
\'\'\'
        uninstall_path = os.path.join(self.install_path, "uninstall.py")
        with open(uninstall_path, 'w') as f:
            f.write(uninstall_script)


class InstallerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{{PROJECT_NAME}} Setup")
        self.setFixedSize(580, 420)
        self.install_thread = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel(f"<h2>{{PROJECT_NAME}}</h2><h4>Version {{PROJECT_VERSION}}</h4>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        if PROJECT_DESCRIPTION:
            desc = QLabel(PROJECT_DESCRIPTION)
            desc.setWordWrap(True)
            desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(desc)

        layout.addStretch()

        self.install_btn = QPushButton("Install")
        self.install_btn.setMinimumHeight(40)
        self.install_btn.clicked.connect(self.install)
        layout.addWidget(self.install_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.clicked.connect(self.close)
        layout.addWidget(self.cancel_btn)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMinimumHeight(30)
        layout.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

    def install(self):
        default_path = os.path.join(
            os.environ.get("ProgramFiles", "C:\\\\Program Files"), 
            PROJECT_NAME.replace(" ", "_")
        )
        
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Install Location",
            default_path
        )
        
        if not path:
            return

        self.install_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)

        self.install_thread = InstallThread(path)
        self.install_thread.progress.connect(self.update_progress)
        self.install_thread.finished_signal.connect(self.install_finished)
        self.install_thread.start()

    def update_progress(self, value, message):
        self.progress.setValue(value)
        self.status.setText(message)

    def install_finished(self, success, message):
        if success:
            QMessageBox.information(self, "Success", message)
            self.close()
        else:
            QMessageBox.critical(self, "Error", message)
            self.install_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
            self.progress.setVisible(False)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = InstallerWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
'''

    def _generate_spec_file(self) -> str:
        name_safe = self.project.name.replace(" ", "_").replace("-", "_")

        return f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['installer.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['win32com.client', 'winreg'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{name_safe}_Setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''