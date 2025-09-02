#!/bin/bash

# Mac Build Script for Build Test System
# Dead simple Nuitka build

echo "Starting Mac build..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed"
    exit 1
fi

# Create and activate venv if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment and installing requirements..."
source venv/bin/activate
pip install -r requirements.txt

# Clean previous build
echo "Cleaning previous build..."
rm -rf build/
rm -rf main.dist/
rm -rf main.build/

# Build with Nuitka (using venv python)
echo "Building with Nuitka..."
source venv/bin/activate
python -m nuitka \
    --standalone \
    --onefile \
    --enable-plugin=pyside6 \
    --macos-create-app-bundle \
    --include-data-file=version.txt=version.txt \
    --output-filename=BuildTestSystem \
    --output-dir=build \
    main.py

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "Build successful!"
    echo "Executable created at: build/BuildTestSystem.app"
    
    # Create a simple installer structure
    mkdir -p build/installer
    cp -r build/BuildTestSystem.app build/installer/
    echo "Installer package created at: build/installer/"
else
    echo "Build failed!"
    exit 1
fi

echo "Mac build completed!"
