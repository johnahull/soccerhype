#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""Tests for render utility functions."""

import sys
from pathlib import Path

import pytest
sys.path.insert(0, str(Path(__file__).parent.parent))

from render.utils import escape_drawtext, resolve_path
from render.proxy import to_frame
from render.video import transform_for_zoom, build_zoom_filter


class TestEscapeDrawtext:
    def test_plain_text_unchanged(self):
        assert escape_drawtext("Hello World") == "Hello World"

    def test_escapes_colon(self):
        result = escape_drawtext("Time: 3:00")
        assert "\\:" in result

    def test_escapes_percent(self):
        result = escape_drawtext("100%")
        assert "\\%" in result

    def test_escapes_backslash(self):
        result = escape_drawtext("path\\to")
        assert "\\\\" in result

    def test_escapes_curly_braces(self):
        result = escape_drawtext("{text}")
        assert "\\{" in result
        assert "\\}" in result

    def test_escapes_square_brackets(self):
        result = escape_drawtext("[section]")
        assert "\\[" in result
        assert "\\]" in result

    def test_escapes_single_quote(self):
        result = escape_drawtext("it's")
        assert "'\\''" in result

    def test_empty_string(self):
        assert escape_drawtext("") == ""

    def test_multiple_special_chars(self):
        result = escape_drawtext("a:b%c{d}[e]")
        assert "\\:" in result
        assert "\\%" in result
        assert "\\{" in result
        assert "\\}" in result
        assert "\\[" in result
        assert "\\]" in result


class TestToFrame:
    def test_zero_time(self):
        assert to_frame(0.0, 30.0) == 0

    def test_one_second_at_30fps(self):
        assert to_frame(1.0, 30.0) == 30

    def test_half_second_at_30fps(self):
        assert to_frame(0.5, 30.0) == 15

    def test_negative_time_clamped(self):
        assert to_frame(-1.0, 30.0) == 0

    def test_fractional_frames_rounded(self):
        # 1.5s at 30fps = 45 frames
        assert to_frame(1.5, 30.0) == 45


class TestTransformForZoom:
    def test_no_zoom(self):
        mx, my, r = transform_for_zoom(960, 540, 72, 1920, 1080, 1.0)
        assert (mx, my, r) == (960, 540, 72)

    def test_zoom_center_stays_centered(self):
        # Center of 1920x1080 is (960, 540)
        mx, my, r = transform_for_zoom(960, 540, 72, 1920, 1080, 2.0)
        assert mx == 960
        assert my == 540
        assert r == 144  # radius doubles

    def test_zoom_off_center(self):
        # Point at (480, 270) - half of center coords
        mx, my, r = transform_for_zoom(480, 270, 72, 1920, 1080, 2.0)
        # Offset from center: (-480, -270), doubled: (-960, -540)
        # New position: (960-960, 540-540) = (0, 0)
        assert mx == 0
        assert my == 0

    def test_zoom_less_than_one_no_change(self):
        mx, my, r = transform_for_zoom(100, 200, 50, 1920, 1080, 0.5)
        assert (mx, my, r) == (100, 200, 50)


class TestBuildZoomFilter:
    def test_no_zoom_returns_empty(self):
        assert build_zoom_filter(1920, 1080, 1.0) == ""

    def test_zoom_returns_filter(self):
        result = build_zoom_filter(1920, 1080, 2.0)
        assert "crop=" in result
        assert "scale=1920:1080" in result
        assert "setsar=1" in result

    def test_zoom_less_than_one_returns_empty(self):
        assert build_zoom_filter(1920, 1080, 0.5) == ""


class TestResolvePath:
    def test_none_returns_none(self):
        assert resolve_path(Path("/base"), None) is None

    def test_empty_returns_none(self):
        assert resolve_path(Path("/base"), "") is None

    def test_relative_path_resolved(self):
        result = resolve_path(Path("/base"), "clips/clip01.mp4")
        assert result == Path("/base/clips/clip01.mp4")

    def test_absolute_path_unchanged(self):
        result = resolve_path(Path("/base"), "/absolute/path.mp4")
        assert result == Path("/absolute/path.mp4")
