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


class IdentifierConfigKeys:
    PRIORITY = "priority"
    IGNORE = "ignore"
    VIOLATIONS = "violations"


VALID_IDENTIFIER_CONFIG_KEYS = {
    IdentifierConfigKeys.PRIORITY,
    IdentifierConfigKeys.IGNORE,
    IdentifierConfigKeys.VIOLATIONS,
}


class ConfigKeys:
    PRIORITY = "priority"
    FORMAT = "format"
    CURSOR_FILE = "cursor_file"
    OUTPUT_COMMAND = "output_command"
    EMAIL_TO = "email_to"
    EMAIL_SUBJECT = "email_subject"
    IDENTIFIERS = "identifiers"


VALID_CONFIG_KEYS = {
    ConfigKeys.PRIORITY,
    ConfigKeys.FORMAT,
    ConfigKeys.CURSOR_FILE,
    ConfigKeys.OUTPUT_COMMAND,
    ConfigKeys.EMAIL_TO,
    ConfigKeys.EMAIL_SUBJECT,
    ConfigKeys.IDENTIFIERS,
}

DEFAULT_CONFIG_FILE: str = "/etc/journalcheck.yaml"
DEFAULT_CONFIG_DIR = "/etc/journalcheck.d"
DEFAULT_CURSOR_FILE = "/var/lib/journalcheck/cursor"

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
    _compiled_ignore: list[re.Pattern[str]] = field(
        default_factory=list, init=False, repr=False
    )
    _compiled_violations: list[re.Pattern[str]] = field(
        default_factory=list, init=False, repr=False
    )

    def __post_init__(self):
        if self.priority is not None and not 0 <= self.priority <= 7:
            raise ValueError(f"Priority must be 0-7, got {self.priority}")
        if not isinstance(self.ignore, list):
            raise ValueError(f"ignore must be a list, got {type(self.ignore).__name__}")
        if not isinstance(self.violations, list):
            raise ValueError(
                f"violations must be a list, got {type(self.violations).__name__}"
            )
        # Compile patterns once
        self._compiled_ignore = []
        self._compiled_violations = []
        for pattern in self.ignore:
            try:
                self._compiled_ignore.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}")
        for pattern in self.violations:
            try:
                self._compiled_violations.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}")

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], identifier: str = ""
    ) -> "IdentifierConfig":
        unknown_keys = set(data.keys()) - VALID_IDENTIFIER_CONFIG_KEYS
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
        if self.ignore:
            result[IdentifierConfigKeys.IGNORE] = self.ignore
        if self.violations:
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
    _compiled_identifier_patterns: list[tuple[re.Pattern[str], IdentifierConfig]] = (
        field(default_factory=list, init=False, repr=False)
    )

    def __post_init__(self):
        if not 0 <= self.priority <= 7:
            raise ValueError(f"Priority must be 0-7, got {self.priority}")
        if self.format not in ["short", "json"]:
            raise ValueError(f"Format must be 'short' or 'json', got '{self.format}'")
        # Compile regex identifier patterns once
        self._compiled_identifier_patterns = []
        for ident, ident_config in self.identifiers.items():
            if ident.startswith("/") and ident.endswith("/"):
                try:
                    pattern = re.compile(ident[1:-1])
                    self._compiled_identifier_patterns.append((pattern, ident_config))
                except re.error as e:
                    raise ValueError(f"Invalid regex identifier '{ident}': {e}")

    def get_config_for_identifier(self, ident: str) -> tuple[int, IdentifierConfig]:
        """Get effective priority and config for an identifier.

        Returns: (priority, identifier_config)
        """
        # Check exact match first, so that they always have a higher priority
        if ident and ident in self.identifiers:
            ident_config = self.identifiers[ident]
            effective_priority = (
                ident_config.priority
                if ident_config.priority is not None
                else self.priority
            )
            return effective_priority, ident_config

        # Check compiled regex patterns
        if ident:
            for pattern, pattern_config in self._compiled_identifier_patterns:
                if pattern.match(ident):
                    effective_priority = (
                        pattern_config.priority
                        if pattern_config.priority is not None
                        else self.priority
                    )
                    return effective_priority, pattern_config

        # Default - return empty config
        empty_config = IdentifierConfig()
        return self.priority, empty_config

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        unknown_keys = set(data.keys()) - VALID_CONFIG_KEYS
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

        for ident in DEFAULT_VIOLATIONS:
            if ident not in identifiers:
                identifiers[ident] = IdentifierConfig.from_dict({}, identifier=ident)

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

        result[ConfigKeys.IDENTIFIERS] = {}
        for ident, ident_config in self.identifiers.items():
            if not ident.startswith("/") or not ident.endswith("/"):
                result[ConfigKeys.IDENTIFIERS][ident] = ident_config.to_dict()
        for ident, ident_config in self.identifiers.items():
            if ident.startswith("/") and ident.endswith("/"):
                result[ConfigKeys.IDENTIFIERS][ident] = ident_config.to_dict()

        return result
