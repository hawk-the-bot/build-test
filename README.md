# Build Test System - Windows Edition

A Windows-focused Python application with PySide6 GUI for testing build systems using Nuitka.

**Primary Target: Windows** | Secondary: Mac

## Features

- Simple Hello World GUI
- Version display from file
- Auto-update system via GitHub releases
- Cross-platform builds (Mac/Windows)

## Requirements

- Python 3.8+
- PySide6
- Nuitka
- requests

## Installation

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

## Running

```bash
# Activate virtual environment first
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# Run the app
python main.py
```

## Building (Windows Primary)

The build scripts automatically handle virtual environment setup.

### Windows (Primary Target)
```bash
build_windows.bat
```

### Mac (Secondary Support)  
```bash
./build_mac.sh
```

**Windows build script features:**
- Optimized for Windows development
- Creates Windows-specific executable
- Handles Windows-specific Nuitka flags
- Automatic venv setup
- Windows installer creation

## Windows-Focused S3 Update System

**Windows First**: Optimized for Windows with secondary Mac support. No version checking bullshit.

### ✨ Features
- **Windows optimized**: Primary target is Windows systems
- **Direct S3 download**: No GitHub API calls
- **Always update**: No version comparison nonsense
- **Windows .exe handling**: Seamless Windows executable updates
- **Progress bar**: Visual download progress
- **Auto-install**: Windows-optimized installation process
- **Auto-restart**: Clean Windows app restart
- **Backup system**: Creates backup before installation

### 🔄 Simple Update Flow
1. User clicks "Download & Install Update"
2. Confirms action
3. Downloads directly from S3 with progress
4. Asks final confirmation: "Install update now?"
5. Installs update and creates backup
6. Shows success message and restarts app

### 🎯 S3 Configuration (Windows Priority)
Update the S3 URLs in `updater.py`:

```python
S3_URLS = {
    'windows': 'https://your-s3-bucket.s3.amazonaws.com/BuildTestSystem.exe',    # Main Windows build
    'mac': 'https://your-s3-bucket.s3.amazonaws.com/BuildTestSystem-mac.zip'    # Optional Mac support  
}
```

**Note**: Windows is the primary target. The system will prioritize Windows builds.

### 🛡️ Safety Features
- Creates backup before installation
- User confirmation at each step
- Platform-specific installation logic
- Robust error handling and rollback

## File Structure

- `main.py` - Main GUI application (clean and simple)
- `updater.py` - Auto-update system (platform-specific)
- `version.txt` - Version file
- `requirements.txt` - Python dependencies
- `build_mac.sh` - Mac build script
- `build_windows.bat` - Windows build script

### Platform-Specific Update Support

**Windows (Primary):**
- `.exe` executables (main format)
- `.msi` installers  
- `.zip` archives
- Optimized Windows installation process

**Mac (Secondary):**
- `.app` bundles
- `.dmg` disk images
- `.zip` archives
- Basic Mac support

## Build Output

Builds are created in the `build/` directory with installer packages in `build/installer/`.