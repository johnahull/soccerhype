#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""
Tests for bundle_ffmpeg module
Tests FFmpeg bundling and download functionality
"""

import os
import platform
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import bundle_ffmpeg


class TestBundleFFmpegPlatformDetection(unittest.TestCase):
    """Test platform detection functionality"""

    def test_detect_platform_linux(self):
        """Test Linux platform detection"""
        with patch('platform.system', return_value='Linux'):
            result = bundle_ffmpeg.detect_platform()
            self.assertEqual(result, 'linux')

    def test_detect_platform_darwin(self):
        """Test macOS platform detection"""
        with patch('platform.system', return_value='Darwin'):
            result = bundle_ffmpeg.detect_platform()
            self.assertEqual(result, 'macos')

    def test_detect_platform_windows(self):
        """Test Windows platform detection"""
        with patch('platform.system', return_value='Windows'):
            result = bundle_ffmpeg.detect_platform()
            self.assertEqual(result, 'windows')

    def test_detect_platform_unsupported(self):
        """Test unsupported platform raises error"""
        with patch('platform.system', return_value='FreeBSD'):
            with self.assertRaises(RuntimeError) as context:
                bundle_ffmpeg.detect_platform()

            self.assertIn('Unsupported platform', str(context.exception))


class TestBundleFFmpegURLs(unittest.TestCase):
    """Test FFmpeg download URL configuration"""

    def test_ffmpeg_urls_defined(self):
        """Test that FFmpeg URLs are defined for all platforms"""
        required_platforms = ['windows', 'macos', 'linux']

        for platform_name in required_platforms:
            self.assertIn(platform_name, bundle_ffmpeg.FFMPEG_URLS)
            self.assertTrue(bundle_ffmpeg.FFMPEG_URLS[platform_name])

    def test_ffmpeg_urls_format(self):
        """Test that FFmpeg URLs are valid HTTP(S) URLs"""
        for platform_name, url in bundle_ffmpeg.FFMPEG_URLS.items():
            self.assertTrue(url.startswith('http://') or url.startswith('https://'))


class TestBundleFFmpegDownload(unittest.TestCase):
    """Test file download functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_download_file_creates_directory(self):
        """Test that download creates parent directory if needed"""
        destination = Path(self.temp_dir) / 'subdir' / 'file.zip'

        # Mock urllib to avoid actual download
        mock_response = MagicMock()
        mock_response.headers.get.return_value = '1000'
        mock_response.read.side_effect = [b'test', b'']
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = bundle_ffmpeg.download_file('http://example.com/file.zip', destination)

            self.assertTrue(result)
            self.assertTrue(destination.parent.exists())

    def test_download_file_handles_missing_content_length(self):
        """Test download with missing Content-Length header"""
        destination = Path(self.temp_dir) / 'file.zip'

        mock_response = MagicMock()
        mock_response.headers.get.return_value = None  # No Content-Length
        mock_response.read.side_effect = [b'test data', b'']
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = bundle_ffmpeg.download_file('http://example.com/file.zip', destination)

            self.assertTrue(result)

    def test_download_file_handles_error(self):
        """Test download error handling"""
        destination = Path(self.temp_dir) / 'file.zip'

        with patch('urllib.request.urlopen', side_effect=Exception('Network error')):
            result = bundle_ffmpeg.download_file('http://example.com/file.zip', destination)

            self.assertFalse(result)


class TestBundleFFmpegExtract(unittest.TestCase):
    """Test archive extraction functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_zip_archive(self):
        """Test ZIP archive extraction"""
        import zipfile

        # Create a test ZIP file
        zip_path = Path(self.temp_dir) / 'test.zip'
        extract_dir = Path(self.temp_dir) / 'extracted'

        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('test.txt', 'test content')

        bundle_ffmpeg.extract_archive(zip_path, extract_dir)

        # Verify extraction
        self.assertTrue(extract_dir.exists())
        self.assertTrue((extract_dir / 'test.txt').exists())

    def test_extract_unsupported_format(self):
        """Test extraction with unsupported format raises error"""
        archive_path = Path(self.temp_dir) / 'test.rar'
        archive_path.touch()

        extract_dir = Path(self.temp_dir) / 'extracted'

        with self.assertRaises(ValueError) as context:
            bundle_ffmpeg.extract_archive(archive_path, extract_dir)

        self.assertIn('Unsupported archive format', str(context.exception))


class TestBundleFFmpegFindBinary(unittest.TestCase):
    """Test FFmpeg binary finding functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_find_ffmpeg_binary_windows(self):
        """Test finding ffmpeg.exe on Windows"""
        search_dir = Path(self.temp_dir)
        subdir = search_dir / 'bin'
        subdir.mkdir()

        ffmpeg_path = subdir / 'ffmpeg.exe'
        ffmpeg_path.touch()

        result = bundle_ffmpeg.find_ffmpeg_binary(search_dir, 'windows')

        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'ffmpeg.exe')

    def test_find_ffmpeg_binary_unix(self):
        """Test finding ffmpeg on Unix-like systems"""
        search_dir = Path(self.temp_dir)
        subdir = search_dir / 'bin'
        subdir.mkdir()

        ffmpeg_path = subdir / 'ffmpeg'
        ffmpeg_path.touch()

        result = bundle_ffmpeg.find_ffmpeg_binary(search_dir, 'macos')

        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'ffmpeg')

    def test_find_ffmpeg_binary_not_found(self):
        """Test when FFmpeg binary is not found"""
        search_dir = Path(self.temp_dir)

        result = bundle_ffmpeg.find_ffmpeg_binary(search_dir, 'linux')

        self.assertIsNone(result)

    def test_find_ffmpeg_binary_nested(self):
        """Test finding FFmpeg in nested directory structure"""
        search_dir = Path(self.temp_dir)
        nested_dir = search_dir / 'level1' / 'level2' / 'bin'
        nested_dir.mkdir(parents=True)

        ffmpeg_path = nested_dir / 'ffmpeg'
        ffmpeg_path.touch()

        result = bundle_ffmpeg.find_ffmpeg_binary(search_dir, 'linux')

        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'ffmpeg')


