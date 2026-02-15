# journalcheck

[![CI](https://github.com/gms1/journalcheck/actions/workflows/ci.yml/badge.svg)](https://github.com/gms1/journalcheck/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/gms1/journalcheck/branch/main/graph/badge.svg)](https://codecov.io/gh/gms1/journalcheck)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/gms1/journalcheck/pulls)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A Python package for checking systemd journal entries with configurable priority filtering, pattern matching, and security violation detection.

Inspired by [logcheck](https://packages.debian.org/stable/logcheck), but designed for systemd's journal with output that can be piped to other programs for notifications, monitoring, or alerting.

## Key Differences from logcheck

- **Priority-based filtering**: Filter messages by systemd priority levels (emerg, alert, crit, err, warning, notice, info, debug) - logcheck only supports pattern matching
- **Per-service priority control**: Set different priority thresholds for different services without writing individual ignore patterns
- **Flexible output**: Pipe to any command, send via email, or output to stdout - not limited to email only
- **JSON output**: Machine-readable format for integration with monitoring systems
- **Cursor-based tracking**: Only process new entries since last run using systemd journal cursors

## Features

- Priority-based filtering (emerg, alert, crit, err, warning, notice, info, debug)
- Per-identifier priority configuration
- Regex pattern matching for identifiers
- Two-level pattern hierarchy:
  - **Violations**: Always shown (e.g., failed logins, security events)
  - **Ignore**: Suppress matching messages (exact match)
- Pre-configured violation patterns for common services (sshd, sudo, su)
- Cursor-based tracking (only process new entries)
- Multiple output formats (short, json)
- Modular configuration via `/etc/journalcheck.yaml` and `/etc/journalcheck.d/*.yaml`

## Installation

```bash
pip install -e .
```

## Configuration

Main config: `/etc/journalcheck.yaml`

Additional configs: `/etc/journalcheck.d/*.yaml` (merged automatically)

Example:
```yaml
priority: warning
format: short

# Optional: pipe output to a command
output_command: "notify-send 'Journal Alert'"

# Optional: send output via email
email_to: "admin@example.com"
email_subject: "Journal Alerts"

identifiers:
  ssh:
    priority: info
    ignore:
      - ".*Accepted publickey.*"
    violations:
      - "Failed password"
```

**Output Options:**
- If `output_command` is set, output will be piped to that command
- If `email_to` is set (and no `output_command`), output will be sent via email using the `mail` command
- If neither is set, output goes to stdout (default)

## Default Violations

The following identifiers have pre-configured violation patterns that are automatically included:

- **sshd**: Failed password, Invalid user, Connection closed by authenticating user, etc.
- **sudo**: authentication failure, user NOT in sudoers, incorrect password attempt
- **su**: FAILED su, authentication failure
- **smartd**: SMART Failure, Attribute.*failed, Error.*occurred
- **kernel**: I/O error, Buffer I/O error, end_request: I/O error

You can add additional violations to these identifiers - they will be appended to the defaults.
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Repository

https://github.com/gms1/journalcheck


## Usage

### Basic usage
```bash
journalcheck
```

### Pipe to notification system
```bash
journalcheck | while read line; do notify-send "Journal Alert" "$line"; done
```

### Pipe to email
```bash
journalcheck | mail -s "Journal Alerts" admin@example.com
```

### Pipe to monitoring system
```bash
journalcheck -o json | your-monitoring-tool
```

### Run via systemd timer
The package includes systemd service and timer units for automated checking.
