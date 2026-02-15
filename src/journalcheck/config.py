import re
from dataclasses import dataclass, field
from typing import Any

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

DEFAULT_CONFIG_FILE: str = "/etc/journalcheck.yaml"
DEFAULT_CONFIG_DIR = "/etc/journalcheck.d"
DEFAULT_CURSOR_FILE = "/var/lib/journalcheck/cursor"

DEFAULT_VIOLATIONS: dict[str, list[str]] = {
    "sshd": [
        "Failed password",
        "Invalid user",
        "Connection closed by authenticating user",
        "Disconnected from authenticating user",
    ],
    "sudo": [
        "authentication failure",
        "user NOT in sudoers",
        "incorrect password attempt",
    ],
    "su": [
        "FAILED su",
        "authentication failure",
    ],
    "smartd": [
        "SMART Failure",
        "Attribute.*failed",
        "Error.*occurred",
    ],
    "kernel": [
        "I/O error",
        "Buffer I/O error",
        "end_request: I/O error",
    ],
}


@dataclass
class IdentifierConfig:
    priority: int = 6
    ignore: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not 0 <= self.priority <= 7:
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
        priority = data.get("priority", 6)
        if isinstance(priority, str):
            priority = PRIORITY_NAMES.get(priority.lower(), 6)

        # Start with default violations for this identifier
        violations = list(DEFAULT_VIOLATIONS.get(identifier, []))
        # Append user-configured violations
        violations.extend(data.get("violations", []))

        return cls(
            priority=priority,
            ignore=data.get("ignore", []),
            violations=violations,
        )


@dataclass
class Config:
    priority: int = 6
    format: str = "short"
    cursor_file: str | None = None
    output_command: str | None = None
    email_to: str | None = None
    email_subject: str = "Journal Alerts"
    identifiers: dict[str, IdentifierConfig | int] = field(default_factory=dict)

    def __post_init__(self):
        if not 0 <= self.priority <= 7:
            raise ValueError(f"Priority must be 0-7, got {self.priority}")
        if self.format not in ["short", "json"]:
            raise ValueError(f"Format must be 'short' or 'json', got '{self.format}'")
        for ident, config in self.identifiers.items():
            if isinstance(config, int) and not 0 <= config <= 7:
                raise ValueError(f"Priority for '{ident}' must be 0-7, got {config}")
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
            if isinstance(ident_config, IdentifierConfig):
                return (
                    ident_config.priority,
                    ident_config.violations,
                    ident_config.ignore,
                )
            return ident_config, [], []

        # Check regex patterns
        if ident:
            for pattern, pattern_config in self.identifiers.items():
                if pattern.startswith("/") and pattern.endswith("/"):
                    regex = pattern[1:-1]
                    if re.match(regex, ident):
                        if isinstance(pattern_config, IdentifierConfig):
                            return (
                                pattern_config.priority,
                                pattern_config.violations,
                                pattern_config.ignore,
                            )
                        return pattern_config, [], []

        # Default
        return self.priority, [], []

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        priority = data.get("priority", 6)
        if isinstance(priority, str):
            priority = PRIORITY_NAMES.get(priority.lower(), 6)

        identifiers: dict[str, IdentifierConfig | int] = {}
        for ident, ident_config in data.get("identifiers", {}).items():
            if isinstance(ident_config, dict):
                identifiers[ident] = IdentifierConfig.from_dict(
                    ident_config, identifier=ident
                )
            else:
                if isinstance(ident_config, str):
                    identifiers[ident] = PRIORITY_NAMES.get(ident_config.lower(), 6)
                else:
                    identifiers[ident] = ident_config

        return cls(
            priority=priority,
            format=data.get("format", "short"),
            cursor_file=data.get("cursor_file"),
            output_command=data.get("output_command"),
            email_to=data.get("email_to"),
            email_subject=data.get("email_subject", "Journal Alerts"),
            identifiers=identifiers,
        )