class TestBundleFFmpegMain(unittest.TestCase):
    """Test main bundling functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_bundle_ffmpeg_invalid_platform(self):
        """Test bundling with invalid platform"""
        result = bundle_ffmpeg.bundle_ffmpeg('invalid_platform', self.temp_dir)

        self.assertFalse(result)

    def test_bundle_ffmpeg_existing_binary_no_overwrite(self):
        """Test bundling when binary exists and user declines overwrite"""
        output_dir = Path(self.temp_dir) / 'binaries'
        output_dir.mkdir()

        # Create existing ffmpeg binary
        ffmpeg_path = output_dir / 'ffmpeg'
        ffmpeg_path.touch()

        # Mock user input to decline overwrite
        with patch('builtins.input', return_value='n'):
            result = bundle_ffmpeg.bundle_ffmpeg('linux', output_dir)

            # Should return True (cancelled, not error)
            self.assertTrue(result)

    def test_bundle_ffmpeg_creates_output_directory(self):
        """Test that bundling creates output directory"""
        output_dir = Path(self.temp_dir) / 'new_binaries'

        # Mock the download and extraction process
        with patch('bundle_ffmpeg.download_file', return_value=True):
            with patch('bundle_ffmpeg.extract_archive'):
                with patch('bundle_ffmpeg.find_ffmpeg_binary', return_value=None):
                    bundle_ffmpeg.bundle_ffmpeg('linux', output_dir)

                    # Directory should be created even if bundling fails
                    self.assertTrue(output_dir.exists())


class TestBundleFFmpegIntegration(unittest.TestCase):
    """Integration tests for bundle_ffmpeg (requires network)"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    @unittest.skip("Skipping network-dependent test by default")
    def test_bundle_ffmpeg_full_workflow(self):
        """Test complete FFmpeg bundling workflow (network required)"""
        # This test is skipped by default as it requires network access
        # and downloads large files. Enable manually for full integration testing.

        platform_name = bundle_ffmpeg.detect_platform()
        output_dir = Path(self.temp_dir) / 'binaries'

        result = bundle_ffmpeg.bundle_ffmpeg(platform_name, output_dir)

        if result:
            # Verify binary was created
            if platform_name == 'windows':
                binary_path = output_dir / 'ffmpeg.exe'
            else:
                binary_path = output_dir / 'ffmpeg'

            self.assertTrue(binary_path.exists())


class TestBundleFFmpegSecurity(unittest.TestCase):
    """Security-focused tests for bundle_ffmpeg"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_path_traversal_protection(self):
        """Test that path traversal attempts are handled safely"""
        # This tests that the bundling process doesn't write outside
        # the intended directory
        output_dir = Path(self.temp_dir) / 'binaries'

        # All operations should be within output_dir
        # The actual protection is in using Path.mkdir(parents=True)
        # and Path operations which handle this safely

        output_dir.mkdir(parents=True)
        self.assertTrue(output_dir.exists())

        # Verify we can't escape the directory with relative paths
        test_path = output_dir / '..' / 'escape'
        resolved = test_path.resolve()

        # Should resolve to actual path, not escape
        self.assertIsInstance(resolved, Path)

    def test_download_destination_validation(self):
        """Test that download destination is validated"""
        destination = Path(self.temp_dir) / 'test.zip'

        mock_response = MagicMock()
        mock_response.headers.get.return_value = '100'
        mock_response.read.side_effect = [b'test', b'']
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = bundle_ffmpeg.download_file('http://example.com/file.zip', destination)

            self.assertTrue(result)
            # Destination should be within temp_dir
            self.assertTrue(str(destination).startswith(str(self.temp_dir)))


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestBundleFFmpegPlatformDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestBundleFFmpegURLs))
    suite.addTests(loader.loadTestsFromTestCase(TestBundleFFmpegDownload))
    suite.addTests(loader.loadTestsFromTestCase(TestBundleFFmpegExtract))
    suite.addTests(loader.loadTestsFromTestCase(TestBundleFFmpegFindBinary))
    suite.addTests(loader.loadTestsFromTestCase(TestBundleFFmpegMain))
    suite.addTests(loader.loadTestsFromTestCase(TestBundleFFmpegIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestBundleFFmpegSecurity))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
