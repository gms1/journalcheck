import pytest
from journalcheck.config import Config, IdentifierConfig, PRIORITY_NAMES


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
    data = {"priority": "warning", "ignore": [".*test.*"], "violations": ["fail"]}
    config = IdentifierConfig.from_dict(data)
    assert config.priority == 4
    assert config.ignore == [".*test.*"]
    assert config.violations == ["fail"]


def test_config_from_dict():
    data = {
        "priority": "err",
        "format": "json",
        "identifiers": {
            "ssh": {"priority": 6, "violations": ["BREAK-IN"]},
            "kernel": {"priority": 3},
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
        Config.from_dict({"priority": 6, "unknown_key": "value"})


def test_identifier_config_unknown_key():
    with pytest.raises(
        ValueError, match="Unknown keys in identifier config: unknown_key"
    ):
        IdentifierConfig.from_dict({"priority": 6, "unknown_key": "value"})


def test_identifier_config_to_dict():
    config = IdentifierConfig(priority=4, ignore=["test"], violations=["fail"])
    result = config.to_dict()
    assert result["priority"] == "warning"
    assert result["ignore"] == ["test"]
    assert result["violations"] == ["fail"]

    # Test with no priority set (should not include priority in output)
    config_no_priority = IdentifierConfig(ignore=["test"], violations=["fail"])
    result_no_priority = config_no_priority.to_dict()
    assert "priority" not in result_no_priority
    assert result_no_priority["ignore"] == ["test"]
    assert result_no_priority["violations"] == ["fail"]


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
    assert result["priority"] == "err"
    assert result["format"] == "json"
    assert result["cursor_file"] == "/tmp/cursor"
    assert result["output_command"] == "echo test"
    assert result["email_to"] == "admin@example.com"
    assert result["email_subject"] == "Test Alert"
    assert result["identifiers"]["ssh"]["priority"] == "info"
    assert result["identifiers"]["ssh"]["violations"] == ["Failed"]


def test_default_violations_sshd():
    config = Config.from_dict({"identifiers": {"sshd": {}}})
    assert len(config.identifiers["sshd"].violations) > 0
    assert any("Failed password" in v for v in config.identifiers["sshd"].violations)


def test_default_violations_with_custom():
    config = Config.from_dict(
        {"identifiers": {"sshd": {"violations": ["custom pattern"]}}}
    )
    violations = config.identifiers["sshd"].violations
    assert "custom pattern" in violations
    assert any("Failed password" in v for v in violations)
    assert len(violations) > 1
