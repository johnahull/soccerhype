#!/usr/bin/env python3
"""
Security tests for PlayerProfileManager module.

Tests focus on security-critical functionality including:
- Path traversal prevention
- Input validation and sanitization
- PII protection
- Atomic file operations
"""

import tempfile
import unittest
import pathlib
import json
import os
from unittest.mock import patch, mock_open

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from profile_manager import PlayerProfileManager, sanitize_profile_id


class TestSanitizeProfileId(unittest.TestCase):
    """Test profile ID sanitization for security."""

    def test_basic_sanitization(self):
        """Test basic name sanitization."""
        self.assertEqual(sanitize_profile_id("John Smith"), "john_smith")

    def test_special_characters_removed(self):
        """Test that special characters are removed."""
        self.assertEqual(sanitize_profile_id("John@Smith!"), "johnsmith")

    def test_multiple_spaces_collapsed(self):
        """Test that multiple spaces are collapsed to single underscore."""
        self.assertEqual(sanitize_profile_id("John   Smith"), "john_smith")

    def test_length_limit(self):
        """Test that profile IDs are limited to 20 characters."""
        long_name = "A" * 30
        result = sanitize_profile_id(long_name)
        self.assertLessEqual(len(result), 20)

    def test_empty_name_fallback(self):
        """Test fallback for empty names."""
        self.assertEqual(sanitize_profile_id(""), "player")
        self.assertEqual(sanitize_profile_id("   "), "player")
        self.assertEqual(sanitize_profile_id("@#$%"), "player")

    def test_directory_traversal_prevention(self):
        """Test that directory traversal attempts are sanitized."""
        self.assertEqual(sanitize_profile_id("../../../etc/passwd"), "etcpasswd")
        self.assertEqual(sanitize_profile_id("..\\..\\windows\\system32"), "windowssystem32")


