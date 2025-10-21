# SoccerHype Standalone Packaging Guide

This document provides complete instructions for creating standalone executables of SoccerHype for Windows and macOS distribution.

## Overview

SoccerHype can be packaged as a standalone application using PyInstaller, allowing users to run the application without installing Python or managing dependencies.

## Prerequisites

### All Platforms
- Python 3.9 or higher
- Git (for version control)
- 500MB+ free disk space

### Windows-Specific
- Windows 10 or later
- Visual Studio Build Tools (for some dependencies)

### macOS-Specific
- macOS 10.13 (High Sierra) or later
- Xcode Command Line Tools

## Quick Start

### Windows

```batch
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Download and bundle FFmpeg (optional but recommended)
python bundle_ffmpeg.py --platform windows

# 3. Build the standalone executable
build_windows.bat
```

The output will be in `dist/SoccerHype/SoccerHype.exe`

### macOS

```bash
# 1. Install Python dependencies
pip3 install -r requirements.txt

# 2. Download and bundle FFmpeg (optional but recommended)
python3 bundle_ffmpeg.py --platform macos

# 3. Build the standalone application
./build_macos.sh
```

The output will be in `dist/SoccerHype.app`

## Detailed Instructions

### Step 1: Prepare Your Environment

#### Install PyInstaller
```bash
pip install pyinstaller
```

#### Verify FFmpeg Installation
SoccerHype requires FFmpeg for video processing. You have two options:

**Option A: Bundle FFmpeg (Recommended for Distribution)**
```bash
# Automatically downloads and prepares FFmpeg for bundling
python bundle_ffmpeg.py --platform auto
```

**Option B: Use System FFmpeg**
Users will need to install FFmpeg separately. The application will detect system FFmpeg automatically.

#### FFmpeg Checksum Verification (Production Builds)

For production releases, it's strongly recommended to enable checksum verification to ensure FFmpeg binaries haven't been tampered with:

1. **Download FFmpeg and get its checksum:**
   ```bash
   # Download and compute checksum
   python bundle_ffmpeg.py --platform auto
   sha256sum binaries/ffmpeg  # Linux/macOS
   # Or on Windows PowerShell:
   # Get-FileHash binaries\ffmpeg.exe -Algorithm SHA256
   ```

2. **Update checksums in bundle_ffmpeg.py:**
   ```python
   FFMPEG_CHECKSUMS = {
       'windows': 'abc123...',  # Replace with actual SHA256 hash
       'macos': 'def456...',
       'linux': 'ghi789...',
   }
   ```

3. **Re-run bundling to verify:**
   ```bash
   python bundle_ffmpeg.py --platform auto
   # Should print "Checksum verified: abc123..."
   ```

**Note:** The bundling script automatically includes both FFmpeg and FFprobe when available. FFprobe is not critical for SoccerHype functionality but may be useful for debugging video files.

### Step 2: Build the Application

#### Windows Build Process

1. **Run the build script:**
   ```batch
   build_windows.bat
   ```

2. **What the script does:**
   - Installs Python dependencies
   - Checks for bundled FFmpeg (prompts if missing)
   - Runs PyInstaller with the spec file
   - Copies required fonts
   - Creates README in distribution folder

3. **Output:**
   - Folder: `dist/SoccerHype/`
   - Executable: `dist/SoccerHype/SoccerHype.exe`
   - Size: ~200-400MB (depending on bundled components)

#### macOS Build Process

1. **Make the script executable (first time only):**
   ```bash
   chmod +x build_macos.sh
   ```

2. **Run the build script:**
   ```bash
   ./build_macos.sh
   ```

3. **What the script does:**
   - Installs Python dependencies
   - Checks for bundled FFmpeg
   - Runs PyInstaller with the spec file
   - Copies fonts from system
   - Creates application bundle

4. **Output:**
   - Application: `dist/SoccerHype.app`
   - Size: ~200-400MB

### Step 3: Test the Standalone Application

