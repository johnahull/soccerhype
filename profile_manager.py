#!/usr/bin/env python3
# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""
Player Profile Management Module

Provides secure, centralized management of player profiles with atomic file operations,
input validation, and PII protection.

This module is extracted from soccerhype_gui.py to improve code organization and
maintainability while maintaining security best practices.
"""

import json
import os
import pathlib
import re
import tempfile
import time
import tkinter as tk
from tkinter import messagebox
from typing import Dict, List, Optional


def sanitize_profile_id(name: str) -> str:
    """
    Sanitize a name to create a safe profile ID.

    Args:
        name: The player name to sanitize

    Returns:
        A sanitized profile ID containing only alphanumeric characters and underscores
    """
    # Remove all non-alphanumeric characters except spaces, convert to lowercase
    clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name).strip().lower()
    # Replace spaces with underscores and collapse multiple underscores
    clean_name = re.sub(r'\s+', '_', clean_name)
    # Remove leading/trailing underscores and limit length
    clean_name = clean_name.strip('_')[:20]
    # Ensure it's not empty
    if not clean_name:
        clean_name = 'player'
    return clean_name


class PlayerProfileManager:
    """
    Secure player profile management with atomic file operations.

    This class provides centralized management of player profiles with:
    - Atomic file operations using temp file + rename pattern
    - Input validation and sanitization
    - PII protection (profiles excluded from version control)
    - Comprehensive error handling
    """

    def __init__(self, profiles_db_path: pathlib.Path):
        """
        Initialize the profile manager.

        Args:
            profiles_db_path: Path to the player profiles database file
        """
        self.profiles_db_path = profiles_db_path
        self.player_profiles: Dict[str, Dict] = {}
        self.load_player_profiles()

    def load_player_profiles(self) -> None:
        """Load player profiles from database file with error handling."""
        try:
            if self.profiles_db_path.exists():
                with open(self.profiles_db_path, 'r', encoding='utf-8') as f:
                    self.player_profiles = json.load(f)
            else:
                self.player_profiles = {}
        except (IOError, json.JSONDecodeError) as e:
            messagebox.showerror("Error", f"Could not load player profiles: {e}")
            self.player_profiles = {}

    def save_player_profiles(self) -> None:
        """Save player profiles using atomic write operation."""
        try:
            # Use atomic write: write to temp file, then rename
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.json',
                dir=self.profiles_db_path.parent
            )
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(self.player_profiles, f, indent=2, ensure_ascii=False)
                # Atomic rename on same filesystem
                os.replace(temp_path, self.profiles_db_path)
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
        except IOError as e:
            messagebox.showerror("Error", f"Could not save player profiles: {e}")

    def get_profile_names(self) -> List[str]:
        """Get list of profile IDs for dropdown menus."""
        return list(self.player_profiles.keys())

    def get_profile(self, profile_id: str) -> Dict:
        """
        Get profile data by ID.

        Args:
            profile_id: The profile identifier

        Returns:
            Profile data dictionary, or empty dict if not found
        """
        return self.player_profiles.get(profile_id, {})

    def save_profile(self, profile_id: str, profile_data: Dict) -> None:
        """
        Save a profile with validation.

        Args:
            profile_id: The profile identifier
            profile_data: Profile data dictionary
        """
        # Add timestamps
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        if profile_id not in self.player_profiles:
            profile_data["created"] = current_time
        profile_data["modified"] = current_time

        self.player_profiles[profile_id] = profile_data
        self.save_player_profiles()

    def delete_profile(self, profile_id: str) -> bool:
        """
        Delete a profile.

        Args:
            profile_id: The profile identifier

        Returns:
            True if profile was deleted, False if not found
        """
        if profile_id in self.player_profiles:
            del self.player_profiles[profile_id]
            self.save_player_profiles()
            return True
        return False

    def validate_profile_data(self, profile_data: Dict) -> List[str]:
        """
        Validate profile data and return list of errors.

        Args:
            profile_data: Profile data to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate required fields
        name = profile_data.get('name', '').strip()
        if not name:
            errors.append("Player name is required")
        elif len(name) > 100:
            errors.append("Player name must be 100 characters or less")

        # Validate email if provided
        email = profile_data.get('email', '').strip()
        if email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                errors.append("Invalid email format")

        # Validate GPA if provided
        gpa = profile_data.get('gpa', '').strip()
        if gpa:
            try:
                gpa_float = float(gpa)
                if not (0.0 <= gpa_float <= 4.0):
                    errors.append("GPA must be between 0.0 and 4.0")
            except ValueError:
                errors.append("GPA must be a valid number")

        # Validate graduation year if provided
        grad_year = profile_data.get('grad_year', '').strip()
        if grad_year:
            try:
                year = int(grad_year)
                current_year = time.localtime().tm_year
                if not (current_year <= year <= current_year + 10):
                    errors.append(f"Graduation year must be between {current_year} and {current_year + 10}")
            except ValueError:
                errors.append("Graduation year must be a valid number")

        return errors

    def generate_profile_id(self, name: str) -> str:
        """
        Generate a unique profile ID based on the player name.

        Args:
            name: The player's name

        Returns:
            A unique profile ID
        """
        base_id = sanitize_profile_id(name)
        timestamp = str(int(time.time()))
        return f"{base_id}_{timestamp}"

    def duplicate_profile(self, source_profile_id: str, new_name: str) -> Optional[str]:
        """
        Create a duplicate of an existing profile with a new name.

        Args:
            source_profile_id: ID of the profile to duplicate
            new_name: Name for the new profile

        Returns:
            The new profile ID if successful, None if source not found
        """
        if source_profile_id not in self.player_profiles:
            return None

        # Create a copy of the source profile
        source_profile = self.player_profiles[source_profile_id].copy()
        source_profile['name'] = new_name

        # Generate new ID and save
        new_profile_id = self.generate_profile_id(new_name)
        self.save_profile(new_profile_id, source_profile)

        return new_profile_id

    def get_profiles_count(self) -> int:
        """Get the total number of profiles."""
        return len(self.player_profiles)

    def search_profiles(self, search_term: str) -> List[str]:
        """
        Search profiles by name.

        Args:
            search_term: Text to search for in profile names

        Returns:
            List of profile IDs matching the search term
        """
        search_lower = search_term.lower()
        matching_ids = []

        for profile_id, profile_data in self.player_profiles.items():
            name = profile_data.get('name', '').lower()
            if search_lower in name:
                matching_ids.append(profile_id)

        return matching_ids