@echo off
REM Build script for creating standalone SoccerHype Windows executable
REM Requires: Python 3.9+, PyInstaller, FFmpeg binary

echo ========================================
echo SoccerHype Windows Build Script
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.9 or higher.
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        exit /b 1
    )
)

REM Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)

REM Download FFmpeg if not present
if not exist "binaries\ffmpeg.exe" (
    echo.
    echo FFmpeg not found in binaries directory.
    echo Please download FFmpeg and place ffmpeg.exe in the binaries\ folder.
    echo.
    echo You can download FFmpeg from: https://ffmpeg.org/download.html
    echo Or run: python bundle_ffmpeg.py --platform windows
    echo.
    set /p continue="Continue without FFmpeg bundling? (y/N): "
    if /i not "%continue%"=="y" exit /b 1
) else (
    echo FFmpeg found: binaries\ffmpeg.exe
)

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Run PyInstaller
echo.
echo Building SoccerHype executable...
pyinstaller soccerhype.spec
if errorlevel 1 (
    echo ERROR: Build failed
    exit /b 1
)

REM Copy fonts if available
if exist "C:\Windows\Fonts\DejaVuSans.ttf" (
    echo.
    echo Copying DejaVu fonts...
    if not exist "dist\SoccerHype\fonts" mkdir "dist\SoccerHype\fonts"
    copy "C:\Windows\Fonts\DejaVuSans*.ttf" "dist\SoccerHype\fonts\" >nul 2>&1
)

REM Create README in dist
echo.
echo Creating distribution README...
(
echo SoccerHype - Standalone Windows Application
echo ===========================================
echo.
echo Installation:
echo 1. Extract this folder to your desired location
echo 2. Run SoccerHype.exe
echo.
echo Requirements:
echo - FFmpeg must be bundled or installed system-wide
echo - Approximately 500MB free disk space for video processing
echo.
echo Usage:
echo - Launch SoccerHype.exe to open the main application
echo - Create athlete folders and add video clips
echo - Mark plays interactively
echo - Render professional highlight videos
echo.
echo For support and documentation, visit the project repository.
) > "dist\SoccerHype\README.txt"

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Output location: dist\SoccerHype\
echo Executable: dist\SoccerHype\SoccerHype.exe
echo.
echo To create an installer, use:
echo   - NSIS (Nullsoft Scriptable Install System)
echo   - Inno Setup
echo   - Or zip the dist\SoccerHype folder for distribution
echo.

pause
