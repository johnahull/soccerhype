# Copyright (c) 2025 John Hull
# Licensed under the MIT License - see LICENSE file
"""
SoccerHype version information.

This module provides version information for the SoccerHype highlight video tool.
"""

__version__ = "0.1.0"
__version_info__ = tuple(int(x) for x in __version__.split("."))

# Release information
RELEASE_DATE = "2025-01-10"
PROJECT_NAME = "SoccerHype"
PROJECT_URL = "https://github.com/johnahull/highlight_tool"
AUTHOR = "John Hull"
AUTHOR_EMAIL = "john@johnahull.com"
LICENSE = "MIT"

def get_version():
    """Return the version string."""
    return __version__

def get_version_info():
    """Return the version information as a dictionary."""
    return {
        "version": __version__,
        "version_info": __version_info__,
        "release_date": RELEASE_DATE,
        "project_name": PROJECT_NAME,
        "project_url": PROJECT_URL,
        "author": AUTHOR,
        "author_email": AUTHOR_EMAIL,
        "license": LICENSE,
    }

if __name__ == "__main__":
    print(f"{PROJECT_NAME} v{__version__}")
    print(f"Released: {RELEASE_DATE}")
    print(f"License: {LICENSE}")
    print(f"Project URL: {PROJECT_URL}")
