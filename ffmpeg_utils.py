#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""
FFmpeg utility functions for SoccerHype
Handles detection of bundled vs system FFmpeg binaries
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

def get_bundled_ffmpeg_path():
    """
    Get path to bundled FFmpeg binary if running as PyInstaller bundle
    Returns None if not found or not running as bundle
    """
    # Check if running as PyInstaller bundle
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle
        bundle_dir = Path(sys._MEIPASS)

        # Check for FFmpeg in binaries subdirectory
        if platform.system() == 'Windows':
            ffmpeg_path = bundle_dir / 'binaries' / 'ffmpeg.exe'
        else:
            ffmpeg_path = bundle_dir / 'binaries' / 'ffmpeg'

        if ffmpeg_path.exists() and ffmpeg_path.is_file():
            return str(ffmpeg_path)

    # Check for FFmpeg in local binaries directory (development mode)
    if platform.system() == 'Windows':
        local_ffmpeg = Path('binaries') / 'ffmpeg.exe'
    else:
        local_ffmpeg = Path('binaries') / 'ffmpeg'

    if local_ffmpeg.exists() and local_ffmpeg.is_file():
        return str(local_ffmpeg.resolve())

    return None

def get_bundled_ffprobe_path():
    """
    Get path to bundled FFprobe binary if running as PyInstaller bundle
    Returns None if not found or not running as bundle
    """
    # Check if running as PyInstaller bundle
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle
        bundle_dir = Path(sys._MEIPASS)

        # Check for FFprobe in binaries subdirectory
        if platform.system() == 'Windows':
            ffprobe_path = bundle_dir / 'binaries' / 'ffprobe.exe'
        else:
            ffprobe_path = bundle_dir / 'binaries' / 'ffprobe'

        if ffprobe_path.exists() and ffprobe_path.is_file():
            return str(ffprobe_path)

    # Check for FFprobe in local binaries directory (development mode)
    if platform.system() == 'Windows':
        local_ffprobe = Path('binaries') / 'ffprobe.exe'
    else:
        local_ffprobe = Path('binaries') / 'ffprobe'

    if local_ffprobe.exists() and local_ffprobe.is_file():
        return str(local_ffprobe.resolve())

    return None

def get_system_ffmpeg_path():
    """
    Get path to system-installed FFmpeg binary
    Returns None if not found
    """
    ffmpeg_path = shutil.which('ffmpeg')
    return ffmpeg_path

def get_system_ffprobe_path():
    """
    Get path to system-installed FFprobe binary
    Returns None if not found
    """
    ffprobe_path = shutil.which('ffprobe')
    return ffprobe_path

def get_ffmpeg_path():
    """
    Get FFmpeg binary path, preferring bundled version over system version
    Returns path as string, or None if not found

    Priority order:
    1. Bundled FFmpeg (in PyInstaller bundle or local binaries/)
    2. System FFmpeg (in PATH)
    """
    # Try bundled first
    bundled = get_bundled_ffmpeg_path()
    if bundled:
        return bundled

    # Fall back to system
    system = get_system_ffmpeg_path()
    if system:
        return system

    return None

def get_ffprobe_path():
    """
    Get FFprobe binary path, preferring bundled version over system version
    Returns path as string, or None if not found

    Priority order:
    1. Bundled FFprobe (in PyInstaller bundle or local binaries/)
    2. System FFprobe (in PATH)
    """
    # Try bundled first
    bundled = get_bundled_ffprobe_path()
    if bundled:
        return bundled

    # Fall back to system
    system = get_system_ffprobe_path()
    if system:
        return system

    return None

def verify_ffmpeg(ffmpeg_path=None):
    """
    Verify that FFmpeg is available and working

    Args:
        ffmpeg_path: Path to FFmpeg binary (optional, will auto-detect if None)

    Returns:
        tuple: (success: bool, version_string: str, error_message: str)
    """
    if ffmpeg_path is None:
        ffmpeg_path = get_ffmpeg_path()

    if ffmpeg_path is None:
        return (False, None, "FFmpeg not found in bundle or system PATH")

    try:
        result = subprocess.run(
            [ffmpeg_path, '-version'],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )

        if result.returncode == 0:
            # Extract version from first line
            version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
            return (True, version_line, None)
        else:
            return (False, None, f"FFmpeg returned error code {result.returncode}")

    except FileNotFoundError:
        return (False, None, f"FFmpeg binary not found at: {ffmpeg_path}")
    except subprocess.TimeoutExpired:
        return (False, None, "FFmpeg verification timed out")
    except Exception as e:
        return (False, None, f"Error verifying FFmpeg: {str(e)}")

def get_ffmpeg_info():
    """
    Get detailed information about FFmpeg installation

    Returns:
        dict with keys: path, is_bundled, version, error
    """
    bundled_path = get_bundled_ffmpeg_path()
    system_path = get_system_ffmpeg_path()
    active_path = get_ffmpeg_path()

    info = {
        'bundled_path': bundled_path,
        'system_path': system_path,
        'active_path': active_path,
        'is_bundled': active_path == bundled_path if active_path else False,
        'version': None,
        'error': None
    }

    if active_path:
        success, version, error = verify_ffmpeg(active_path)
        info['version'] = version
        info['error'] = error
    else:
        info['error'] = "FFmpeg not found"

    return info

def ensure_ffmpeg_available():
    """
    Check if FFmpeg is available, raise RuntimeError if not
    Returns the path to FFmpeg if successful
    """
    ffmpeg_path = get_ffmpeg_path()

    if ffmpeg_path is None:
        raise RuntimeError(
            "FFmpeg not found. Please install FFmpeg or ensure it's in your PATH.\n"
            "Download from: https://ffmpeg.org/download.html"
        )

    success, version, error = verify_ffmpeg(ffmpeg_path)
    if not success:
        raise RuntimeError(f"FFmpeg verification failed: {error}")

    return ffmpeg_path

def print_ffmpeg_info():
    """Print detailed FFmpeg information for debugging"""
    info = get_ffmpeg_info()

    print("FFmpeg Detection Information:")
    print("-" * 50)
    print(f"Bundled FFmpeg: {info['bundled_path'] or 'Not found'}")
    print(f"System FFmpeg:  {info['system_path'] or 'Not found'}")
    print(f"Active FFmpeg:  {info['active_path'] or 'Not found'}")
    print(f"Using bundled:  {info['is_bundled']}")
    print(f"Version:        {info['version'] or 'N/A'}")
    if info['error']:
        print(f"Error:          {info['error']}")
    print("-" * 50)

if __name__ == '__main__':
    # Test FFmpeg detection
    print_ffmpeg_info()
