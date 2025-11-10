# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-01-10

### Added
- **Core Video Processing**
  - Interactive video player for marking athlete positions with red spotlight rings
  - Automated video clip proxy generation with standardized 1920px-wide format
  - FFmpeg-based rendering with high-quality output (CRF 18)
  - Batch processing support for multiple athletes with parallel execution
  - Customizable intro slates with player pictures or video backgrounds

- **GUI Applications**
  - Unified GUI application (`soccerhype_gui.py`) for complete workflow
  - Enhanced marking interface with smart defaults and templates
  - Visual clip reordering with thumbnail preview
  - Comprehensive player profile management with PII protection

- **Standalone Application Packaging**
  - PyInstaller configuration for Windows and macOS distributions
  - Automated build scripts (`build_windows.bat`, `build_macos.sh`)
  - FFmpeg bundling utility with automatic detection
  - Cross-platform FFmpeg detection and fallback support

- **Security Features**
  - Path traversal protection for all file operations
  - Command injection prevention with safe subprocess calls
  - Input validation and sanitization for user data
  - Atomic file operations to prevent data corruption
  - PII protection with automatic exclusion from version control

- **Testing & Quality**
  - Comprehensive test suite with pytest
  - Security testing for path traversal and input validation
  - Profile manager tests with edge case coverage
  - Enhanced error handling framework

- **Documentation**
  - Comprehensive developer guide (CLAUDE.md)
  - Detailed packaging instructions (PACKAGING.md)
  - Enhancement documentation (ENHANCEMENTS.md)
  - Setup scripts for automated installation

### Fixed
- Rendering issues and data loss prevention in GUI workflows
- Intro media selection and profile autofill bugs
- Clip preview bugs after drag reordering
- Layout overlap in Player Information dialog
- Critical security vulnerabilities in packaging infrastructure
- Code quality issues identified in security reviews

### Changed
- Separated profile management from clip marking workflow for better modularity
- Extracted shared PlayerProfileManager to reduce code duplication
- Improved atomic file operations for data integrity
- Enhanced subprocess security across all modules

### Security
- Implemented comprehensive PII protection system
- Added players_database.json to .gitignore
- Fixed path traversal vulnerabilities
- Secured all subprocess calls with shell=False
- Added input sanitization for profile IDs and file names

## Project Information

**Repository**: https://github.com/johnahull/highlight_tool
**License**: MIT License
**Author**: John Hull

---

[Unreleased]: https://github.com/johnahull/highlight_tool/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/johnahull/highlight_tool/releases/tag/v0.1.0
