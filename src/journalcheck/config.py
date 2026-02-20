import re
from dataclasses import dataclass, field
from typing import Any, cast

PRIORITY_NAMES: dict[str, int] = {
    "emerg": 0,
    "alert": 1,
    "crit": 2,
    "err": 3,
    "warning": 4,
    "notice": 5,
    "info": 6,
    "debug": 7,
}

PRIORITY_NUMBERS: dict[int, str] = {
    0: "emerg",
    1: "alert",
    2: "crit",
    3: "err",
    4: "warning",
    5: "notice",
    6: "info",
    7: "debug",
}

DEFAULT_CONFIG_FILE: str = "/etc/journalcheck.yaml"
DEFAULT_CONFIG_DIR = "/etc/journalcheck.d"
DEFAULT_CURSOR_FILE = "/var/lib/journalcheck/cursor"


class IdentifierConfigKeys:
    PRIORITY = "priority"
    IGNORE = "ignore"
    VIOLATIONS = "violations"


class ConfigKeys:
    PRIORITY = "priority"
    FORMAT = "format"
    CURSOR_FILE = "cursor_file"
    OUTPUT_COMMAND = "output_command"
    EMAIL_TO = "email_to"
    EMAIL_SUBJECT = "email_subject"
    IDENTIFIERS = "identifiers"


DEFAULT_VIOLATIONS: dict[str, list[str]] = {
    "kernel": [
        "I/O error",
        "Out of memory",
        "Killed process",
    ],
    "sshd": [
        "Invalid user",
        "Failed password",
        "Connection closed by authenticating user",
    ],
    "sudo": [
        "authentication failure",
        "incorrect password attempt",
        "unknown user",
        "user NOT in sudoers",
    ],
    "su": [
        "FAILED SU",
        "authentication failed",
    ],
    "smartd": [
        "SMART Failure",
        "reached.*limit",
        "Currently unreadable.*sectors",
        "Offline uncorrectable sectors",
    ],
}


