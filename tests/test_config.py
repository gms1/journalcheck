import pytest
from journalcheck.config import (
    Config,
    IdentifierConfig,
    PRIORITY_NAMES,
    ConfigKeys,
    IdentifierConfigKeys,
)


def test_normalize_priority_string():
    assert PRIORITY_NAMES["warning"] == 4
    assert PRIORITY_NAMES["info"] == 6


def test_normalize_priority_int():
    config = Config(priority=3)
    assert config.priority == 3


def test_identifier_config_invalid_priority():
    with pytest.raises(ValueError, match="Priority must be 0-7"):
        IdentifierConfig(priority=10)


def test_identifier_config_invalid_regex():
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        IdentifierConfig(ignore=["[invalid"])


def test_identifier_config_invalid_regex_in_violations():
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        IdentifierConfig(violations=["[invalid"])


def test_identifier_config_invalid_ignore():
    with pytest.raises(ValueError, match="ignore must be a list"):
        IdentifierConfig(ignore={"key": "value"})


def test_identifier_config_invalid_violations():
    with pytest.raises(ValueError, match="violations must be a list"):
        IdentifierConfig(violations={"key": "value"})


def test_config_invalid_priority():
    with pytest.raises(ValueError, match="Priority must be 0-7"):
        Config(priority=8)


def test_config_invalid_format():
    with pytest.raises(ValueError, match="Format must be"):
        Config(format="invalid")


def test_config_invalid_identifier_priority():
    with pytest.raises(ValueError, match="Priority must be 0-7"):
        Config(identifiers={"test": IdentifierConfig(priority=10)})


def test_config_invalid_regex_identifier():
    with pytest.raises(ValueError, match="Invalid regex identifier"):
        Config(identifiers={"/[invalid/": IdentifierConfig(priority=4)})


def test_identifier_config_from_dict():
    data = {
        IdentifierConfigKeys.PRIORITY: "warning",
        IdentifierConfigKeys.IGNORE: [".*test.*"],
        IdentifierConfigKeys.VIOLATIONS: ["fail"],
    }
    config = IdentifierConfig.from_dict(data)
    assert config.priority == 4
    assert config.ignore == [".*test.*"]
    assert config.violations == ["fail"]


def test_config_from_dict():
    data = {
        ConfigKeys.PRIORITY: "err",
        ConfigKeys.FORMAT: "json",
        ConfigKeys.IDENTIFIERS: {
            "ssh": {
                IdentifierConfigKeys.PRIORITY: 6,
                IdentifierConfigKeys.VIOLATIONS: ["BREAK-IN"],
            },
            "kernel": {IdentifierConfigKeys.PRIORITY: 3},
        },
    }
    config = Config.from_dict(data)
    assert config.priority == 3
    assert config.format == "json"
    assert isinstance(config.identifiers["ssh"], IdentifierConfig)
    assert config.identifiers["ssh"].priority == 6
    assert isinstance(config.identifiers["kernel"], IdentifierConfig)
    assert config.identifiers["kernel"].priority == 3


def test_config_unknown_key():
    with pytest.raises(ValueError, match="Unknown keys in config: unknown_key"):
        Config.from_dict({ConfigKeys.PRIORITY: 6, "unknown_key": "value"})


def test_identifier_config_unknown_key():
    with pytest.raises(
        ValueError, match="Unknown keys in identifier config: unknown_key"
    ):
        IdentifierConfig.from_dict(
            {IdentifierConfigKeys.PRIORITY: 6, "unknown_key": "value"}
        )


def test_identifier_config_to_dict():
    config = IdentifierConfig(priority=4, ignore=["test"], violations=["fail"])
    result = config.to_dict()
    assert result[IdentifierConfigKeys.PRIORITY] == "warning"
    assert result[IdentifierConfigKeys.IGNORE] == ["test"]
    assert result[IdentifierConfigKeys.VIOLATIONS] == ["fail"]

    # Test with no priority set (should not include priority in output)
    config_no_priority = IdentifierConfig(ignore=["test"], violations=["fail"])
    result_no_priority = config_no_priority.to_dict()
    assert IdentifierConfigKeys.PRIORITY not in result_no_priority
    assert result_no_priority[IdentifierConfigKeys.IGNORE] == ["test"]
    assert result_no_priority[IdentifierConfigKeys.VIOLATIONS] == ["fail"]


def test_config_to_dict():
    config = Config(
        priority=3,
        format="json",
        cursor_file="/tmp/cursor",
        output_command="echo test",
        email_to="admin@example.com",
        email_subject="Test Alert",
        identifiers={"ssh": IdentifierConfig(priority=6, violations=["Failed"])},
    )
    result = config.to_dict()
    assert result[ConfigKeys.PRIORITY] == "err"
    assert result[ConfigKeys.FORMAT] == "json"
    assert result[ConfigKeys.CURSOR_FILE] == "/tmp/cursor"
    assert result[ConfigKeys.OUTPUT_COMMAND] == "echo test"
    assert result[ConfigKeys.EMAIL_TO] == "admin@example.com"
    assert result[ConfigKeys.EMAIL_SUBJECT] == "Test Alert"
    assert result[ConfigKeys.IDENTIFIERS]["ssh"][IdentifierConfigKeys.PRIORITY] == "info"
    assert result[ConfigKeys.IDENTIFIERS]["ssh"][IdentifierConfigKeys.VIOLATIONS] == [
        "Failed"
    ]


def test_default_violations_sshd():
    config = Config.from_dict({ConfigKeys.IDENTIFIERS: {"sshd": {}}})
    assert len(config.identifiers["sshd"].violations) > 0
    assert any("Failed password" in v for v in config.identifiers["sshd"].violations)


def test_default_violations_with_custom():
    config = Config.from_dict(
        {
            ConfigKeys.IDENTIFIERS: {
                "sshd": {IdentifierConfigKeys.VIOLATIONS: ["custom pattern"]}
            }
        }
    )
    violations = config.identifiers["sshd"].violations
    assert "custom pattern" in violations
    assert any("Failed password" in v for v in violations)
    assert len(violations) > 1
