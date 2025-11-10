# Contributing to SoccerHype

Thank you for your interest in contributing to SoccerHype! While this project is currently maintained primarily by its author, we welcome bug reports, documentation improvements, and well-considered pull requests.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Submitting Changes](#submitting-changes)
- [Security Guidelines](#security-guidelines)

## Code of Conduct

This project adheres to the Contributor Covenant [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to john@johnahull.com.

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title** describing the problem
- **Detailed steps** to reproduce the issue
- **Expected vs actual behavior**
- **Environment details**: OS, Python version, FFmpeg version
- **Log output** or error messages (if applicable)
- **Video file details** (codec, resolution, frame rate) if relevant

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Clear title** describing the enhancement
- **Detailed description** of the proposed functionality
- **Use case**: Why is this enhancement useful?
- **Examples**: Mockups, code snippets, or workflows

### Pull Requests

We accept pull requests for:

- Bug fixes
- Documentation improvements
- Code quality improvements (performance, readability)
- New features (please open an issue first to discuss)

**Note**: For significant new features, please open an issue for discussion before investing time in development.

## Development Setup

### Prerequisites

- Python 3.9 or higher
- FFmpeg with libx264 and libfreetype support
- Git

### Setup Steps

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/YOUR-USERNAME/highlight_tool.git
   cd highlight_tool
   ```

2. **Run the setup script**:
   ```bash
   ./setup.sh
   # Or for enhanced features:
   ./setup_enhanced.sh
   ```

3. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

4. **Verify installation**:
   ```bash
   python -c "import yaml, tkinter; print('Dependencies OK')"
   ffmpeg -version | grep libx264
   ```

## Coding Standards

### Python Style Guide

- **Follow PEP 8** for code style
- **Use descriptive variable names**
- **Add docstrings** to functions and classes
- **Type hints** are encouraged for new code
- **Line length**: Prefer 88 characters (Black formatter default)

### Security Best Practices

**🔒 CRITICAL**: Always follow these security guidelines:

1. **PII Protection**:
   - Never commit files containing personal information
   - Check `.gitignore` includes sensitive files
   - Validate `players_database.json` is excluded

2. **Input Validation**:
   - Sanitize all user inputs (profile IDs, file names, form data)
   - Use regex validation for structured data (emails, etc.)
   - Implement length limits and character restrictions

3. **Path Traversal Prevention**:
   - Always validate file paths are within expected directories
   - Use `pathlib.Path.resolve()` to canonicalize paths
   - Never trust user-provided paths without validation

4. **Subprocess Security**:
   - Always use `subprocess.run(shell=False)`
   - Pass arguments as lists, not concatenated strings
   - Add timeout protection for external commands
   - Validate executable paths before calling

5. **Atomic File Operations**:
   - Use temp file + rename pattern for critical data
   - Prevent data corruption during writes
   - Example:
     ```python
     tmp_path = f"{target_path}.tmp"
     with open(tmp_path, 'w') as f:
         # write data
     os.replace(tmp_path, target_path)  # atomic
     ```

### Code Organization

- **Keep functions focused**: One function, one responsibility
- **Avoid deep nesting**: Extract complex logic into helper functions
- **Error handling**: Use try/except blocks appropriately
- **Logging**: Use descriptive error messages

## Testing Guidelines

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_profile_manager.py

# Run with coverage
pytest --cov=. --cov-report=html
```

### Writing Tests

- **Test new functionality**: All new features should include tests
- **Test edge cases**: Empty inputs, large files, invalid data
- **Test security**: Validate input sanitization, path validation
- **Use fixtures**: For common setup/teardown
- **Mock external calls**: Mock FFmpeg calls, file I/O when appropriate

### Security Testing Checklist

When adding code that handles user input or files:

- [ ] Path traversal protection tested
- [ ] Input validation implemented
- [ ] Subprocess calls use safe patterns
- [ ] PII not exposed in error messages
- [ ] File operations are atomic
- [ ] Tests cover malicious inputs

## Submitting Changes

### Commit Message Guidelines

- **Use clear, descriptive commit messages**
- **Start with a verb**: "Add", "Fix", "Update", "Remove", etc.
- **Reference issues**: Include "Fixes #123" or "Closes #456"
- **Keep commits focused**: One logical change per commit

Examples:
```
Add ring radius validation in mark_play.py

Fix path traversal vulnerability in create_athlete.py
Fixes #42

Update README with troubleshooting section
```

### Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b fix/issue-description
   ```

2. **Make your changes** following coding standards

3. **Add tests** for new functionality

4. **Run the test suite**:
   ```bash
   pytest
   ```

5. **Update documentation** if needed

6. **Push to your fork**:
   ```bash
   git push origin fix/issue-description
   ```

7. **Open a pull request** with:
   - Clear title describing the change
   - Description of what changed and why
   - Reference to related issues
   - Screenshots/examples if relevant

8. **Respond to review feedback** promptly

### PR Review Criteria

Your PR will be reviewed for:

- ✅ **Functionality**: Does it work as intended?
- ✅ **Code quality**: Is it readable, maintainable, well-structured?
- ✅ **Security**: Does it follow security best practices?
- ✅ **Tests**: Are there adequate tests?
- ✅ **Documentation**: Is documentation updated?
- ✅ **Compatibility**: Does it work across platforms (Linux, Windows, macOS)?

## Project Structure

```
highlight_tool/
├── athletes/              # Athlete project directories
├── tests/                 # Test files
├── .github/              # GitHub workflows and templates
├── *.py                  # Main Python modules
├── requirements.txt      # Python dependencies
├── setup.sh             # Setup script
├── CLAUDE.md            # Developer documentation
├── PACKAGING.md         # Packaging instructions
└── ENHANCEMENTS.md      # Enhancement documentation
```

### Key Modules

- **create_athlete.py**: Folder structure creation
- **mark_play.py**: Interactive video marking interface
- **render_highlight.py**: FFmpeg video rendering
- **profile_manager.py**: Player profile management
- **ffmpeg_utils.py**: FFmpeg detection and utilities
- **error_handling.py**: Custom error classes
- **soccerhype_gui.py**: GUI application

## Getting Help

- **Documentation**: Start with [CLAUDE.md](CLAUDE.md) for comprehensive technical details
- **Issues**: Check [existing issues](https://github.com/johnahull/highlight_tool/issues) for known problems
- **Questions**: Open a GitHub issue with the "question" label
- **Contact**: Email john@johnahull.com for private inquiries

## Recognition

Contributors will be acknowledged in:

- Release notes
- CHANGELOG.md
- GitHub contributors page

Thank you for contributing to SoccerHype!

---

*Last updated: 2025-01-10*
