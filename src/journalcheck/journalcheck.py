#!/usr/bin/env python3
from __future__ import annotations

import sys
import traceback
from systemd import journal
import yaml
from pathlib import Path
import argparse
import json
import os
import subprocess
from datetime import datetime, timedelta
from typing import Any, Optional

from .config import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_CONFIG_DIR,
    DEFAULT_CURSOR_FILE,
    DEFAULT_EMAIL_SUBJECT,
    VALID_CONFIG_KEYS,
    Config,
    ConfigKeys,
    IdentifierConfigKeys,
    OutputFormat,
)

# Environment variable set by systemd service to suppress stdout
ENV_JOURNALCHECK_SERVICE = "JOURNALCHECK_SERVICE"


class JournalFields:
    SYSLOG_IDENTIFIER = "SYSLOG_IDENTIFIER"
    COMM = "_COMM"
    PID = "_PID"
    PRIORITY = "PRIORITY"
    MESSAGE = "MESSAGE"
    REALTIME_TIMESTAMP = "__REALTIME_TIMESTAMP"
    HOSTNAME = "_HOSTNAME"
    CURSOR = "__CURSOR"
    SEVERITY = "SEVERITY"
    BOOT_ID = "_BOOT_ID"


class Severity:
    VIOLATION = "VIOLATION"


BOOT_MARKER = "-- BOOT --"


def _merge_configs(data: dict[str, Any], loaded: dict[str, Any]) -> dict[str, Any]:
    """Merge a loaded configuration into existing configuration data.

    Scalar values are overwritten, while identifier ignore/violations
    lists are appended.

    Args:
        data: Existing configuration data to merge into
        loaded: New configuration data to merge from

    Returns:
        The merged configuration dictionary

    Raises:
        ValueError: If unknown configuration keys are found
    """
    unknown_keys = set(loaded.keys()) - VALID_CONFIG_KEYS
    if unknown_keys:
        raise ValueError(f"Unknown keys in config: {', '.join(sorted(unknown_keys))}")

    # copy all scalar configuration values, except for the identifiers,
    # which are handled differently.
    for key in loaded:
        if key != ConfigKeys.IDENTIFIERS:
            data[key] = loaded[key]

    if loaded.get(ConfigKeys.IDENTIFIERS) is not None:
        if not isinstance(loaded.get(ConfigKeys.IDENTIFIERS), dict):
            raise ValueError(
                f"{ConfigKeys.IDENTIFIERS} must be a dict, "
                f"got {type(loaded.get(ConfigKeys.IDENTIFIERS)).__name__}"
            )
        if ConfigKeys.IDENTIFIERS not in data:
            data[ConfigKeys.IDENTIFIERS] = {}
        for ident, ident_config in loaded[ConfigKeys.IDENTIFIERS].items():
            if ident in data[ConfigKeys.IDENTIFIERS]:
                # Merge: append ignore and violations lists
                existing = data[ConfigKeys.IDENTIFIERS][ident]
                if isinstance(existing, dict) and isinstance(ident_config, dict):
                    if IdentifierConfigKeys.IGNORE in ident_config:
                        existing.setdefault(IdentifierConfigKeys.IGNORE, []).extend(
                            ident_config[IdentifierConfigKeys.IGNORE]
                        )
                    if IdentifierConfigKeys.VIOLATIONS in ident_config:
                        existing.setdefault(IdentifierConfigKeys.VIOLATIONS, []).extend(
                            ident_config[IdentifierConfigKeys.VIOLATIONS]
                        )
                    if IdentifierConfigKeys.PRIORITY in ident_config:
                        existing[IdentifierConfigKeys.PRIORITY] = ident_config[
                            IdentifierConfigKeys.PRIORITY
                        ]
                else:
                    data[ConfigKeys.IDENTIFIERS][ident] = ident_config
            else:
                data[ConfigKeys.IDENTIFIERS][ident] = ident_config
    return data


