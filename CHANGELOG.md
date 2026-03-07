# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- improved configuration validation
- small refactoring

## [1.0.1] - 2026-03-01

- print to stdout even if other output options are enabled
- display the order of the identifiers in --show-config as they are handled
- fixed applying default violations
- small refactorings

## [1.0.0] - 2026-02-22

- first stable version

## [0.0.8] - 2026-02-22

### Features
- apt repository for Debian and Ubuntu

### Fixes

- fixed unexpected error: Unknown keys in config: output_command
- fixed missing properties when merging

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

[Unreleased]: https://github.com/gms1/journalcheck/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/gms1/journalcheck/releases/tag/v1.0.1
[1.0.0]: https://github.com/gms1/journalcheck/releases/tag/v1.0.0
[0.0.8]: https://github.com/gms1/journalcheck/releases/tag/v0.0.8
[0.0.5]: https://github.com/gms1/journalcheck/releases/tag/v0.0.5
