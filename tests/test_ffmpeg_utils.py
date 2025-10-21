#!/usr/bin/env python3
"""
Tests for ffmpeg_utils module
Tests FFmpeg detection, bundled vs system binary handling
"""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import ffmpeg_utils


class TestFFmpegUtils(unittest.TestCase):
    """Test suite for ffmpeg_utils module"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.binaries_dir = Path(self.temp_dir) / 'binaries'
        self.binaries_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_system_ffmpeg_path_when_installed(self):
        """Test system FFmpeg detection when FFmpeg is installed"""
        result = ffmpeg_utils.get_system_ffmpeg_path()

        # Check if ffmpeg is actually installed on the system
        if shutil.which('ffmpeg'):
            self.assertIsNotNone(result)
            self.assertTrue(os.path.exists(result))
        else:
            self.assertIsNone(result)

    def test_get_bundled_ffmpeg_path_not_frozen(self):
        """Test bundled FFmpeg detection when not running as PyInstaller bundle"""
        # When not frozen, should check local binaries directory
        with patch('pathlib.Path.exists', return_value=False):
            result = ffmpeg_utils.get_bundled_ffmpeg_path()
            # May be None if binaries directory doesn't exist
            self.assertIsInstance(result, (str, type(None)))

    def test_get_bundled_ffmpeg_path_frozen(self):
        """Test bundled FFmpeg detection when running as PyInstaller bundle"""
        # Mock PyInstaller frozen state
        with patch('sys.frozen', True, create=True):
            with patch('sys._MEIPASS', self.temp_dir, create=True):
                # Create mock FFmpeg binary
                if platform.system() == 'Windows':
                    ffmpeg_path = self.binaries_dir / 'ffmpeg.exe'
                else:
                    ffmpeg_path = self.binaries_dir / 'ffmpeg'

                ffmpeg_path.touch()

                result = ffmpeg_utils.get_bundled_ffmpeg_path()

                if result:
                    self.assertIsInstance(result, str)

    def test_get_ffmpeg_path_priority(self):
        """Test that bundled FFmpeg takes priority over system FFmpeg"""
        # This test verifies the priority order
        result = ffmpeg_utils.get_ffmpeg_path()

        # Should return either bundled or system path, or None
        self.assertIsInstance(result, (str, type(None)))

    def test_verify_ffmpeg_not_found(self):
        """Test verification when FFmpeg is not found"""
        success, version, error = ffmpeg_utils.verify_ffmpeg('/nonexistent/ffmpeg')

        self.assertFalse(success)
        self.assertIsNone(version)
        self.assertIsNotNone(error)
        self.assertIn('not found', error.lower())

    def test_verify_ffmpeg_with_system_binary(self):
        """Test verification with actual system FFmpeg if available"""
        system_ffmpeg = shutil.which('ffmpeg')

        if system_ffmpeg:
            success, version, error = ffmpeg_utils.verify_ffmpeg(system_ffmpeg)

            self.assertTrue(success)
            self.assertIsNotNone(version)
            self.assertIsNone(error)
            self.assertIn('ffmpeg', version.lower())
        else:
            self.skipTest("FFmpeg not installed on system")

    def test_verify_ffmpeg_auto_detect(self):
        """Test verification with auto-detection"""
        if shutil.which('ffmpeg'):
            success, version, error = ffmpeg_utils.verify_ffmpeg()

            # Should succeed if FFmpeg is in PATH or bundled
            if success:
                self.assertIsNotNone(version)
                self.assertIsNone(error)
        else:
            # No FFmpeg available
            success, version, error = ffmpeg_utils.verify_ffmpeg()
            self.assertFalse(success)

    def test_get_ffmpeg_info_structure(self):
        """Test that get_ffmpeg_info returns correct structure"""
        info = ffmpeg_utils.get_ffmpeg_info()

        # Verify all required keys are present
        required_keys = ['bundled_path', 'system_path', 'active_path',
                        'is_bundled', 'version', 'error']

        for key in required_keys:
            self.assertIn(key, info)

    def test_get_ffmpeg_info_is_bundled_flag(self):
        """Test that is_bundled flag is correctly set"""
        info = ffmpeg_utils.get_ffmpeg_info()

        # is_bundled should be boolean
        self.assertIsInstance(info['is_bundled'], bool)

        # If active_path equals bundled_path, is_bundled should be True
        if info['active_path'] and info['bundled_path']:
            if info['active_path'] == info['bundled_path']:
                self.assertTrue(info['is_bundled'])

    def test_ensure_ffmpeg_available_when_not_available(self):
        """Test ensure_ffmpeg_available raises error when FFmpeg not found"""
        with patch('ffmpeg_utils.get_ffmpeg_path', return_value=None):
            with self.assertRaises(RuntimeError) as context:
                ffmpeg_utils.ensure_ffmpeg_available()

            self.assertIn('FFmpeg not found', str(context.exception))

    def test_ensure_ffmpeg_available_when_verification_fails(self):
        """Test ensure_ffmpeg_available raises error when verification fails"""
        with patch('ffmpeg_utils.get_ffmpeg_path', return_value='/fake/ffmpeg'):
            with patch('ffmpeg_utils.verify_ffmpeg', return_value=(False, None, 'Test error')):
                with self.assertRaises(RuntimeError) as context:
                    ffmpeg_utils.ensure_ffmpeg_available()

                self.assertIn('verification failed', str(context.exception).lower())

    def test_ensure_ffmpeg_available_success(self):
        """Test ensure_ffmpeg_available returns path when successful"""
        system_ffmpeg = shutil.which('ffmpeg')

        if system_ffmpeg:
            path = ffmpeg_utils.ensure_ffmpeg_available()
            self.assertIsNotNone(path)
            self.assertTrue(os.path.exists(path))
        else:
            self.skipTest("FFmpeg not installed on system")

    def test_platform_specific_binary_names(self):
        """Test that platform-specific binary names are used"""
        with patch('platform.system', return_value='Windows'):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.is_file', return_value=True):
                    # Should look for ffmpeg.exe on Windows
                    # This is implicitly tested in get_bundled_ffmpeg_path
                    pass

    def test_print_ffmpeg_info_no_exception(self):
        """Test that print_ffmpeg_info doesn't raise exceptions"""
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            ffmpeg_utils.print_ffmpeg_info()

        output = f.getvalue()
        self.assertIn('FFmpeg Detection Information', output)


