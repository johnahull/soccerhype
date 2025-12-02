#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""
FFmpeg bundling helper for SoccerHype standalone packaging
Downloads and prepares FFmpeg binaries for inclusion in the standalone app
"""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

# FFmpeg download URLs (static builds)
# NOTE: These URLs point to latest releases which change frequently.
# Checksum verification is optional but recommended for production use.
# Set FFMPEG_CHECKSUMS below to enable verification.
FFMPEG_URLS = {
    'windows': 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',
    'macos': 'https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip',
    'linux': 'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz',
}

# Optional SHA256 checksums for verification (None = skip verification)
# These should be updated when pinning to specific FFmpeg versions
# To generate: sha256sum <downloaded_file>
FFMPEG_CHECKSUMS = {
    'windows': None,  # Set to SHA256 hash when pinning versions
    'macos': None,
    'linux': None,
}

# Maximum download size (500MB) to prevent disk exhaustion
MAX_DOWNLOAD_SIZE = 500 * 1024 * 1024

def detect_platform():
    """Detect the current platform

    Returns normalized platform name: 'windows', 'macos', or 'linux'
    Uses platform.system() which returns consistent values across Python versions
    """
    system = platform.system()

    # Normalize to lowercase for comparison
    system_lower = system.lower()

    if system_lower == 'darwin':
        return 'macos'
    elif system_lower == 'windows':
        return 'windows'
    elif system_lower == 'linux':
        return 'linux'
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

def download_file(url, destination):
    """Download a file with progress indication and size limit protection"""
    print(f"Downloading from: {url}")
    print(f"Destination: {destination}")

    try:
        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get('Content-Length') or 0)

            # Check size limit to prevent disk exhaustion
            if total_size > MAX_DOWNLOAD_SIZE:
                print(f"\nError: File size ({total_size} bytes) exceeds maximum allowed size ({MAX_DOWNLOAD_SIZE} bytes)")
                return False

            block_size = 8192
            downloaded = 0

            destination.parent.mkdir(parents=True, exist_ok=True)

            with open(destination, 'wb') as f:
                while True:
                    chunk = response.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Also check downloaded size to catch cases where Content-Length is missing
                    if downloaded > MAX_DOWNLOAD_SIZE:
                        print(f"\nError: Downloaded size exceeds maximum allowed size ({MAX_DOWNLOAD_SIZE} bytes)")
                        return False

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')

            print()  # New line after progress
            return True

    except Exception as e:
        print(f"\nError downloading: {e}")
        return False

def verify_checksum(file_path, expected_checksum):
    """Verify SHA256 checksum of a file"""
    if expected_checksum is None:
        print("Note: Checksum verification skipped (no checksum configured)")
        return True

    print("Verifying file checksum...")
    sha256_hash = hashlib.sha256()

    with open(file_path, 'rb') as f:
        # Read in 64k chunks for memory efficiency
        for chunk in iter(lambda: f.read(65536), b''):
            sha256_hash.update(chunk)

    actual_checksum = sha256_hash.hexdigest()

    if actual_checksum.lower() == expected_checksum.lower():
        print(f"Checksum verified: {actual_checksum}")
        return True
    else:
        print(f"ERROR: Checksum mismatch!")
        print(f"  Expected: {expected_checksum}")
        print(f"  Actual:   {actual_checksum}")
        print(f"\nThis may indicate a corrupted download or security issue.")
        print(f"Please verify the download source and try again.")
        return False

def extract_archive(archive_path, extract_dir):
    """Extract archive based on file type with path traversal protection"""
    print(f"Extracting: {archive_path}")

    archive_path = Path(archive_path)
    extract_dir = Path(extract_dir).resolve()
    extract_dir.mkdir(parents=True, exist_ok=True)

    if archive_path.suffix == '.zip':
        import zipfile
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            # Validate each member path to prevent path traversal attacks
            for member in zip_ref.namelist():
                member_path = (extract_dir / member).resolve()
                if not str(member_path).startswith(str(extract_dir)):
                    raise ValueError(f"Attempted path traversal in archive: {member}")
            zip_ref.extractall(extract_dir)
    elif archive_path.suffix in ['.tar', '.xz', '.gz']:
        import tarfile
        with tarfile.open(archive_path, 'r:*') as tar_ref:
            # Filter members to prevent path traversal attacks
            safe_members = []
            for member in tar_ref.getmembers():
                member_path = (extract_dir / member.name).resolve()
                if not str(member_path).startswith(str(extract_dir)):
                    raise ValueError(f"Attempted path traversal in archive: {member.name}")
                safe_members.append(member)
            tar_ref.extractall(extract_dir, members=safe_members)
    else:
        raise ValueError(f"Unsupported archive format: {archive_path.suffix}")

    print("Extraction complete")

def find_ffmpeg_binary(search_dir, platform_name):
    """Find the ffmpeg binary in extracted directory"""
    search_dir = Path(search_dir)

    if platform_name == 'windows':
        pattern = '**/ffmpeg.exe'
    else:
        pattern = '**/ffmpeg'

    # Search for ffmpeg binary
    for ffmpeg_path in search_dir.rglob(pattern):
        if ffmpeg_path.is_file():
            return ffmpeg_path

    return None

def find_ffprobe_binary(search_dir, platform_name):
    """Find the ffprobe binary in extracted directory"""
    search_dir = Path(search_dir)

    if platform_name == 'windows':
        pattern = '**/ffprobe.exe'
    else:
        pattern = '**/ffprobe'

    # Search for ffprobe binary
    for ffprobe_path in search_dir.rglob(pattern):
        if ffprobe_path.is_file():
            return ffprobe_path

    return None

def bundle_ffmpeg(platform_name, output_dir='binaries'):
    """Download and bundle FFmpeg for the specified platform"""
    print(f"Bundling FFmpeg for platform: {platform_name}")

    if platform_name not in FFMPEG_URLS:
        print(f"Error: No FFmpeg download URL configured for {platform_name}")
        return False

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if FFmpeg already exists
    if platform_name == 'windows':
        ffmpeg_dest = output_dir / 'ffmpeg.exe'
        ffprobe_dest = output_dir / 'ffprobe.exe'
    else:
        ffmpeg_dest = output_dir / 'ffmpeg'
        ffprobe_dest = output_dir / 'ffprobe'

    if ffmpeg_dest.exists():
        response = input(f"FFmpeg already exists at {ffmpeg_dest}. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return True

    # Create temporary directory for download with unique name for safety
    import tempfile
    temp_dir = Path(tempfile.mkdtemp(prefix='ffmpeg_download_'))

    try:
        # Determine archive filename
        url = FFMPEG_URLS[platform_name]
        if platform_name == 'windows':
            archive_name = 'ffmpeg.zip'
        elif platform_name == 'macos':
            archive_name = 'ffmpeg.zip'
        else:  # linux
            archive_name = 'ffmpeg.tar.xz'

        archive_path = temp_dir / archive_name

        # Download FFmpeg
        if not download_file(url, archive_path):
            return False

        # Verify checksum if configured
        expected_checksum = FFMPEG_CHECKSUMS.get(platform_name)
        if not verify_checksum(archive_path, expected_checksum):
            print("\nChecksum verification failed. Aborting.")
            return False

        # Extract archive
        extract_dir = temp_dir / 'extracted'
        extract_archive(archive_path, extract_dir)

        # Find FFmpeg binary
        ffmpeg_binary = find_ffmpeg_binary(extract_dir, platform_name)

        if not ffmpeg_binary:
            print("Error: Could not find ffmpeg binary in extracted archive")
            return False

        print(f"Found FFmpeg at: {ffmpeg_binary}")

        # Copy to output directory
        shutil.copy2(ffmpeg_binary, ffmpeg_dest)

        # Make executable on Unix-like systems
        if platform_name in ['macos', 'linux']:
            os.chmod(ffmpeg_dest, 0o755)

        print(f"\nSuccess! FFmpeg bundled at: {ffmpeg_dest}")

        # Also try to find and bundle ffprobe
        ffprobe_binary = find_ffprobe_binary(extract_dir, platform_name)
        if ffprobe_binary:
            print(f"Found FFprobe at: {ffprobe_binary}")
            shutil.copy2(ffprobe_binary, ffprobe_dest)

            # Make executable on Unix-like systems
            if platform_name in ['macos', 'linux']:
                os.chmod(ffprobe_dest, 0o755)

            print(f"FFprobe bundled at: {ffprobe_dest}")
        else:
            print("Note: ffprobe not found in archive (not critical for SoccerHype)")

        # Verify the binary works
        print("\nVerifying FFmpeg binary...")
        try:
            result = subprocess.run([str(ffmpeg_dest), '-version'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("FFmpeg verification successful!")
                print(result.stdout.split('\n')[0])  # Print version line
            else:
                print("Warning: FFmpeg binary may not be working correctly")
        except Exception as e:
            print(f"Warning: Could not verify FFmpeg: {e}")

        return True

    except Exception as e:
        print(f"Error bundling FFmpeg: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Clean up temporary directory
        if temp_dir.exists():
            print("\nCleaning up temporary files...")
            shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    parser = argparse.ArgumentParser(
        description='Download and bundle FFmpeg for SoccerHype packaging'
    )
    parser.add_argument(
        '--platform',
        choices=['windows', 'macos', 'linux', 'auto'],
        default='auto',
        help='Target platform (default: auto-detect)'
    )
    parser.add_argument(
        '--output-dir',
        default='binaries',
        help='Output directory for FFmpeg binary (default: binaries/)'
    )

    args = parser.parse_args()

    try:
        # Detect platform if auto
        if args.platform == 'auto':
            platform_name = detect_platform()
            print(f"Auto-detected platform: {platform_name}")
        else:
            platform_name = args.platform

        # Bundle FFmpeg
        success = bundle_ffmpeg(platform_name, args.output_dir)

        if success:
            print("\n" + "="*50)
            print("FFmpeg bundling completed successfully!")
            print("="*50)
            print(f"\nYou can now run the build script for {platform_name}")
            sys.exit(0)
        else:
            print("\nFFmpeg bundling failed.")
            sys.exit(1)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
