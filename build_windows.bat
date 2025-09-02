@echo off
REM Windows Build Script for Build Test System - Windows Edition
REM Optimized for Windows development - Primary target platform
REM Dead simple but industrial grade

echo Starting Windows build...

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Create and activate venv if not exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment and installing requirements...
call venv\Scripts\activate
pip install -r requirements.txt

REM Clean previous build
echo Cleaning previous build...
if exist build rmdir /s /q build
if exist main.dist rmdir /s /q main.dist
if exist main.build rmdir /s /q main.build

REM Check MSVC availability and set compiler flags
echo Checking for Microsoft Visual C++ compiler...
where cl.exe >nul 2>&1
if errorlevel 1 (
    echo WARNING: MSVC compiler not found in PATH
    echo Using MinGW64 fallback for fast compilation...
    set COMPILER_FLAGS=--mingw64
    set COMPILER_NAME=MinGW64
) else (
    echo SUCCESS: MSVC compiler found - using optimal MSVC!
    set COMPILER_FLAGS=--msvc=latest
    set COMPILER_NAME=MSVC
)

REM Build with Nuitka - Windows Optimized
echo Building with Nuitka (Windows Edition) using %COMPILER_NAME%...
call venv\Scripts\activate
python -m nuitka ^
    --standalone ^
    --enable-plugin=pyside6 ^
    --windows-console-mode=disable ^
    --windows-uac-admin ^
    --windows-company-name="Build Test Systems" ^
    --windows-product-name="Build Test System" ^
    --windows-file-version=1.0.0.0 ^
    --windows-product-version=1.0.0.0 ^
    --windows-file-description="Windows-focused build test application" ^
    %COMPILER_FLAGS% ^
    --include-data-file=version.txt=version.txt ^
    --output-filename=BuildTestSystem.exe ^
    --output-dir=build ^
    main.py

REM Check if build was successful
if %errorlevel% equ 0 (
    echo Windows build successful using %COMPILER_NAME%!
    echo Primary Windows executable created at: build\BuildTestSystem.exe
    
    REM Create Windows installer structure
    if not exist build\installer mkdir build\installer
    copy build\BuildTestSystem.exe build\installer\
    
    REM Create Windows-specific installer files
    echo Creating Windows installer package...
    if not exist build\installer\README.txt (
        echo Build Test System - Windows Edition > build\installer\README.txt
        echo. >> build\installer\README.txt
        echo This is the Windows-optimized version. >> build\installer\README.txt
        echo Run BuildTestSystem.exe to start the application. >> build\installer\README.txt
    )
    
    echo Windows installer package created at: build\installer\
    echo Ready for S3 upload: build\BuildTestSystem.exe
) else (
    echo Windows build failed!
    pause
    exit /b 1
)

echo Windows build completed successfully!
echo Primary platform build ready for distribution.
pause
