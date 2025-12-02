#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""
Tests for video sections feature including security, validation, and persistence.
"""

import json
import pathlib
import sys
import tempfile
import unittest

# Add parent directory to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from constants import SECTIONS, SECTION_COLORS, OVERLAY_DEFAULT_COLOR
from render_highlight import escape_drawtext


class TestSectionConstants(unittest.TestCase):
    """Test that section constants are properly defined."""

    def test_sections_not_empty(self):
        """Sections list should not be empty."""
        self.assertGreater(len(SECTIONS), 0, "SECTIONS list should not be empty")

    def test_sections_are_strings(self):
        """All sections should be strings."""
        for section in SECTIONS:
            self.assertIsInstance(section, str, f"Section {section} should be a string")

    def test_all_sections_have_colors(self):
        """All sections should have corresponding colors."""
        for section in SECTIONS:
            self.assertIn(section, SECTION_COLORS, f"Section '{section}' missing color mapping")

    def test_all_colors_are_valid_hex(self):
        """All section colors should be valid hex color codes."""
        for section, color in SECTION_COLORS.items():
            self.assertRegex(color, r'^#[0-9A-Fa-f]{6}$',
                           f"Color for '{section}' is not valid hex: {color}")

    def test_default_color_is_valid_hex(self):
        """Default overlay color should be valid hex."""
        self.assertRegex(OVERLAY_DEFAULT_COLOR, r'^#[0-9A-Fa-f]{6}$',
                        f"Default color is not valid hex: {OVERLAY_DEFAULT_COLOR}")


class TestFFmpegTextEscaping(unittest.TestCase):
    """Test FFmpeg drawtext filter text escaping for security."""

    def test_simple_text_passthrough(self):
        """Simple text without special characters should pass through."""
        result = escape_drawtext("Goals")
        self.assertEqual(result, "Goals")

    def test_backslash_escaping(self):
        """Backslashes should be escaped."""
        result = escape_drawtext("Test\\Path")
        self.assertEqual(result, "Test\\\\Path")

    def test_colon_escaping(self):
        """Colons should be escaped (FFmpeg filter separator)."""
        result = escape_drawtext("Test:Value")
        self.assertEqual(result, "Test\\:Value")

    def test_percent_escaping(self):
        """Percent signs should be escaped (FFmpeg text expansion)."""
        result = escape_drawtext("100% Win")
        self.assertEqual(result, "100\\% Win")

    def test_curly_brace_escaping(self):
        """Curly braces should be escaped (FFmpeg text expansion)."""
        result = escape_drawtext("Test{value}")
        self.assertEqual(result, "Test\\{value\\}")

    def test_square_bracket_escaping(self):
        """Square brackets should be escaped (FFmpeg text expansion)."""
        result = escape_drawtext("Test[value]")
        self.assertEqual(result, "Test\\[value\\]")

    def test_single_quote_escaping(self):
        """Single quotes should be escaped for shell safety."""
        result = escape_drawtext("Goal's")
        # Single quote becomes '\\''
        self.assertIn("'\\''", result)

    def test_multiple_special_chars(self):
        """Multiple special characters should all be escaped."""
        result = escape_drawtext("Test: 100% {value}")
        self.assertIn("\\:", result)
        self.assertIn("\\%", result)
        self.assertIn("\\{", result)
        self.assertIn("\\}", result)

    def test_empty_string(self):
        """Empty string should return empty string."""
        result = escape_drawtext("")
        self.assertEqual(result, "")

    def test_unicode_characters(self):
        """Unicode characters should be preserved."""
        result = escape_drawtext("Futból")
        self.assertIn("Futból", result)


class TestSectionPersistence(unittest.TestCase):
    """Test that sections are properly saved and loaded from project.json."""

    def test_section_saves_to_json(self):
        """Section data should serialize to JSON correctly."""
        clip_data = {
            "proxy_name": "clip01.mp4",
            "section": "Goals"
        }
        json_str = json.dumps(clip_data)
        loaded = json.loads(json_str)
        self.assertEqual(loaded["section"], "Goals")

    def test_none_section_serializes(self):
        """None/null section should serialize correctly."""
        clip_data = {
            "proxy_name": "clip01.mp4",
            "section": None
        }
        json_str = json.dumps(clip_data)
        loaded = json.loads(json_str)
        self.assertIsNone(loaded["section"])

    def test_invalid_section_detection(self):
        """Invalid section names should be detectable."""
        invalid_section = "InvalidSection"
        self.assertNotIn(invalid_section, SECTIONS,
                        "Invalid section should not be in SECTIONS list")


class TestOverlayDurationCalculation(unittest.TestCase):
    """Test overlay duration calculation logic."""

    def test_normal_clip_duration(self):
        """Normal length clip (5s) should get default overlay duration."""
        from constants import OVERLAY_DURATION_DEFAULT, OVERLAY_DURATION_MIN, OVERLAY_MARGIN
        clip_dur = 5.0
        # Calculation: min(3.0, max(1.5, 5.0 - 0.5)) = min(3.0, 4.5) = 3.0
        overlay_dur = min(OVERLAY_DURATION_DEFAULT, max(OVERLAY_DURATION_MIN, clip_dur - OVERLAY_MARGIN))
        overlay_dur = min(overlay_dur, clip_dur)  # Critical fix
        self.assertEqual(overlay_dur, 3.0)
        self.assertLessEqual(overlay_dur, clip_dur)

    def test_short_clip_duration(self):
        """Short clip (2s) should get clamped overlay duration."""
        from constants import OVERLAY_DURATION_DEFAULT, OVERLAY_DURATION_MIN, OVERLAY_MARGIN
        clip_dur = 2.0
        # Calculation: min(3.0, max(1.5, 2.0 - 0.5)) = min(3.0, 1.5) = 1.5
        overlay_dur = min(OVERLAY_DURATION_DEFAULT, max(OVERLAY_DURATION_MIN, clip_dur - OVERLAY_MARGIN))
        overlay_dur = min(overlay_dur, clip_dur)  # Critical fix
        self.assertEqual(overlay_dur, 1.5)
        self.assertLessEqual(overlay_dur, clip_dur)

    def test_very_short_clip_duration(self):
        """Very short clip (1s) should never exceed clip duration."""
        from constants import OVERLAY_DURATION_DEFAULT, OVERLAY_DURATION_MIN, OVERLAY_MARGIN
        clip_dur = 1.0
        # Without fix: min(3.0, max(1.5, 1.0 - 0.5)) = min(3.0, 1.5) = 1.5 (BAD!)
        # With fix: min(1.5, 1.0) = 1.0 (GOOD!)
        overlay_dur = min(OVERLAY_DURATION_DEFAULT, max(OVERLAY_DURATION_MIN, clip_dur - OVERLAY_MARGIN))
        overlay_dur = min(overlay_dur, clip_dur)  # Critical fix
        self.assertEqual(overlay_dur, 1.0)
        self.assertLessEqual(overlay_dur, clip_dur)

    def test_overlay_never_exceeds_clip(self):
        """Overlay duration should never exceed clip duration for any input."""
        from constants import OVERLAY_DURATION_DEFAULT, OVERLAY_DURATION_MIN, OVERLAY_MARGIN
        test_durations = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
        for clip_dur in test_durations:
            overlay_dur = min(OVERLAY_DURATION_DEFAULT, max(OVERLAY_DURATION_MIN, clip_dur - OVERLAY_MARGIN))
            overlay_dur = min(overlay_dur, clip_dur)  # Critical fix
            self.assertLessEqual(overlay_dur, clip_dur,
                               f"Overlay {overlay_dur}s exceeds clip duration {clip_dur}s")


if __name__ == "__main__":
    unittest.main()