def load_config(
    config_file_param: Optional[str] = None,
    priority_param: Optional[int] = None,
    output_format_param: Optional[str] = None,
) -> Config:
    """Load and merge configuration from file(s) and command-line parameters.

    Configuration is loaded from:
    1. Main config file (default: /etc/journalcheck.yaml)
    2. Config directory files (default: /etc/journalcheck.d/*.yaml, sorted)
    3. Command-line parameter overrides

    Args:
        config_file_param: Optional path to main config file (overrides default)
        priority_param: Optional priority level override from command line
        output_format_param: Optional output format override from command line

    Returns:
        Merged Config object

    Raises:
        FileNotFoundError: If specified config file doesn't exist
        ValueError: If configuration is invalid
    """
    config_file = Path(DEFAULT_CONFIG_FILE)
    config_dir: Path | None = Path(DEFAULT_CONFIG_DIR)

    data: dict[str, Any] = {}

    if config_file_param:
        config_file = Path(config_file_param)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        config_dir = None
    else:
        # Check for .yml alternative if .yaml doesn't exist
        if not config_file.exists():
            yml_alternative = config_file.with_suffix(".yml")
            if yml_alternative.exists():
                config_file = yml_alternative
        data[ConfigKeys.CURSOR_FILE] = DEFAULT_CURSOR_FILE

    config_files: list[Path] = []

    # Load main config file
    if config_file.exists():
        config_files.append(config_file)

    if config_dir and config_dir.exists() and config_dir.is_dir():
        yaml_files = list(config_dir.glob("*.yaml"))
        yml_files = list(config_dir.glob("*.yml"))
        config_files.extend(sorted(yaml_files + yml_files))

    for yaml_file in config_files:
        with open(yaml_file) as f:
            loaded = yaml.safe_load(f) or {}
            data = _merge_configs(data, loaded)

    if priority_param is not None:
        data[ConfigKeys.PRIORITY] = priority_param

    if output_format_param is not None:
        data[ConfigKeys.FORMAT] = output_format_param

    return Config.from_dict(data)


def get_identifier(entry: dict[str, Any]) -> str:
    """Extract the identifier from a journal entry.

    Returns SYSLOG_IDENTIFIER if present, otherwise _COMM, otherwise empty string.

    Args:
        entry: Journal entry dictionary

    Returns:
        Identifier string
    """
    syslog_id: Optional[str] = entry.get(JournalFields.SYSLOG_IDENTIFIER)
    comm: Optional[str] = entry.get(JournalFields.COMM)
    return syslog_id if syslog_id else comm if comm else ""


def format_identifier_with_pid(entry: dict[str, Any]) -> str:
    """Format identifier with PID for display.

    Formats as "identifier[pid]" or "(comm)[pid]" depending on what's available.

    Args:
        entry: Journal entry dictionary

    Returns:
        Formatted identifier string with PID
    """
    syslog_id: Optional[str] = entry.get(JournalFields.SYSLOG_IDENTIFIER)
    comm: Optional[str] = entry.get(JournalFields.COMM)
    pid: Any = entry.get(JournalFields.PID)

    if syslog_id:
        ident: str = syslog_id
    elif comm:
        ident = f"({comm})"
    else:
        ident = ""

    if pid:
        ident = f"{ident}[{pid}]"

    return ident


def should_show_entry(entry: dict[str, Any], config: Config) -> tuple[bool, str]:
    """Determine if a journal entry should be shown based on configuration.

    Decision logic:
    1. Violation patterns always match (highest priority)
    2. Priority filtering (entry priority must be <= configured priority)
    3. Ignore patterns suppress matching messages (lowest priority)

    Args:
        entry: Journal entry dictionary
        config: Configuration object

    Returns:
        Tuple of (should_show, severity_marker)
        - should_show: True if entry should be displayed
        - severity_marker: "VIOLATION" if matched violation pattern, else ""
    """
    ident: str = get_identifier(entry)
    priority: int = entry.get(JournalFields.PRIORITY, 6)
    message: str = entry.get(JournalFields.MESSAGE, "")

    # Get effective config for this identifier
    effective_priority, ident_config = config.get_config_for_identifier(ident)

    # Check violations first (always shown)
    for pattern in ident_config._compiled_violations:
        if pattern.search(message):
            return True, Severity.VIOLATION

    # Check priority
    if priority > effective_priority:
        return False, ""

    # Check ignore patterns last (with implicit anchors)
    for pattern in ident_config._compiled_ignore:
        if pattern.fullmatch(message):
            return False, ""

    return True, ""


def format_entry(
    entry: dict[str, Any], format_type: OutputFormat, severity: str = ""
) -> str:
    """Format a journal entry for output.

    Args:
        entry: Journal entry dictionary
        format_type: Output format (SHORT or JSON)
        severity: Optional severity marker (e.g., "VIOLATION")

    Returns:
        Formatted entry string
    """
    if format_type == OutputFormat.JSON:
        result: dict[str, Any] = dict(entry)
        if severity:
            result[JournalFields.SEVERITY] = severity
        return json.dumps(result, default=str)
    else:
        timestamp: Any = entry.get(JournalFields.REALTIME_TIMESTAMP)
        if timestamp is None:
            timestamp = datetime.now()
        if isinstance(timestamp, datetime):
            ts_str: str = timestamp.strftime("%b %d %H:%M:%S")
        else:
            ts_str = str(timestamp)
        hostname: str = entry.get(JournalFields.HOSTNAME, "")
        ident: str = format_identifier_with_pid(entry)
        message: str = entry.get(JournalFields.MESSAGE, "")
        severity_marker: str = f" [{severity}]" if severity else ""
        return f"{ts_str} {hostname} {ident}{severity_marker}: {message}"


