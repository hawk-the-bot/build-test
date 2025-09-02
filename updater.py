#!/usr/bin/env python3
"""
Windows-Focused S3 Update System for Build Test Application

Boss's requirements: 
- Windows primary target
- No bullshit version checking  
- Always download and install from S3
- Dead fucking simple but industrial grade
"""

import sys
import os
import requests
import subprocess
import shutil
import tempfile
import zipfile
from pathlib import Path
from PySide6.QtCore import QThread, Signal


# S3 Configuration - WINDOWS FOCUSED
# Primary target: Windows
S3_URLS = {
    'windows': 'https://your-s3-bucket.s3.amazonaws.com/BuildTestSystem.exe',  # Main Windows build
    'mac': 'https://your-s3-bucket.s3.amazonaws.com/BuildTestSystem-mac.zip'   # Optional Mac support
}


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
        platform = PlatformDetector.get_platform()
        url = S3_URLS.get(platform)
        
        # If no URL for current platform and not Windows, show error
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
    
    @staticmethod
    def is_windows():
        """Check if running on Windows (primary target)"""
        return PlatformDetector.get_platform() == 'windows'


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
                # Primary Windows installation
                self.install_windows(downloaded_file)
            elif self.platform == 'mac':
                # Secondary Mac support
                self.install_mac(downloaded_file)
            else:
                raise Exception("This build system is optimized for Windows. Other platforms have limited support.")
            
            self.install_complete.emit()
            
        except Exception as e:
            raise Exception(f"Installation failed: {str(e)}")


class MacUpdater:
    """Mac-specific update handling"""
    
    @staticmethod
    def install(downloaded_file, temp_dir):
        """Install update on Mac"""
        current_exe = MacUpdater.get_current_executable()
        backup_path = current_exe + ".backup"
        
        file_ext = Path(downloaded_file).suffix.lower()
        
        if file_ext == '.app':
            MacUpdater.install_app_bundle(downloaded_file, current_exe, backup_path)
        elif file_ext == '.dmg':
            MacUpdater.install_from_dmg(downloaded_file, current_exe, backup_path, temp_dir)
        elif file_ext == '.pkg':
            MacUpdater.install_pkg(downloaded_file)
        elif file_ext == '.zip':
            MacUpdater.install_from_zip(downloaded_file, current_exe, backup_path, temp_dir)
        else:
            raise Exception(f"Unsupported Mac update file type: {file_ext}")
    
    @staticmethod
    def get_current_executable():
        """Get current executable path"""
        if getattr(sys, 'frozen', False):
            return sys.executable
        else:
            return os.path.abspath(__file__)
    
    @staticmethod
    def install_app_bundle(app_file, current_exe, backup_path):
        """Install .app bundle"""
        if os.path.exists(current_exe):
            shutil.move(current_exe, backup_path)
        shutil.move(app_file, current_exe)
        os.chmod(current_exe, 0o755)
    
    @staticmethod
    def install_from_dmg(dmg_file, current_exe, backup_path, temp_dir):
        """Install from .dmg file"""
        # Mount DMG
        mount_point = os.path.join(temp_dir, "mount")
        os.makedirs(mount_point, exist_ok=True)
        
        subprocess.run(['hdiutil', 'attach', dmg_file, '-mountpoint', mount_point], check=True)
        
        try:
            # Find .app in mounted volume
            for item in os.listdir(mount_point):
                if item.endswith('.app'):
                    app_path = os.path.join(mount_point, item)
                    if os.path.exists(current_exe):
                        shutil.move(current_exe, backup_path)
                    shutil.copytree(app_path, current_exe)
                    break
        finally:
            # Unmount DMG
            subprocess.run(['hdiutil', 'detach', mount_point])
    
    @staticmethod
    def install_pkg(pkg_file):
        """Install .pkg file (requires admin privileges)"""
        subprocess.run(['sudo', 'installer', '-pkg', pkg_file, '-target', '/'], check=True)
    
    @staticmethod
    def install_from_zip(zip_file, current_exe, backup_path, temp_dir):
        """Install from .zip file"""
        extract_dir = os.path.join(temp_dir, "extract")
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Find executable in extracted files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith('.app') or os.access(os.path.join(root, file), os.X_OK):
                    extracted_exe = os.path.join(root, file)
                    if os.path.exists(current_exe):
                        shutil.move(current_exe, backup_path)
                    shutil.move(extracted_exe, current_exe)
                    os.chmod(current_exe, 0o755)
                    return


class WindowsUpdater:
    """Windows-specific update handling"""
    
    @staticmethod
    def install(downloaded_file, temp_dir):
        """Install update on Windows"""
        current_exe = WindowsUpdater.get_current_executable()
        backup_path = current_exe + ".backup"
        
        file_ext = Path(downloaded_file).suffix.lower()
        
        if file_ext == '.exe':
            WindowsUpdater.install_exe(downloaded_file, current_exe, backup_path, temp_dir)
        elif file_ext == '.msi':
            WindowsUpdater.install_msi(downloaded_file)
        elif file_ext == '.zip':
            WindowsUpdater.install_from_zip(downloaded_file, current_exe, backup_path, temp_dir)
        else:
            raise Exception(f"Unsupported Windows update file type: {file_ext}")
    
    @staticmethod
    def get_current_executable():
        """Get current executable path"""
        if getattr(sys, 'frozen', False):
            return sys.executable
        else:
            return os.path.abspath(__file__)
    
    @staticmethod
    def install_exe(exe_file, current_exe, backup_path, temp_dir):
        """Install .exe file using update script"""
        update_script = os.path.join(temp_dir, "update.bat")
        
        script_content = f'''@echo off
echo Installing update...
timeout /t 2 /nobreak > nul

if exist "{current_exe}" (
    copy "{current_exe}" "{backup_path}"
)

copy "{exe_file}" "{current_exe}"
echo Update installed successfully!

start "" "{current_exe}"
del "%0"
'''
        
        with open(update_script, 'w') as f:
            f.write(script_content)
        
        # Run update script and exit
        subprocess.Popen(update_script, shell=True)
    
    @staticmethod
    def install_msi(msi_file):
        """Install .msi file"""
        subprocess.run(['msiexec', '/i', msi_file, '/quiet'], check=True)
    
    @staticmethod
    def install_from_zip(zip_file, current_exe, backup_path, temp_dir):
        """Install from .zip file"""
        extract_dir = os.path.join(temp_dir, "extract")
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Find executable in extracted files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith('.exe'):
                    extracted_exe = os.path.join(root, file)
                    WindowsUpdater.install_exe(extracted_exe, current_exe, backup_path, temp_dir)
                    return


# Add platform-specific installation to UpdateDownloader
def install_mac(self, downloaded_file):
    """Mac installation"""
    MacUpdater.install(downloaded_file, self.temp_dir)

def install_windows(self, downloaded_file):
    """Windows installation"""
    WindowsUpdater.install(downloaded_file, self.temp_dir)

# Monkey patch the methods
UpdateDownloader.install_mac = install_mac
UpdateDownloader.install_windows = install_windows