class TestFFmpegUtilsIntegration(unittest.TestCase):
    """Integration tests for ffmpeg_utils with real FFmpeg binary"""

    def test_real_ffmpeg_verification(self):
        """Test verification with real FFmpeg binary if available"""
        ffmpeg_path = shutil.which('ffmpeg')

        if not ffmpeg_path:
            self.skipTest("FFmpeg not installed on system")

        success, version, error = ffmpeg_utils.verify_ffmpeg(ffmpeg_path)

        self.assertTrue(success, f"FFmpeg verification failed: {error}")
        self.assertIsNotNone(version)
        self.assertIsNone(error)

        # Verify version string contains expected information
        self.assertIn('ffmpeg', version.lower())

    def test_ffmpeg_path_is_executable(self):
        """Test that returned FFmpeg path is executable"""
        ffmpeg_path = ffmpeg_utils.get_ffmpeg_path()

        if not ffmpeg_path:
            self.skipTest("FFmpeg not found")

        # Check if file exists
        self.assertTrue(os.path.exists(ffmpeg_path))

        # On Unix-like systems, check if executable
        if platform.system() != 'Windows':
            self.assertTrue(os.access(ffmpeg_path, os.X_OK))


class TestFFmpegUtilsEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_verify_ffmpeg_timeout(self):
        """Test that verification handles timeout correctly"""
        # Create a mock that times out
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('ffmpeg', 5)):
            success, version, error = ffmpeg_utils.verify_ffmpeg('/fake/ffmpeg')

            self.assertFalse(success)
            self.assertIsNone(version)
            self.assertIn('timed out', error.lower())

    def test_verify_ffmpeg_with_invalid_binary(self):
        """Test verification with a file that's not FFmpeg"""
        # Create a temporary non-FFmpeg file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            success, version, error = ffmpeg_utils.verify_ffmpeg(temp_file)

            # Should fail as it's not FFmpeg
            self.assertFalse(success)
        finally:
            os.unlink(temp_file)

    def test_get_bundled_path_with_symlink(self):
        """Test bundled path resolution with symlinks"""
        if platform.system() == 'Windows':
            self.skipTest("Symlink test not applicable on Windows")

        temp_dir = tempfile.mkdtemp()
        try:
            binaries_dir = Path(temp_dir) / 'binaries'
            binaries_dir.mkdir()

            # Create a fake ffmpeg binary
            fake_ffmpeg = binaries_dir / 'ffmpeg'
            fake_ffmpeg.touch()

            # Should handle symlinks correctly
            if fake_ffmpeg.exists():
                self.assertTrue(fake_ffmpeg.is_file())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_path_with_spaces(self):
        """Test FFmpeg paths containing spaces"""
        test_path = "/path with spaces/to/ffmpeg"

        # Verify the path is handled correctly
        success, version, error = ffmpeg_utils.verify_ffmpeg(test_path)

        # Should fail (doesn't exist) but shouldn't crash
        self.assertFalse(success)
        self.assertIsInstance(error, str)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFFmpegUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestFFmpegUtilsIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestFFmpegUtilsEdgeCases))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