#### Windows Testing
```batch
cd dist\SoccerHype
SoccerHype.exe
```

#### macOS Testing
```bash
open dist/SoccerHype.app
```

**Test checklist:**
- [ ] Application launches without errors
- [ ] FFmpeg is detected (check in application logs)
- [ ] Can create new athlete folder
- [ ] Can mark plays on a test video
- [ ] Can render a highlight video
- [ ] Fonts display correctly in output

### Step 4: Create Installer (Optional)

#### Windows Installer

Use **Inno Setup** or **NSIS** to create an installer:

**Inno Setup Example:**
1. Download Inno Setup from https://jrsoftware.org/isinfo.php
2. Create a script file `soccerhype_installer.iss`:

```ini
[Setup]
AppName=SoccerHype
AppVersion=1.0.0
DefaultDirName={pf}\SoccerHype
DefaultGroupName=SoccerHype
OutputDir=installers
OutputBaseFilename=SoccerHype-Setup
Compression=lzma2
SolidCompression=yes

[Files]
Source: "dist\SoccerHype\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\SoccerHype"; Filename: "{app}\SoccerHype.exe"
Name: "{commondesktop}\SoccerHype"; Filename: "{app}\SoccerHype.exe"

[Run]
Filename: "{app}\SoccerHype.exe"; Description: "Launch SoccerHype"; Flags: postinstall nowait skipifsilent
```

3. Compile with Inno Setup Compiler

#### macOS DMG Installer

Create a DMG disk image for easy distribution:

```bash
hdiutil create -volname "SoccerHype" \
  -srcfolder dist/SoccerHype.app \
  -ov -format UDZO \
  dist/SoccerHype.dmg
```

For a more polished DMG with custom background and layout, use **create-dmg**:
```bash
brew install create-dmg
create-dmg \
  --volname "SoccerHype" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --app-drop-link 600 185 \
  "dist/SoccerHype.dmg" \
  "dist/SoccerHype.app"
```

### Step 5: Code Signing (Recommended for Distribution)

#### Windows Code Signing
Requires a code signing certificate from a trusted CA:

```powershell
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist\SoccerHype\SoccerHype.exe
```

#### macOS Code Signing
Requires an Apple Developer account:

```bash
# Sign the application
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  --options runtime \
  dist/SoccerHype.app

# Notarize with Apple (required for macOS 10.15+)
xcrun altool --notarize-app \
  --primary-bundle-id "com.soccerhype.app" \
  --username "your@email.com" \
  --password "@keychain:AC_PASSWORD" \
  --file dist/SoccerHype.dmg

# Staple the notarization ticket
xcrun stapler staple dist/SoccerHype.app
```

## Advanced Configuration

### Customizing the Build

Edit `soccerhype.spec` to customize the build:

```python
# Add custom data files
datas = [
    ('templates', 'templates'),  # Include template files
    ('docs', 'docs'),            # Include documentation
]

# Add custom icons
icon='path/to/custom_icon.ico'  # Windows
icon='path/to/custom_icon.icns'  # macOS

# Exclude unnecessary modules
excludes = [
    'matplotlib',
    'scipy',
    'pandas',
]
```

### Optimizing Build Size

1. **Remove unnecessary packages:**
   Edit the `excludes` list in `soccerhype.spec`

2. **Use UPX compression:**
   PyInstaller uses UPX by default. To disable:
   ```python
   upx=False  # In EXE() and COLLECT()
   ```

3. **Strip debug symbols (macOS/Linux):**
   ```python
   strip=True  # In EXE()
   ```

### Bundling Additional Resources

To include fonts, templates, or other resources:

```python
# In soccerhype.spec
datas = [
    ('fonts/*.ttf', 'fonts'),
    ('templates/*.json', 'templates'),
]
```

## Troubleshooting

### Common Issues

**Issue: "FFmpeg not found" error**
- Solution: Run `python bundle_ffmpeg.py` or ensure system FFmpeg is installed
- Verify with: `python ffmpeg_utils.py`

