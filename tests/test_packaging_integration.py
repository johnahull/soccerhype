#!/usr/bin/env python3
"""
Integration tests for standalone packaging
Tests the complete packaging workflow
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPackagingFiles(unittest.TestCase):
    """Test that all packaging files exist and are valid"""

    def test_spec_file_exists(self):
        """Test that PyInstaller spec file exists"""
        spec_file = Path('soccerhype.spec')
        self.assertTrue(spec_file.exists(), "soccerhype.spec not found")

    def test_spec_file_syntax(self):
        """Test that spec file has valid Python syntax"""
        spec_file = Path('soccerhype.spec')

        if spec_file.exists():
            # Try to compile the spec file
            with open(spec_file) as f:
                content = f.read()

            try:
                compile(content, str(spec_file), 'exec')
            except SyntaxError as e:
                self.fail(f"Spec file has syntax errors: {e}")

    def test_build_scripts_exist(self):
        """Test that build scripts exist"""
        windows_script = Path('build_windows.bat')
        macos_script = Path('build_macos.sh')

        self.assertTrue(windows_script.exists(), "build_windows.bat not found")
        self.assertTrue(macos_script.exists(), "build_macos.sh not found")

    def test_macos_script_executable(self):
        """Test that macOS build script is executable"""
        macos_script = Path('build_macos.sh')

        if macos_script.exists() and sys.platform != 'win32':
            # Check if executable
            self.assertTrue(os.access(macos_script, os.X_OK),
                          "build_macos.sh is not executable")

    def test_bundle_ffmpeg_script_exists(self):
        """Test that FFmpeg bundling script exists"""
        bundle_script = Path('bundle_ffmpeg.py')
        self.assertTrue(bundle_script.exists(), "bundle_ffmpeg.py not found")

    def test_bundle_ffmpeg_executable(self):
        """Test that bundle_ffmpeg.py is executable"""
        bundle_script = Path('bundle_ffmpeg.py')

        if bundle_script.exists() and sys.platform != 'win32':
            self.assertTrue(os.access(bundle_script, os.X_OK),
                          "bundle_ffmpeg.py is not executable")

    def test_ffmpeg_utils_exists(self):
        """Test that ffmpeg_utils module exists"""
        utils_file = Path('ffmpeg_utils.py')
        self.assertTrue(utils_file.exists(), "ffmpeg_utils.py not found")

    def test_packaging_documentation_exists(self):
        """Test that packaging documentation exists"""
        packaging_doc = Path('PACKAGING.md')
        self.assertTrue(packaging_doc.exists(), "PACKAGING.md not found")

    def test_packaging_doc_not_empty(self):
        """Test that packaging documentation has content"""
        packaging_doc = Path('PACKAGING.md')

        if packaging_doc.exists():
            content = packaging_doc.read_text()
            self.assertGreater(len(content), 1000,
                             "PACKAGING.md seems too short")

    def test_requirements_includes_pyinstaller(self):
        """Test that requirements.txt includes PyInstaller"""
        requirements = Path('requirements.txt')

        if requirements.exists():
            content = requirements.read_text().lower()
            self.assertIn('pyinstaller', content,
                        "PyInstaller not in requirements.txt")


class TestPackagingModules(unittest.TestCase):
    """Test that packaging modules can be imported"""

    def test_import_ffmpeg_utils(self):
        """Test that ffmpeg_utils can be imported"""
        try:
            import ffmpeg_utils
        except ImportError as e:
            self.fail(f"Cannot import ffmpeg_utils: {e}")

    def test_import_bundle_ffmpeg(self):
        """Test that bundle_ffmpeg can be imported"""
        try:
            import bundle_ffmpeg
        except ImportError as e:
            self.fail(f"Cannot import bundle_ffmpeg: {e}")

    def test_ffmpeg_utils_functions_exist(self):
        """Test that required functions exist in ffmpeg_utils"""
        import ffmpeg_utils

        required_functions = [
            'get_ffmpeg_path',
            'get_bundled_ffmpeg_path',
            'get_system_ffmpeg_path',
            'verify_ffmpeg',
            'get_ffmpeg_info',
            'ensure_ffmpeg_available',
            'print_ffmpeg_info'
        ]

        for func_name in required_functions:
            self.assertTrue(hasattr(ffmpeg_utils, func_name),
                          f"ffmpeg_utils missing function: {func_name}")

    def test_bundle_ffmpeg_functions_exist(self):
        """Test that required functions exist in bundle_ffmpeg"""
        import bundle_ffmpeg

        required_functions = [
            'detect_platform',
            'download_file',
            'extract_archive',
            'find_ffmpeg_binary',
            'bundle_ffmpeg',
        ]

        for func_name in required_functions:
            self.assertTrue(hasattr(bundle_ffmpeg, func_name),
                          f"bundle_ffmpeg missing function: {func_name}")


class TestGitignoreConfiguration(unittest.TestCase):
    """Test that .gitignore is properly configured for packaging"""

    def test_gitignore_exists(self):
        """Test that .gitignore exists"""
        gitignore = Path('.gitignore')
        self.assertTrue(gitignore.exists(), ".gitignore not found")

    def test_gitignore_excludes_build_artifacts(self):
        """Test that .gitignore excludes build directories"""
        gitignore = Path('.gitignore')

        if gitignore.exists():
            content = gitignore.read_text()

            required_excludes = ['build/', 'dist/', 'binaries/']

            for exclude in required_excludes:
                self.assertIn(exclude, content,
                            f".gitignore missing: {exclude}")

    def test_gitignore_excludes_ffmpeg_temp(self):
        """Test that .gitignore excludes FFmpeg temporary files"""
        gitignore = Path('.gitignore')

        if gitignore.exists():
            content = gitignore.read_text()
            self.assertIn('temp_ffmpeg_download', content)


class TestMainApplicationEntry(unittest.TestCase):
    """Test main application entry point"""

    def test_soccerhype_gui_exists(self):
        """Test that main GUI application exists"""
        gui_file = Path('soccerhype_gui.py')
        self.assertTrue(gui_file.exists(), "soccerhype_gui.py not found")

    def test_soccerhype_gui_has_main(self):
        """Test that GUI has main entry point"""
        gui_file = Path('soccerhype_gui.py')

        if gui_file.exists():
            content = gui_file.read_text()
            self.assertIn('if __name__ == "__main__"', content)
            self.assertIn('def main(', content)


class TestScriptValidation(unittest.TestCase):
    """Validate build scripts syntax and structure"""

    def test_windows_script_syntax(self):
        """Test Windows batch script for obvious syntax errors"""
        script = Path('build_windows.bat')

        if script.exists():
            content = script.read_text()

            # Check for basic batch file structure
            self.assertIn('@echo off', content.lower())
            self.assertIn('pyinstaller', content.lower())

    def test_macos_script_syntax(self):
        """Test macOS shell script for obvious syntax errors"""
        script = Path('build_macos.sh')

        if script.exists():
            content = script.read_text()

            # Check for bash shebang
            self.assertTrue(content.startswith('#!/bin/bash'))

            # Check for basic commands
            self.assertIn('pyinstaller', content)

    def test_macos_script_has_error_handling(self):
        """Test that macOS script has error handling"""
        script = Path('build_macos.sh')

        if script.exists():
            content = script.read_text()

            # Should have set -e for error handling
            self.assertIn('set -e', content)


class TestSpecFileConfiguration(unittest.TestCase):
    """Test PyInstaller spec file configuration"""

    def test_spec_defines_analysis(self):
        """Test that spec file defines Analysis"""
        spec_file = Path('soccerhype.spec')

        if spec_file.exists():
            content = spec_file.read_text()
            self.assertIn('Analysis', content)
            self.assertIn('soccerhype_gui.py', content)

    def test_spec_defines_exe(self):
        """Test that spec file defines EXE"""
        spec_file = Path('soccerhype.spec')

        if spec_file.exists():
            content = spec_file.read_text()
            self.assertIn('EXE(', content)

    def test_spec_defines_collect(self):
        """Test that spec file defines COLLECT"""
        spec_file = Path('soccerhype.spec')

        if spec_file.exists():
            content = spec_file.read_text()
            self.assertIn('COLLECT(', content)

    def test_spec_has_platform_detection(self):
        """Test that spec file has platform detection"""
        spec_file = Path('soccerhype.spec')

        if spec_file.exists():
            content = spec_file.read_text()
            self.assertIn('sys.platform', content)


class TestDocumentation(unittest.TestCase):
    """Test packaging documentation completeness"""

    def test_packaging_md_has_all_sections(self):
        """Test that PACKAGING.md has all required sections"""
        doc = Path('PACKAGING.md')

        if doc.exists():
            content = doc.read_text()

            required_sections = [
                'Overview',
                'Prerequisites',
                'Quick Start',
                'Windows',
                'macOS',
                'Troubleshooting',
                'Build',
                'FFmpeg'
            ]

            for section in required_sections:
                self.assertIn(section, content,
                            f"PACKAGING.md missing section: {section}")

    def test_claude_md_mentions_packaging(self):
        """Test that CLAUDE.md mentions packaging"""
        doc = Path('CLAUDE.md')

        if doc.exists():
            content = doc.read_text()
            self.assertIn('Packaging', content)
            self.assertIn('PACKAGING.md', content)


class TestEnvironmentSetup(unittest.TestCase):
    """Test environment setup for packaging"""

    def test_python_version_compatible(self):
        """Test that Python version is compatible"""
        version = sys.version_info

        # Require Python 3.9+
        self.assertGreaterEqual(version.major, 3)
        if version.major == 3:
            self.assertGreaterEqual(version.minor, 9)

    @unittest.skipIf(sys.platform == 'win32', "Not applicable on Windows")
    def test_scripts_have_unix_line_endings(self):
        """Test that shell scripts have Unix line endings"""
        script = Path('build_macos.sh')

        if script.exists():
            with open(script, 'rb') as f:
                content = f.read()

            # Should not have Windows line endings
            self.assertNotIn(b'\r\n', content,
                           "Script has Windows line endings")


def run_tests():
    """Run all integration tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPackagingFiles))
    suite.addTests(loader.loadTestsFromTestCase(TestPackagingModules))
    suite.addTests(loader.loadTestsFromTestCase(TestGitignoreConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestMainApplicationEntry))
    suite.addTests(loader.loadTestsFromTestCase(TestScriptValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestSpecFileConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestDocumentation))
    suite.addTests(loader.loadTestsFromTestCase(TestEnvironmentSetup))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
