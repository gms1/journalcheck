# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Features

### Fixes

- fixed unexpected error: Unknown keys in config: output_command

## [0.0.5] - 2026-02-21

### Featurs
- Initial release
- Priority-based filtering with systemd journal integration
- Per-identifier priority configuration
- Regex pattern matching for identifiers (case-sensitive with (?i) support)
- Case-insensitive ignore and violation patterns
- Pre-configured violation patterns for common services (sshd, sudo, su, smartd, kernel)
- Cursor-based tracking to process only new entries
- Multiple output formats (short, json)
- Modular configuration via `/etc/journalcheck.yaml` and `/etc/journalcheck.d/*.yaml`
- Systemd timer integration for automated checking
- Output piping to commands or email
- `--test` flag to run without updating cursor
- `--show-config` flag to display merged configuration
- PyPI package distribution
- Debian package distribution
- CI/CD with GitHub Actions
- Test suite with 95% coverage

[Unreleased]: https://github.com/gms1/journalcheck/compare/v0.0.5...HEAD
[0.0.5]: https://github.com/gms1/journalcheck/releases/tag/v0.0.5
