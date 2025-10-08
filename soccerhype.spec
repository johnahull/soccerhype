# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SoccerHype standalone application
Builds a bundled executable for Windows and macOS
"""

import sys
from pathlib import Path

block_cipher = None

# Determine platform-specific settings
is_windows = sys.platform.startswith('win')
is_macos = sys.platform == 'darwin'

# Data files to include
datas = [
    # Include any template files or resources if they exist
    # ('path/to/resource', 'destination/in/bundle')
]

# Binary files (will include FFmpeg if found in binaries/ directory)
binaries = []

# Try to find and include FFmpeg binary
ffmpeg_binary_dir = Path('binaries')
if ffmpeg_binary_dir.exists():
    if is_windows:
        ffmpeg_exe = ffmpeg_binary_dir / 'ffmpeg.exe'
        if ffmpeg_exe.exists():
            binaries.append((str(ffmpeg_exe), 'binaries'))
    else:  # macOS/Linux
        ffmpeg_bin = ffmpeg_binary_dir / 'ffmpeg'
        if ffmpeg_bin.exists():
            binaries.append((str(ffmpeg_bin), 'binaries'))

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
if is_windows:
    hiddenimports.extend([
        'win32api',
        'win32con',
    ])

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
    icon='icon.ico' if is_windows else 'icon.icns',  # Add icons if available
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
    app = BUNDLE(
        coll,
        name='SoccerHype.app',
        icon='icon.icns',  # Add macOS icon if available
        bundle_identifier='com.soccerhype.app',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHumanReadableCopyright': 'Copyright © 2025',
        },
    )
