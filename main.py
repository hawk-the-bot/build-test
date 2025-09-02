#!/usr/bin/env python3

import sys
import os
import subprocess
import time
import requests
import shutil
import tempfile
import zipfile
import psutil
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QMessageBox, QProgressBar
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont


# Embedded Updater Classes - No import issues!
class PlatformDetector:
    """Detect platform for S3 download"""
    
    @staticmethod
    def get_platform():
        """Get simplified platform name"""
        if sys.platform == 'darwin':
            return 'mac'
        elif sys.platform.startswith('win'):
            return 'windows'
        else:
            return 'linux'
    
    @staticmethod
    def get_s3_url():
        """Get S3 URL for current platform - Windows priority"""
        # S3 Configuration - WINDOWS FOCUSED
        # PRODUCTION: Using S3 for real updates
        S3_URLS = {
            'windows': 'https://release-jesus-automator.s3.us-east-1.amazonaws.com/releases/main.dist.zip',
            'mac': 'https://your-s3-bucket.s3.amazonaws.com/BuildTestSystem-mac.zip'
        }
        
        platform = PlatformDetector.get_platform()
        url = S3_URLS.get(platform)
        
        if not url and platform != 'windows':
            raise Exception(f"Windows is the primary target. Current platform: {platform}")
        
        return url
    
    @staticmethod
    def get_filename():
        """Get filename from S3 URL"""
        url = PlatformDetector.get_s3_url()
        if url:
            return url.split('/')[-1]
        return None


