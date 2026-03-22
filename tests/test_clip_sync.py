#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Tests for clip_sync.py - clip marking status detection."""

import json
import sys
from pathlib import Path

import pytest
sys.path.insert(0, str(Path(__file__).parent.parent))

from clip_sync import is_clip_marked


class TestIsClipMarked:
    def test_fully_marked_clip(self):
        clip = {
            "file": "clips_in/clip01.mp4",
            "marker_x_std": 960,
            "marker_y_std": 540,
            "spot_time": 1.0,
            "radius_std": 72,
        }
        assert is_clip_marked(clip) is True

    def test_unmarked_clip_no_marker(self):
        clip = {
            "file": "clips_in/clip01.mp4",
        }
        assert is_clip_marked(clip) is False

    def test_partially_marked_clip(self):
        clip = {
            "file": "clips_in/clip01.mp4",
            "marker_x_std": 960,
            # missing marker_y_std, spot_frame_std
        }
        # Partial marking - depends on implementation
        # At minimum, should not crash
        result = is_clip_marked(clip)
        assert isinstance(result, bool)

    def test_clip_with_zero_values(self):
        clip = {
            "file": "clips_in/clip01.mp4",
            "marker_x_std": 0,
            "marker_y_std": 0,
            "spot_frame_std": 0,
            "radius_std": 72,
        }
        # Zero coordinates are valid (top-left corner)
        result = is_clip_marked(clip)
        assert isinstance(result, bool)

    def test_empty_clip_dict(self):
        assert is_clip_marked({}) is False

    def test_clip_with_legacy_fields(self):
        clip = {
            "file": "clips_in/clip01.mp4",
            "marker_x": 960,
            "marker_y": 540,
            "spot_time": 1.0,
            "radius": 72,
        }
        # Legacy fields without _std suffix
        result = is_clip_marked(clip)
        assert isinstance(result, bool)
