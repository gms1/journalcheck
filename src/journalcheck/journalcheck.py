#!/usr/bin/env python3
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
    VALID_CONFIG_KEYS,
    Config,
    ConfigKeys,
    IdentifierConfigKeys,
)


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


def _merge_configs(data: dict[str, Any], loaded: dict[str, Any]) -> dict[str, Any]:
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
    syslog_id: Optional[str] = entry.get(JournalFields.SYSLOG_IDENTIFIER)
    comm: Optional[str] = entry.get(JournalFields.COMM)
    return syslog_id if syslog_id else comm if comm else ""


def format_identifier_with_pid(entry: dict[str, Any]) -> str:
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


def format_entry(entry: dict[str, Any], format_type: str, severity: str = "") -> str:
    if format_type == "json":
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


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Config file path")
    parser.add_argument("-p", "--priority", type=int, help="Priority level")
    parser.add_argument(
        "-o", "--output", choices=["short", "json"], help="Output format"
    )
    parser.add_argument(
        "-t", "--test", action="store_true", help="Test mode: do not update cursor file"
    )
    parser.add_argument(
        "--show-config", action="store_true", help="Show merged configuration and exit"
    )
    return parser.parse_args(args)


def run(reader: journal.Reader, args: Optional[list[str]] = None) -> None:
    parsed_args: argparse.Namespace = parse_args(args)
    config: Config = load_config(
        config_file_param=parsed_args.config,
        priority_param=parsed_args.priority,
        output_format_param=parsed_args.output,
    )

    if parsed_args.show_config:
        print(yaml.dump(config.to_dict(), default_flow_style=False, sort_keys=False))
        return

    cursor_file: Path | None = Path(config.cursor_file) if config.cursor_file else None

    if cursor_file:
        if cursor_file.exists():
            with open(cursor_file) as f:
                cursor: str = f.read().strip()
                if cursor:
                    reader.seek_cursor(cursor)
                    reader.get_next()
        else:
            # If cursor file is configured but doesn't exist, seek to last 24 hours
            since: datetime = datetime.now() - timedelta(days=1)
            reader.seek_realtime(since)  # type: ignore[attr-defined]

    # Collect output
    output_lines: list[str] = []
    last_boot_id: str | None = None
    for entry in reader:
        show, severity = should_show_entry(entry, config)
        if show:
            # Check for reboot (only for non-json format)
            if config.format != "json":
                this_boot_id = entry.get(JournalFields.BOOT_ID)
                if last_boot_id and this_boot_id and this_boot_id != last_boot_id:
                    output_lines.append("-- Reboot --")
                last_boot_id = this_boot_id

            output_lines.append(format_entry(entry, config.format, severity))

    if not output_lines:
        return

    # Handle output
    output_text = "\n".join(output_lines)

    if not os.getenv("JOURNALCHECK_SERVICE"):
        print(output_text)

    if config.output_command:
        subprocess.run(config.output_command, shell=True, input=output_text, text=True)

    if config.email_to:
        subprocess.run(
            ["mail", "-s", config.email_subject, config.email_to],
            input=output_text,
            text=True,
        )

    # Save cursor
    if cursor_file and not parsed_args.test:
        last_cursor: Any = entry.get(JournalFields.CURSOR)
        if last_cursor:
            cursor_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cursor_file, "w") as f:
                f.write(str(last_cursor))


def main() -> None:
    try:
        run(journal.Reader())
    except yaml.YAMLError as e:
        print(f"Error parsing the configuration: {e}", file=sys.stderr)
        sys.exit(1)

    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception:
        print("Unexpected Error:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