@dataclass
class IdentifierConfig:
    priority: int | None = None
    ignore: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.priority is not None and not 0 <= self.priority <= 7:
            raise ValueError(f"Priority must be 0-7, got {self.priority}")
        if not isinstance(self.ignore, list):
            raise ValueError(f"ignore must be a list, got {type(self.ignore).__name__}")
        if not isinstance(self.violations, list):
            raise ValueError(
                f"violations must be a list, got {type(self.violations).__name__}"
            )
        for pattern in self.ignore + self.violations:
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}")

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], identifier: str = ""
    ) -> "IdentifierConfig":
        valid_keys = {
            IdentifierConfigKeys.PRIORITY,
            IdentifierConfigKeys.IGNORE,
            IdentifierConfigKeys.VIOLATIONS,
        }
        unknown_keys = set(data.keys()) - valid_keys
        if unknown_keys:
            raise ValueError(
                f"Unknown keys in identifier config: {', '.join(sorted(unknown_keys))}"
            )

        priority = data.get(IdentifierConfigKeys.PRIORITY)
        if priority is not None and isinstance(priority, str):
            priority = PRIORITY_NAMES.get(priority.lower())

        # Start with default violations for this identifier
        violations: list[str] = list(DEFAULT_VIOLATIONS.get(identifier, []))
        # Append user-configured violations
        if data.get(IdentifierConfigKeys.VIOLATIONS):
            violations.extend(
                cast(list[str], data.get(IdentifierConfigKeys.VIOLATIONS))
            )

        ignore = data.get(IdentifierConfigKeys.IGNORE)
        if not ignore:
            ignore = []

        return cls(
            priority=priority,
            ignore=ignore,
            violations=violations,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.priority is not None:
            result[IdentifierConfigKeys.PRIORITY] = PRIORITY_NUMBERS[self.priority]
        result[IdentifierConfigKeys.IGNORE] = self.ignore
        result[IdentifierConfigKeys.VIOLATIONS] = self.violations
        return result


@dataclass
class Config:
    priority: int = 6
    format: str = "short"
    cursor_file: str | None = None
    output_command: str | None = None
    email_to: str | None = None
    email_subject: str = "Journal Alerts"
    identifiers: dict[str, IdentifierConfig] = field(default_factory=dict)

    def __post_init__(self):
        if not 0 <= self.priority <= 7:
            raise ValueError(f"Priority must be 0-7, got {self.priority}")
        if self.format not in ["short", "json"]:
            raise ValueError(f"Format must be 'short' or 'json', got '{self.format}'")
        for ident in self.identifiers:
            if ident.startswith("/") and ident.endswith("/"):
                try:
                    re.compile(ident[1:-1])
                except re.error as e:
                    raise ValueError(f"Invalid regex identifier '{ident}': {e}")

    def get_config_for_identifier(self, ident: str) -> tuple[int, list[str], list[str]]:
        """Get effective priority, violations, and ignore patterns for an identifier.

        Returns: (priority, violations, ignore)
        """
        # Check exact match first
        if ident and ident in self.identifiers:
            ident_config = self.identifiers[ident]
            return (
                (
                    ident_config.priority
                    if ident_config.priority is not None
                    else self.priority
                ),
                ident_config.violations,
                ident_config.ignore,
            )

        # Check regex patterns
        if ident:
            for pattern, pattern_config in self.identifiers.items():
                if pattern.startswith("/") and pattern.endswith("/"):
                    regex = pattern[1:-1]
                    if re.match(regex, ident):
                        return (
                            (
                                pattern_config.priority
                                if pattern_config.priority is not None
                                else self.priority
                            ),
                            pattern_config.violations,
                            pattern_config.ignore,
                        )

        # Default
        return self.priority, [], []

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        valid_keys = {
            ConfigKeys.PRIORITY,
            ConfigKeys.FORMAT,
            ConfigKeys.CURSOR_FILE,
            ConfigKeys.OUTPUT_COMMAND,
            ConfigKeys.EMAIL_TO,
            ConfigKeys.EMAIL_SUBJECT,
            ConfigKeys.IDENTIFIERS,
        }
        unknown_keys = set(data.keys()) - valid_keys
        if unknown_keys:
            raise ValueError(
                f"Unknown keys in config: {', '.join(sorted(unknown_keys))}"
            )

        priority = data.get(ConfigKeys.PRIORITY, 6)
        if isinstance(priority, str):
            priority = PRIORITY_NAMES.get(priority.lower(), 6)

        identifiers: dict[str, IdentifierConfig] = {}
        for ident, ident_config in data.get(ConfigKeys.IDENTIFIERS, {}).items():
            if isinstance(ident_config, dict):
                identifiers[ident] = IdentifierConfig.from_dict(
                    ident_config, identifier=ident
                )
            else:
                raise ValueError(
                    f"Identifier '{ident}' must be a dict, "
                    f"got {type(ident_config).__name__}"
                )

        return cls(
            priority=priority,
            format=data.get(ConfigKeys.FORMAT, "short"),
            cursor_file=data.get(ConfigKeys.CURSOR_FILE),
            output_command=data.get(ConfigKeys.OUTPUT_COMMAND),
            email_to=data.get(ConfigKeys.EMAIL_TO),
            email_subject=data.get(ConfigKeys.EMAIL_SUBJECT, "Journal Alerts"),
            identifiers=identifiers,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            ConfigKeys.PRIORITY: PRIORITY_NUMBERS[self.priority],
            ConfigKeys.FORMAT: self.format,
        }
        if self.cursor_file:
            result[ConfigKeys.CURSOR_FILE] = self.cursor_file
        if self.output_command:
            result[ConfigKeys.OUTPUT_COMMAND] = self.output_command
        if self.email_to:
            result[ConfigKeys.EMAIL_TO] = self.email_to
            result[ConfigKeys.EMAIL_SUBJECT] = self.email_subject

        # Add all identifiers with default violations
        result[ConfigKeys.IDENTIFIERS] = {}

        # First add configured identifiers
        for ident, ident_config in self.identifiers.items():
            result[ConfigKeys.IDENTIFIERS][ident] = ident_config.to_dict()

        # Then add unconfigured identifiers that have default violations
        for ident in DEFAULT_VIOLATIONS:
            if ident not in result[ConfigKeys.IDENTIFIERS]:
                result[ConfigKeys.IDENTIFIERS][ident] = {
                    IdentifierConfigKeys.IGNORE: [],
                    IdentifierConfigKeys.VIOLATIONS: DEFAULT_VIOLATIONS[ident],
                }

        return result
