#!/usr/bin/env python3
from systemd import journal
import yaml
from pathlib import Path
import argparse
import json
import re
from datetime import datetime, timedelta
from typing import Any, Optional

from .config import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_CONFIG_DIR,
    DEFAULT_CURSOR_FILE,
    Config,
)


def load_config(
    config_file_param: Optional[str] = None,
    priority_param: Optional[int] = None,
    output_format_param: Optional[str] = None,
) -> Config:
    config_file = Path(DEFAULT_CONFIG_FILE)
    config_dir: Path | None = Path(DEFAULT_CONFIG_DIR)
    use_default_cursor = True

    if config_file_param:
        config_file = Path(config_file_param)
        config_dir = None
        use_default_cursor = False

    data: dict[str, Any] = {}

    # Load main config file
    if config_file.exists():
        with open(config_file) as f:
            data = yaml.safe_load(f) or {}

    # Load additional configs from /etc/journalcheck.d/
    if config_dir and config_dir.exists() and config_dir.is_dir():
        for yaml_file in sorted(config_dir.glob("*.yaml")):
            with open(yaml_file) as f:
                loaded = yaml.safe_load(f) or {}
                if "identifiers" in loaded:
                    if "identifiers" not in data:
                        data["identifiers"] = {}
                    for ident, ident_config in loaded["identifiers"].items():
                        if ident in data["identifiers"]:
                            # Merge: append ignore and violations lists
                            existing = data["identifiers"][ident]
                            if isinstance(existing, dict) and isinstance(
                                ident_config, dict
                            ):
                                if "ignore" in ident_config:
                                    existing.setdefault("ignore", []).extend(
                                        ident_config["ignore"]
                                    )
                                if "violations" in ident_config:
                                    existing.setdefault("violations", []).extend(
                                        ident_config["violations"]
                                    )
                                if "priority" in ident_config:
                                    existing["priority"] = ident_config["priority"]
                            else:
                                data["identifiers"][ident] = ident_config
                        else:
                            data["identifiers"][ident] = ident_config
                if "priority" in loaded:
                    data["priority"] = loaded["priority"]
                if "format" in loaded:
                    data["format"] = loaded["format"]
                if "cursor_file" in loaded:
                    data["cursor_file"] = loaded["cursor_file"]

    if priority_param is not None:
        data["priority"] = priority_param

    if output_format_param is not None:
        data["format"] = output_format_param

    if use_default_cursor and "cursor_file" not in data:
        data["cursor_file"] = DEFAULT_CURSOR_FILE

    return Config.from_dict(data)


def get_identifier(entry: dict[str, Any]) -> str:
    syslog_id: Optional[str] = entry.get("SYSLOG_IDENTIFIER")
    comm: Optional[str] = entry.get("_COMM")
    return syslog_id if syslog_id else comm if comm else ""


def format_identifier_with_pid(entry: dict[str, Any]) -> str:
    syslog_id: Optional[str] = entry.get("SYSLOG_IDENTIFIER")
    comm: Optional[str] = entry.get("_COMM")
    pid: Any = entry.get("_PID")

    if syslog_id:
        ident: str = syslog_id
        if pid:
            ident = f"{ident}[{pid}]"
    elif comm:
        ident = f"({comm})"
        if pid:
            ident = f"({comm})[{pid}]"
    else:
        ident = ""

    return ident


def should_show_entry(entry: dict[str, Any], config: Config) -> tuple[bool, str]:
    ident: str = get_identifier(entry)
    priority: int = entry.get("PRIORITY", 6)
    message: str = entry.get("MESSAGE", "")

    # Get effective config for this identifier
    effective_priority, violations, ignore = config.get_config_for_identifier(ident)

    # Check violations first (always shown)
    for pattern in violations:
        if re.search(pattern, message):
            return True, "VIOLATION"

    # Check priority
    if priority > effective_priority:
        return False, ""

    # Check ignore patterns last (with implicit anchors)
    for pattern in ignore:
        if re.fullmatch(pattern, message):
            return False, ""

    return True, ""


def format_entry(entry: dict[str, Any], format_type: str, severity: str = "") -> str:
    if format_type == "json":
        result: dict[str, Any] = dict(entry)
        if severity:
            result["SEVERITY"] = severity
        return json.dumps(result, default=str)
    else:
        timestamp: Any = entry.get("__REALTIME_TIMESTAMP", datetime.now())
        if isinstance(timestamp, datetime):
            ts_str: str = timestamp.strftime("%b %d %H:%M:%S")
        else:
            ts_str = str(timestamp)
        hostname: str = entry.get("_HOSTNAME", "")
        ident: str = format_identifier_with_pid(entry)
        message: str = entry.get("MESSAGE", "")
        severity_marker: str = f" [{severity}]" if severity else ""
        return f"{ts_str} {hostname} {ident}{severity_marker}: {message}"


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Config file path")
    parser.add_argument("-p", "--priority", type=int, help="Priority level")
    parser.add_argument(
        "-o", "--output", choices=["short", "json"], help="Output format"
    )
    return parser.parse_args(args)


def main() -> None:
    args: argparse.Namespace = parse_args()
    config: Config = load_config(
        config_file_param=args.config,
        priority_param=args.priority,
        output_format_param=args.output,
    )

    j: journal.Reader = journal.Reader()

    cursor_file: Path | None = Path(config.cursor_file) if config.cursor_file else None
    cursor_loaded: bool = False

    if cursor_file and cursor_file.exists():
        with open(cursor_file) as f:
            cursor: str = f.read().strip()
            if cursor:
                j.seek_cursor(cursor)
                j.get_next()
                cursor_loaded = True

    if not cursor_loaded:
        # Default to last 24 hours if no cursor
        since: datetime = datetime.now() - timedelta(days=1)
        j.seek_realtime(since)  # type: ignore[attr-defined]

    # Collect output
    output_lines: list[str] = []
    for entry in j:
        show, severity = should_show_entry(entry, config)
        if show:
            output_lines.append(format_entry(entry, config.format, severity))

    # Handle output
    if output_lines:
        output_text = "\n".join(output_lines)

        if config.output_command:
            # Pipe to command
            import subprocess

            subprocess.run(
                config.output_command, shell=True, input=output_text, text=True
            )
        elif config.email_to:
            # Send via email
            import subprocess

            subprocess.run(
                ["mail", "-s", config.email_subject, config.email_to],
                input=output_text,
                text=True,
            )
        else:
            # Print to stdout
            print(output_text)

    # Save cursor
    if cursor_file and output_lines:
        last_cursor: Any = entry.get("__CURSOR")
        if last_cursor:
            cursor_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cursor_file, "w") as f:
                f.write(str(last_cursor))


if __name__ == "__main__":
    main()
