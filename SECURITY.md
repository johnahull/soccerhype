# Security Policy

## Supported Versions

Currently, SoccerHype is in active development. Security updates are provided for the latest version only.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of SoccerHype seriously. If you discover a security vulnerability, please follow these steps:

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by:

1. **Email**: Send details to john@johnahull.com
2. **Subject Line**: Use "SoccerHype Security Vulnerability" in the subject
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact
   - Suggested fix (if you have one)

### What to Expect

- **Acknowledgment**: You should receive a response within 48 hours acknowledging receipt of your report
- **Updates**: We will keep you informed about our progress addressing the vulnerability
- **Timeline**: We aim to release a fix within 7-14 days for critical vulnerabilities
- **Credit**: With your permission, we will acknowledge your contribution in the release notes

### Security Best Practices for Users

When using SoccerHype, follow these security guidelines:

1. **Protect PII**: Never commit `players_database.json` or files containing personal information
2. **Validate Inputs**: Be cautious when processing untrusted video files
3. **Update Regularly**: Keep SoccerHype and its dependencies (FFmpeg, Python packages) up to date
4. **Review Code**: Examine any custom scripts or modifications before running them
5. **File Permissions**: Ensure sensitive files have appropriate permissions (e.g., 600 for player database)

### Known Security Features

SoccerHype implements several security measures:

- **Path Traversal Protection**: All file operations validate paths are within expected directories
- **Command Injection Prevention**: Uses `subprocess.run(shell=False)` with argument lists
- **Input Validation**: Sanitizes user inputs including profile IDs, file names, and form data
- **Atomic File Operations**: Uses temp file + rename pattern to prevent data corruption
- **PII Protection**: Automatically excludes sensitive data from version control

### Scope

The following are considered **in scope** for security reports:

- Command injection vulnerabilities
- Path traversal vulnerabilities
- Arbitrary code execution
- Data exposure or PII leaks
- Authentication/authorization bypasses
- Dependency vulnerabilities (with proof of exploitability)

The following are **out of scope**:

- Social engineering attacks
- Physical attacks
- Denial of service through resource exhaustion (expected for large video files)
- Issues in third-party dependencies without proof of impact on SoccerHype
- Vulnerabilities requiring significant user configuration errors

## Security Update Process

When a security vulnerability is confirmed:

1. A fix will be developed and tested
2. A new version will be released with security patches
3. A security advisory will be published on GitHub
4. The CHANGELOG will document the fix (without disclosing exploit details)
5. Users will be notified through GitHub release notes

## Questions?

If you have questions about this security policy, please open a GitHub issue or contact john@johnahull.com.

---

*Last updated: 2025-01-10*
