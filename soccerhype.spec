# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SoccerHype standalone application
Builds a bundled executable for Windows and macOS
"""

import sys
from pathlib import Path

block_cipher = None

# Determine platform-specific settings
# Note: Using sys.platform here (not platform.system()) because PyInstaller
# is evaluated at build time and sys.platform is more reliable in this context
# sys.platform values: 'win32', 'darwin', 'linux', etc.
is_windows = sys.platform.startswith('win')
is_macos = sys.platform == 'darwin'

# Data files to include
datas = [
    # Include any template files or resources if they exist
    # ('path/to/resource', 'destination/in/bundle')
]

# Binary files (will include FFmpeg if found in binaries/ directory)
binaries = []

# Try to find and include FFmpeg and FFprobe binaries
ffmpeg_binary_dir = Path('binaries')
if ffmpeg_binary_dir.exists():
    if is_windows:
        ffmpeg_exe = ffmpeg_binary_dir / 'ffmpeg.exe'
        ffprobe_exe = ffmpeg_binary_dir / 'ffprobe.exe'
        if ffmpeg_exe.exists():
            binaries.append((str(ffmpeg_exe), 'binaries'))
        if ffprobe_exe.exists():
            binaries.append((str(ffprobe_exe), 'binaries'))
    else:  # macOS/Linux
        ffmpeg_bin = ffmpeg_binary_dir / 'ffmpeg'
        ffprobe_bin = ffmpeg_binary_dir / 'ffprobe'
        if ffmpeg_bin.exists():
            binaries.append((str(ffmpeg_bin), 'binaries'))
        if ffprobe_bin.exists():
            binaries.append((str(ffprobe_bin), 'binaries'))

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'cv2',
    'yaml',
    'pathlib',
    'profile_manager',
]

# Add platform-specific hidden imports
# Note: win32api/win32con are optional and only needed if pywin32 is installed
# SoccerHype works fine without them, but they may be used by some dependencies
if is_windows:
    try:
        import win32api
        hiddenimports.extend([
            'win32api',
            'win32con',
        ])
    except ImportError:
        # pywin32 not installed, skip these imports
        pass

a = Analysis(
    ['soccerhype_gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',  # Exclude unnecessary heavy packages
        'scipy',
        'pandas',
        'numpy.distutils',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Optional icon files (None if not found)
icon_file = None
if is_windows:
    if Path('icon.ico').exists():
        icon_file = 'icon.ico'
else:
    if Path('icon.icns').exists():
        icon_file = 'icon.icns'

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SoccerHype',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SoccerHype',
)

# macOS app bundle
if is_macos:
    # Use icon file if it exists, otherwise None
    macos_icon = 'icon.icns' if Path('icon.icns').exists() else None

    app = BUNDLE(
        coll,
        name='SoccerHype.app',
        icon=macos_icon,
        bundle_identifier='com.soccerhype.app',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHumanReadableCopyright': 'Copyright © 2025',
        },
    )