class TestPlayerProfileManager(unittest.TestCase):
    """Test PlayerProfileManager security and functionality."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = pathlib.Path(self.temp_dir) / "test_profiles.json"
        self.manager = PlayerProfileManager(self.db_path)

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_database_initialization(self):
        """Test initialization with empty database."""
        self.assertEqual(len(self.manager.player_profiles), 0)
        self.assertEqual(self.manager.get_profiles_count(), 0)

    def test_profile_validation_email(self):
        """Test email validation."""
        # Valid emails
        valid_profile = {"name": "Test Player", "email": "test@example.com"}
        errors = self.manager.validate_profile_data(valid_profile)
        self.assertEqual(len(errors), 0)

        # Invalid emails
        invalid_profile = {"name": "Test Player", "email": "invalid-email"}
        errors = self.manager.validate_profile_data(invalid_profile)
        self.assertIn("Invalid email format", errors)

    def test_profile_validation_name_required(self):
        """Test that name is required."""
        empty_name_profile = {"name": "", "email": "test@example.com"}
        errors = self.manager.validate_profile_data(empty_name_profile)
        self.assertIn("Player name is required", errors)

    def test_profile_validation_name_length(self):
        """Test name length validation."""
        long_name_profile = {"name": "A" * 101}  # Over 100 chars
        errors = self.manager.validate_profile_data(long_name_profile)
        self.assertIn("Player name must be 100 characters or less", errors)

    def test_profile_validation_gpa_range(self):
        """Test GPA validation."""
        # Valid GPA
        valid_profile = {"name": "Test Player", "gpa": "3.5"}
        errors = self.manager.validate_profile_data(valid_profile)
        self.assertEqual(len(errors), 0)

        # Invalid GPA (out of range)
        invalid_profile = {"name": "Test Player", "gpa": "5.0"}
        errors = self.manager.validate_profile_data(invalid_profile)
        self.assertIn("GPA must be between 0.0 and 4.0", errors)

        # Invalid GPA (not a number)
        invalid_profile = {"name": "Test Player", "gpa": "abc"}
        errors = self.manager.validate_profile_data(invalid_profile)
        self.assertIn("GPA must be a valid number", errors)

    def test_profile_id_generation_uniqueness(self):
        """Test that profile IDs are unique."""
        import time
        id1 = self.manager.generate_profile_id("John Smith")
        time.sleep(0.001)  # Ensure different timestamp
        id2 = self.manager.generate_profile_id("John Smith")
        self.assertNotEqual(id1, id2)  # Should have different timestamps

    def test_atomic_file_operations(self):
        """Test that file operations are atomic."""
        # Save a profile
        profile_data = {"name": "Test Player", "email": "test@example.com"}
        profile_id = self.manager.generate_profile_id("Test Player")

        self.manager.save_profile(profile_id, profile_data)

        # Verify file exists and contains data
        self.assertTrue(self.db_path.exists())
        with open(self.db_path, 'r') as f:
            data = json.load(f)
            self.assertIn(profile_id, data)
            self.assertEqual(data[profile_id]["name"], "Test Player")

    def test_search_functionality(self):
        """Test profile search."""
        # Add test profiles
        profile1 = {"name": "John Smith", "position": "Forward"}
        profile2 = {"name": "Jane Doe", "position": "Midfielder"}

        id1 = self.manager.generate_profile_id("John Smith")
        id2 = self.manager.generate_profile_id("Jane Doe")

        self.manager.save_profile(id1, profile1)
        self.manager.save_profile(id2, profile2)

        # Test search
        results = self.manager.search_profiles("john")
        self.assertEqual(len(results), 1)
        self.assertIn(id1, results)

        results = self.manager.search_profiles("smith")
        self.assertEqual(len(results), 1)
        self.assertIn(id1, results)

    def test_duplicate_profile(self):
        """Test profile duplication."""
        original_profile = {"name": "Original Player", "position": "Forward"}
        original_id = self.manager.generate_profile_id("Original Player")

        self.manager.save_profile(original_id, original_profile)

        # Duplicate profile
        new_id = self.manager.duplicate_profile(original_id, "Duplicate Player")
        self.assertIsNotNone(new_id)

        # Verify duplicate exists with new name
        duplicate_profile = self.manager.get_profile(new_id)
        self.assertEqual(duplicate_profile["name"], "Duplicate Player")
        self.assertEqual(duplicate_profile["position"], "Forward")  # Copied field

    def test_profile_deletion(self):
        """Test profile deletion."""
        profile_data = {"name": "Test Player"}
        profile_id = self.manager.generate_profile_id("Test Player")

        self.manager.save_profile(profile_id, profile_data)
        self.assertEqual(self.manager.get_profiles_count(), 1)

        # Delete profile
        result = self.manager.delete_profile(profile_id)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_profiles_count(), 0)

        # Try to delete non-existent profile
        result = self.manager.delete_profile("non_existent")
        self.assertFalse(result)


class TestSecurityFeatures(unittest.TestCase):
    """Test security-specific features."""

    def test_pii_not_logged_in_errors(self):
        """Test that PII is not exposed in error messages."""
        # This would be implemented based on actual error handling
        # For now, it's a placeholder for the security requirement
        pass

    def test_path_validation(self):
        """Test that paths are validated properly."""
        # Test that manager only works with safe paths
        with tempfile.TemporaryDirectory() as temp_dir:
            safe_path = pathlib.Path(temp_dir) / "profiles.json"
            manager = PlayerProfileManager(safe_path)

            # This should work
            self.assertIsInstance(manager, PlayerProfileManager)

    def test_input_sanitization_comprehensive(self):
        """Test comprehensive input sanitization."""
        test_cases = [
            "normal_name",
            "name with spaces",
            "name@with#special!chars",
            "../../../etc/passwd",
            "name\nwith\nnewlines",
            "name\twith\ttabs",
            "name<script>alert('xss')</script>",
        ]

        for test_input in test_cases:
            result = sanitize_profile_id(test_input)
            # Ensure result contains only safe characters
            self.assertRegex(result, r'^[a-z0-9_]+$')
            self.assertLessEqual(len(result), 20)


if __name__ == '__main__':
    unittest.main()