**Issue: "DLL load failed" on Windows**
- Solution: Install Visual C++ Redistributable
- Download from: https://support.microsoft.com/en-us/help/2977003/

**Issue: "Application damaged" on macOS**
- Solution: Code sign the application or allow in System Preferences → Security & Privacy
- Quick fix: `xattr -cr dist/SoccerHype.app`

**Issue: Large file size (>500MB)**
- Solution: Exclude unnecessary packages in spec file
- Check: `pyinstaller --log-level DEBUG` for included modules

**Issue: Slow startup time**
- Solution: Use one-folder mode instead of one-file mode (default)
- For one-file: Change `EXE(... exclude_binaries=False)`

### Debug Mode

To debug packaging issues:

```bash
# Run with debug logging
pyinstaller --log-level DEBUG soccerhype.spec

# Test in development
python soccerhype_gui.py

# Verify FFmpeg detection
python ffmpeg_utils.py
```

### Platform-Specific Issues

#### Windows
- **Antivirus false positives:** Submit executable to antivirus vendors for whitelisting
- **Missing DLLs:** Use Dependency Walker to identify missing dependencies
- **Permission errors:** Run as administrator during development

#### macOS
- **Gatekeeper blocking:** Code sign or right-click → Open
- **Missing frameworks:** Check with `otool -L dist/SoccerHype.app/Contents/MacOS/SoccerHype`
- **Retina display issues:** Add `NSHighResolutionCapable=True` to Info.plist

## Distribution Checklist

Before distributing your packaged application:

- [ ] Test on clean system without Python installed
- [ ] Verify FFmpeg functionality
- [ ] Test all features (create athlete, mark plays, render)
- [ ] Check file permissions
- [ ] Verify icon displays correctly
- [ ] Test with different video formats
- [ ] Ensure README and license files are included
- [ ] Code sign application (if distributing publicly)
- [ ] Create installer (optional but recommended)
- [ ] Test installer on clean system
- [ ] Document system requirements
- [ ] Prepare release notes

## Build Sizes Reference

| Platform | Mode | FFmpeg Bundled | Approximate Size |
|----------|------|---------------|------------------|
| Windows  | Folder | Yes | ~350-400MB |
| Windows  | Folder | No | ~200-250MB |
| macOS    | App | Yes | ~350-400MB |
| macOS    | App | No | ~200-250MB |

## System Requirements for End Users

### Windows
- Windows 10 or later (64-bit)
- 500MB free disk space for application
- Additional space for video processing (varies by project)
- 4GB RAM minimum, 8GB recommended

### macOS
- macOS 10.13 (High Sierra) or later
- 500MB free disk space for application
- Additional space for video processing (varies by project)
- 4GB RAM minimum, 8GB recommended

## Continuous Integration

### GitHub Actions Example

```yaml
name: Build Standalone
on: [push, pull_request]
jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: python bundle_ffmpeg.py --platform windows
      - run: build_windows.bat
      - uses: actions/upload-artifact@v2
        with:
          name: soccerhype-windows
          path: dist/SoccerHype/

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip3 install -r requirements.txt
      - run: python3 bundle_ffmpeg.py --platform macos
      - run: chmod +x build_macos.sh && ./build_macos.sh
      - uses: actions/upload-artifact@v2
        with:
          name: soccerhype-macos
          path: dist/SoccerHype.app/
```

## Support

For issues with packaging:
1. Check the troubleshooting section above
2. Run `python ffmpeg_utils.py` to verify FFmpeg detection
3. Review PyInstaller logs in `build/` directory
4. Check project issues on GitHub

## Additional Resources

- **PyInstaller Documentation:** https://pyinstaller.readthedocs.io/
- **FFmpeg Downloads:** https://ffmpeg.org/download.html
- **Inno Setup:** https://jrsoftware.org/isinfo.php
- **create-dmg:** https://github.com/andreyvit/create-dmg
- **Code Signing Guide:** https://developer.apple.com/support/code-signing/