def _parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Optional argument list (defaults to sys.argv)

    Returns:
        Parsed arguments namespace
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Config file path")
    parser.add_argument("-p", "--priority", type=int, help="Priority level")
    parser.add_argument(
        "-o", "--output", choices=list(OutputFormat), help="Output format"
    )
    parser.add_argument(
        "-t", "--test", action="store_true", help="Test mode: do not update cursor file"
    )
    parser.add_argument(
        "--show-config", action="store_true", help="Show merged configuration and exit"
    )
    return parser.parse_args(args)


def save_cursor(cursor_file: Path, entry: dict[str, Any]) -> None:
    """Save the journal cursor to a file for tracking position.

    Args:
        cursor_file: Path where the cursor should be saved
        entry: Journal entry containing the cursor

    Raises:
        OSError: If cursor file cannot be created or written
    """
    last_cursor: Any = entry.get(JournalFields.CURSOR)
    if not last_cursor:
        return

    try:
        cursor_file.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(
            f"Failed to create cursor directory {cursor_file.parent}: {e}"
        ) from e

    try:
        with open(cursor_file, "w") as f:
            f.write(str(last_cursor))
    except OSError as e:
        raise OSError(f"Failed to write cursor file {cursor_file}: {e}") from e


def run(reader: journal.Reader, args: Optional[list[str]] = None) -> None:
    """Main execution logic for processing journal entries.

    Loads configuration, processes journal entries according to filters,
    and outputs results via configured methods (stdout, command, email).

    Note: Reboot detection only works in SHORT output format.

    Args:
        reader: systemd journal reader instance
        args: Optional command-line arguments

    Raises:
        OSError: If cursor file cannot be saved
        ValueError: If configuration is invalid
    """
    parsed_args: argparse.Namespace = _parse_args(args)
    config: Config = load_config(
        config_file_param=parsed_args.config,
        priority_param=parsed_args.priority,
        output_format_param=parsed_args.output,
    )

    if parsed_args.show_config:
        print(yaml.dump(config.to_dict(), default_flow_style=False, sort_keys=False))
        return

    cursor_file: Path | None = Path(config.cursor_file) if config.cursor_file else None
    last_boot_id: str | None = None

    if cursor_file:
        if cursor_file.exists():
            with open(cursor_file) as f:
                cursor: str = f.read().strip()
                if cursor:
                    reader.seek_cursor(cursor)
                    prev_entry = reader.get_next()
                    if prev_entry:
                        last_boot_id = prev_entry.get(JournalFields.BOOT_ID)
        else:
            # If cursor file is configured but doesn't exist, seek to last 24 hours
            since: datetime = datetime.now() - timedelta(days=1)
            reader.seek_realtime(since)  # type: ignore[attr-defined]

    # Collect output
    output_lines: list[str] = []
    entry: dict[str, Any] | None = None
    for entry in reader:
        show, severity = should_show_entry(entry, config)
        if show:
            # Check for reboot
            if config.format == OutputFormat.SHORT:
                this_boot_id = entry.get(JournalFields.BOOT_ID)
                if last_boot_id and this_boot_id and this_boot_id != last_boot_id:
                    output_lines.append(BOOT_MARKER)
                last_boot_id = this_boot_id

            output_lines.append(format_entry(entry, config.format, severity))

    if not output_lines:
        return

    # Handle output
    output_text = "\n".join(output_lines)

    if not os.getenv(ENV_JOURNALCHECK_SERVICE):
        print(output_text)

    if config.output_command:
        subprocess.run(config.output_command, shell=True, input=output_text, text=True)

    if config.email_to:
        subprocess.run(
            [
                "mail",
                "-s",
                config.email_subject if config.email_subject else DEFAULT_EMAIL_SUBJECT,
                config.email_to,
            ],
            input=output_text,
            text=True,
        )

    # Save cursor
    if cursor_file and not parsed_args.test and entry:
        save_cursor(cursor_file, entry)


def main() -> None:
    """Entry point for journalcheck command.

    Handles top-level exception catching and exit codes.

    Exit codes:
        0: Success
        1: Error (configuration, file not found, OS error, or unexpected error)
    """
    try:
        run(journal.Reader())
    except yaml.YAMLError as e:
        print(f"Error parsing the configuration: {e}", file=sys.stderr)
        sys.exit(1)

    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception:
        print("Unexpected Error:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
