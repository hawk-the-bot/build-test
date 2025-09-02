#!/usr/bin/env python3

import sys
import os
import subprocess
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QMessageBox, QProgressBar
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from updater import UpdateDownloader

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
        hello_label = QLabel("Hello Windows!")
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
                # Start direct download from S3
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
            self.downloader.install_update(file_path)
        else:
            self.status_label.setText("Update cancelled")
            self.update_button.setEnabled(True)
    
    def on_install_complete(self):
        """Handle installation completion"""
        self.status_label.setText("Update installed! Restarting...")
        
        # Show success message
        QMessageBox.information(
            self,
            "Update Complete",
            "Update installed successfully!\nThe application will now restart."
        )
        
        # Restart the application
        self.restart_application()
    
    def restart_application(self):
        """Restart the application"""
        try:
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                executable = sys.executable
                subprocess.Popen([executable])
            else:
                # Running as Python script
                subprocess.Popen([sys.executable, __file__])
            
            # Exit current instance
            QApplication.quit()
            
        except Exception as e:
            QMessageBox.critical(self, "Restart Failed", f"Could not restart application: {str(e)}")
            self.status_label.setText("Update complete - please restart manually")
            self.update_button.setEnabled(True)
    
    def on_update_error(self, error_msg):
        self.status_label.setText("Update failed")
        self.progress_bar.setVisible(False)
        QMessageBox.warning(self, "Update Error", error_msg)
        self.update_button.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