class WindowsUpdater:
    """Windows-specific update handling - Industrial grade file replacement"""
    
    @staticmethod
    def get_current_executable():
        """Get current executable path"""
        if getattr(sys, 'frozen', False):
            return sys.executable
        else:
            # When running from Python script, simulate the executable path
            # This is for testing purposes
            script_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(script_dir, "BuildTestSystem.exe")
    
    @staticmethod
    def get_current_process_id():
        """Get current process ID"""
        return os.getpid()
    
    @staticmethod
    def create_backup(app_dir, backup_dir):
        """Create backup of current application"""
        try:
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            shutil.copytree(app_dir, backup_dir, ignore=shutil.ignore_patterns('*.tmp', '*.log'))
            return True
        except Exception as e:
            print(f"Backup failed: {e}")
            return False
    
    @staticmethod
    def install_from_zip(zip_file, current_exe, app_dir, backup_dir, temp_dir):
        """Install from .zip file - Full application directory replacement"""
        current_pid = WindowsUpdater.get_current_process_id()
        
        # Extract the zip file
        extract_dir = os.path.join(temp_dir, "extract")
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Find the main application directory in extracted files
        app_source_dir = None
        # Always look for BuildTestSystem.exe regardless of current executable detection
        main_exe_name = "BuildTestSystem.exe"
        
        for root, dirs, files in os.walk(extract_dir):
            if main_exe_name in files:
                app_source_dir = root
                break
        
        if not app_source_dir:
            raise Exception(f"Could not find {main_exe_name} in the update package")
        
        # Create backup
        if not WindowsUpdater.create_backup(app_dir, backup_dir):
            raise Exception("Failed to create backup")
        
        # Create simplified update script with proper path handling
        update_script = os.path.join(temp_dir, "updater.bat")
        
        # Escape paths properly for batch script
        app_dir_safe = app_dir.replace('/', '\\')
        app_source_dir_safe = app_source_dir.replace('/', '\\')
        backup_dir_safe = backup_dir.replace('/', '\\')
        current_exe_safe = current_exe.replace('/', '\\')
        extract_dir_safe = extract_dir.replace('/', '\\')
        
        script_content = f'''@echo off
echo [UPDATER] Starting update process...
echo [UPDATER] PID: {current_pid}

REM Wait for application to close
timeout /t 3 /nobreak > nul

REM Kill process if still running
taskkill /PID {current_pid} /F > nul 2>&1
timeout /t 2 /nobreak > nul

echo [UPDATER] Replacing files...

REM Simple file replacement with retry
set /a attempts=0
:retry
set /a attempts+=1
if %attempts% GTR 3 goto error

REM Use xcopy for simple file replacement
xcopy /E /H /C /I /Q /Y "{app_source_dir_safe}" "{app_dir_safe}" > nul 2>&1
if errorlevel 1 (
    echo [UPDATER] Copy failed, retry %attempts%
    timeout /t 2 /nobreak > nul
    goto retry
)

echo [UPDATER] Files updated successfully
echo [UPDATER] Starting application...
start "" "{current_exe_safe}"
goto cleanup

:error
echo [UPDATER] Update failed, restoring backup...
if exist "{backup_dir_safe}" (
    xcopy /E /H /C /I /Q /Y "{backup_dir_safe}" "{app_dir_safe}" > nul
    start "" "{current_exe_safe}"
)

:cleanup
timeout /t 2 /nobreak > nul
rmdir /s /q "{extract_dir_safe}" > nul 2>&1
del "%~f0" > nul 2>&1
'''
        
        with open(update_script, 'w') as f:
            f.write(script_content)
        
        # Run update script with proper permissions
        try:
            subprocess.Popen(
                [update_script], 
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        except Exception as e:
            # Fallback: try without special flags
            subprocess.Popen([update_script], shell=True)


class UpdateDownloader(QThread):
    """Thread to download and install updates directly from S3"""
    download_progress = Signal(int)  # percentage
    download_complete = Signal(str)  # filepath
    install_complete = Signal()
    error = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.platform = PlatformDetector.get_platform()
        self.download_url = PlatformDetector.get_s3_url()
        self.filename = PlatformDetector.get_filename()
        self.temp_dir = tempfile.mkdtemp()
        
        if not self.download_url:
            raise Exception(f"No S3 URL configured for {self.platform}")
        
    def run(self):
        try:
            self.download_file()
        except Exception as e:
            self.error.emit(f"Download failed: {str(e)}")
    
    def download_file(self):
        """Download the update file from S3 with progress tracking"""
        try:
            response = requests.get(self.download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            file_path = os.path.join(self.temp_dir, self.filename)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(file_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.download_progress.emit(progress)
            
            self.download_complete.emit(file_path)
            
        except Exception as e:
            raise Exception(f"S3 download failed: {str(e)}")
    
    def install_update(self, downloaded_file):
        """Platform-specific installation - Windows optimized"""
        try:
            if self.platform == 'windows':
                self.install_windows(downloaded_file)
            else:
                raise Exception("This build system is optimized for Windows.")
            
            self.install_complete.emit()
            
        except Exception as e:
            raise Exception(f"Installation failed: {str(e)}")
    
    def install_windows(self, downloaded_file):
        """Windows installation"""
        current_exe = WindowsUpdater.get_current_executable()
        app_dir = os.path.dirname(current_exe)
        backup_dir = os.path.join(self.temp_dir, "backup")
        
        file_ext = Path(downloaded_file).suffix.lower()
        
        if file_ext == '.zip':
            WindowsUpdater.install_from_zip(downloaded_file, current_exe, app_dir, backup_dir, self.temp_dir)
        else:
            raise Exception(f"Unsupported Windows update file type: {file_ext}")

def get_version():
    """Read version from version.txt file"""
    try:
        with open('version.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "1.0.0"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_version = get_version()
        self.downloader = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Build Test System - Windows Edition")
        self.setGeometry(300, 300, 400, 300)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Hello World label
        hello_label = QLabel("Hello Windows! - VERSION 1.0.8")
        hello_label.setAlignment(Qt.AlignCenter)
        hello_label.setFont(QFont("Arial", 24))
        layout.addWidget(hello_label)
        
        # Version label
        version_label = QLabel(f"Version: {self.current_version}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setFont(QFont("Arial", 12))
        layout.addWidget(version_label)
        
        # Update button
        self.update_button = QPushButton("Download & Install Update")
        self.update_button.clicked.connect(self.start_update)
        layout.addWidget(self.update_button)
        
        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
    def start_update(self):
        """Start direct S3 update - Windows optimized"""
        reply = QMessageBox.question(
            self,
            "Download & Install Update",
            "This will download the latest Windows version from S3 and install it.\nOptimized for Windows systems.\n\nThe application will restart automatically.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.update_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Downloading from S3...")
            
            try:
                # Start direct download from S3 - Updater is now embedded!
                self.downloader = UpdateDownloader()
                self.downloader.download_progress.connect(self.on_download_progress)
                self.downloader.download_complete.connect(self.on_download_complete)
                self.downloader.install_complete.connect(self.on_install_complete)
                self.downloader.error.connect(self.on_update_error)
                self.downloader.start()
                
            except Exception as e:
                self.on_update_error(f"Failed to start update: {str(e)}")
    
    def on_download_progress(self, percentage):
        """Update download progress"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(f"Downloading update... {percentage}%")
    
    def on_download_complete(self, file_path):
        """Handle download completion and start installation"""
        self.status_label.setText("Installing update...")
        self.progress_bar.setVisible(False)
        
        # Ask for final confirmation before installation
        reply = QMessageBox.question(
            self,
            "Install Update",
            "Download complete! Install the update now?\n\nThe application will restart automatically.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.status_label.setText("Starting installation...")
            
            # Show final message and immediately start installation
            QMessageBox.information(
                self,
                "Update Starting",
                "Installation will begin now.\nThe application will close and restart automatically.\n\nDo not manually restart the application!"
            )
            
            # Start the installation process and exit immediately
            try:
                self.downloader.install_update(file_path)
                
                # Exit immediately - let the Windows updater handle everything
                self.force_exit()
                
            except Exception as e:
                self.on_update_error(f"Installation failed: {str(e)}")
        else:
            self.status_label.setText("Update cancelled")
            self.update_button.setEnabled(True)
    
    def on_install_complete(self):
        """Handle installation completion - This shouldn't be called with new updater"""
        # The new updater handles everything automatically, so this is just a safety fallback
        self.force_exit()
    
    def force_exit(self):
        """Force exit the application to allow file replacement"""
        try:
            # Clean up downloader thread
            if self.downloader and self.downloader.isRunning():
                self.downloader.quit()
                self.downloader.wait(1000)  # Wait up to 1 second
            
            # Force close the application
            QApplication.quit()
            sys.exit(0)
            
        except Exception as e:
            # Last resort - force terminate
            import os
            os._exit(0)
    
    def restart_application(self):
        """Restart the application - Not needed anymore as updater handles this"""
        # This method is kept for backward compatibility but not used
        # The Windows updater script handles restarting automatically
        pass
    
    def on_update_error(self, error_msg):
        self.status_label.setText("Update failed")
        self.progress_bar.setVisible(False)
        QMessageBox.warning(self, "Update Error", error_msg)
        self.update_button.setEnabled(True)
    
    def closeEvent(self, event):
        """Handle application close event"""
        # Clean up downloader thread if running
        if self.downloader and self.downloader.isRunning():
            self.downloader.quit()
            self.downloader.wait(1000)
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
