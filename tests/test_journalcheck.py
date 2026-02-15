import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import yaml
from journalcheck.journalcheck import (
    load_config,
    format_entry,
    should_show_entry,
    parse_args,
    get_identifier,
    format_identifier_with_pid,
)
from journalcheck.config import Config, IdentifierConfig, PRIORITY_NAMES


def test_load_config_default():
    config = load_config()
    assert config.priority == 6
    assert config.format == "short"
    assert config.identifiers == {}


def test_load_config_from_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"priority": 3, "format": "json"}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.priority == 3
        assert config.format == "json"
    finally:
        Path(config_file).unlink()


def test_load_config_with_args():
    config = load_config(priority_param=4, output_format_param="json")
    assert config.priority == 4
    assert config.format == "json"


def test_load_config_with_identifiers():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"identifiers": {"kernel": {"priority": 4}}}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.identifiers["kernel"].priority == 4
    finally:
        Path(config_file).unlink()


def test_should_show_entry_default():
    config = Config(priority=6)
    entry = {"PRIORITY": 5}
    show, severity = should_show_entry(entry, config)
    assert show is True
    assert severity == ""


def test_should_show_entry_filtered():
    config = Config(priority=4)
    entry = {"PRIORITY": 5}
    show, severity = should_show_entry(entry, config)
    assert show is False


def test_should_show_entry_identifier_dict():
    config = Config(priority=6, identifiers={"kernel": IdentifierConfig(priority=4)})
    entry = {"SYSLOG_IDENTIFIER": "kernel", "PRIORITY": 5}
    show, severity = should_show_entry(entry, config)
    assert show is False


def test_should_show_entry_identifier_int():
    config = Config(priority=6, identifiers={"kernel": 4})
    entry = {"SYSLOG_IDENTIFIER": "kernel", "PRIORITY": 3}
    show, severity = should_show_entry(entry, config)
    assert show is True


def test_format_entry_json():
    entry = {"MESSAGE": "test", "_HOSTNAME": "host"}
    result = format_entry(entry, "json")
    assert "test" in result
    assert "host" in result


def test_format_entry_short():
    entry = {
        "__REALTIME_TIMESTAMP": datetime(2024, 1, 1, 12, 0, 0),
        "_HOSTNAME": "testhost",
        "SYSLOG_IDENTIFIER": "testapp",
        "MESSAGE": "test message",
    }
    result = format_entry(entry, "short")
    assert "testhost" in result
    assert "testapp" in result
    assert "test message" in result


def test_parse_args_defaults():
    args = parse_args([])
    assert args.config is None
    assert args.priority is None
    assert args.output is None


def test_parse_args_with_options():
    args = parse_args(["-c", "test.yaml", "-p", "3", "-o", "json"])
    assert args.config == "test.yaml"
    assert args.priority == 3
    assert args.output == "json"


def test_should_show_entry_regex_match():
    config = Config(priority=6, identifiers={"/^systemd.*/": IdentifierConfig(priority=4)})
    entry = {"SYSLOG_IDENTIFIER": "systemd-logind", "PRIORITY": 5}
    show, severity = should_show_entry(entry, config)
    assert show is False


def test_should_show_entry_regex_no_match():
    config = Config(priority=6, identifiers={"/^systemd.*/": IdentifierConfig(priority=4)})
    entry = {"SYSLOG_IDENTIFIER": "kernel", "PRIORITY": 5}
    show, severity = should_show_entry(entry, config)
    assert show is True


def test_should_show_entry_regex_int():
    config = Config(priority=6, identifiers={"/^systemd.*/": 3})
    entry = {"SYSLOG_IDENTIFIER": "systemd-udevd", "PRIORITY": 3}
    show, severity = should_show_entry(entry, config)
    assert show is True


def test_should_show_entry_violation():
    config = Config(priority=6, identifiers={"ssh": IdentifierConfig(violations=["Failed"])})
    entry = {"SYSLOG_IDENTIFIER": "ssh", "PRIORITY": 6, "MESSAGE": "Failed password"}
    show, severity = should_show_entry(entry, config)
    assert show is True
    assert severity == "VIOLATION"


def test_should_show_entry_ignore():
    config = Config(priority=6, identifiers={"ssh": IdentifierConfig(ignore=[".*Accepted.*"])})
    entry = {"SYSLOG_IDENTIFIER": "ssh", "PRIORITY": 6, "MESSAGE": "Accepted publickey"}
    show, severity = should_show_entry(entry, config)
    assert show is False


def test_normalize_priority_string():
    assert PRIORITY_NAMES["warning"] == 4
    assert PRIORITY_NAMES["info"] == 6


def test_normalize_priority_int():
    # Test that integer priorities work directly in Config
    config = Config(priority=3)
    assert config.priority == 3


def test_get_identifier_syslog():
    entry = {"SYSLOG_IDENTIFIER": "test"}
    assert get_identifier(entry) == "test"


def test_get_identifier_comm():
    entry = {"_COMM": "testcomm"}
    assert get_identifier(entry) == "testcomm"


def test_get_identifier_empty():
    entry = {}
    assert get_identifier(entry) == ""


def test_format_identifier_with_pid_syslog():
    entry = {"SYSLOG_IDENTIFIER": "test", "_PID": 1234}
    assert format_identifier_with_pid(entry) == "test[1234]"


def test_format_identifier_with_pid_comm():
    entry = {"_COMM": "test", "_PID": 1234}
    assert format_identifier_with_pid(entry) == "(test)[1234]"


def test_format_identifier_with_pid_no_pid():
    entry = {"SYSLOG_IDENTIFIER": "test"}
    assert format_identifier_with_pid(entry) == "test"


def test_format_entry_with_pid():
    entry = {
        "__REALTIME_TIMESTAMP": datetime(2024, 1, 1, 12, 0, 0),
        "_HOSTNAME": "testhost",
        "SYSLOG_IDENTIFIER": "testapp",
        "_PID": 1234,
        "MESSAGE": "test message",
    }
    result = format_entry(entry, "short")
    assert "testapp[1234]" in result


def test_load_config_priority_names():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"priority": "warning"}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.priority == 4
    finally:
        Path(config_file).unlink()


def test_should_show_entry_regex_violation():
    config = Config(priority=6, identifiers={"/^ssh.*/": IdentifierConfig(violations=["Failed"])})
    entry = {"SYSLOG_IDENTIFIER": "sshd", "PRIORITY": 6, "MESSAGE": "Failed password"}
    show, severity = should_show_entry(entry, config)
    assert show is True
    assert severity == "VIOLATION"


def test_should_show_entry_regex_ignore():
    config = Config(priority=6, identifiers={"/^ssh.*/": IdentifierConfig(ignore=[".*Accepted.*"])})
    entry = {"SYSLOG_IDENTIFIER": "sshd", "PRIORITY": 6, "MESSAGE": "Accepted publickey"}
    show, severity = should_show_entry(entry, config)
    assert show is False


def test_load_config_identifier_int_normalization():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"identifiers": {"kernel": "warning"}}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.identifiers["kernel"] == 4
    finally:
        Path(config_file).unlink()


def test_identifier_config_invalid_priority():
    with pytest.raises(ValueError, match="Priority must be 0-7"):
        IdentifierConfig(priority=10)


def test_identifier_config_invalid_regex():
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        IdentifierConfig(ignore=["[invalid"])


def test_identifier_config_invalid_type():
    with pytest.raises(ValueError, match="ignore must be a list"):
        IdentifierConfig(ignore={"key": "value"})


def test_config_invalid_priority():
    with pytest.raises(ValueError, match="Priority must be 0-7"):
        Config(priority=8)


def test_config_invalid_format():
    with pytest.raises(ValueError, match="Format must be"):
        Config(format="invalid")


def test_config_invalid_identifier_priority():
    with pytest.raises(ValueError, match="Priority for 'test' must be 0-7"):
        Config(identifiers={"test": 10})


def test_config_invalid_regex_identifier():
    with pytest.raises(ValueError, match="Invalid regex identifier"):
        Config(identifiers={"/[invalid/": 4})


def test_load_config_validates_priority():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"priority": 10}, f)
        config_file = f.name

    try:
        with pytest.raises(ValueError, match="Priority must be 0-7"):
            load_config(config_file)
    finally:
        Path(config_file).unlink()


def test_load_config_validates_format():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"format": "invalid"}, f)
        config_file = f.name

    try:
        with pytest.raises(ValueError, match="Format must be"):
            load_config(config_file)
    finally:
        Path(config_file).unlink()


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
            "kernel": 3,
        },
    }
    config = Config.from_dict(data)
    assert config.priority == 3
    assert config.format == "json"
    assert isinstance(config.identifiers["ssh"], IdentifierConfig)
    assert config.identifiers["ssh"].priority == 6
    assert config.identifiers["kernel"] == 3


def test_load_config_custom_file_no_default_cursor():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"priority": 6}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.cursor_file is None
    finally:
        Path(config_file).unlink()


def test_load_config_custom_file_with_cursor():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"cursor_file": "/tmp/custom_cursor"}, f)
        config_file = f.name

    try:
        config = load_config(config_file)
        assert config.cursor_file == "/tmp/custom_cursor"
    finally:
        Path(config_file).unlink()


def test_ignore_pattern_fullmatch():
    # Ignore patterns should match the entire message (fullmatch)
    config = Config(priority=6, identifiers={"test": IdentifierConfig(ignore=["connection accepted"])})
    entry = {"SYSLOG_IDENTIFIER": "test", "PRIORITY": 6, "MESSAGE": "connection accepted"}
    show, severity = should_show_entry(entry, config)
    assert show is False

    # Should not match if pattern doesn't cover entire message
    entry2 = {"SYSLOG_IDENTIFIER": "test", "PRIORITY": 6, "MESSAGE": "prefix connection accepted suffix"}
    show2, severity2 = should_show_entry(entry2, config)
    assert show2 is True


def test_violation_pattern_search():
    # Violation patterns should match anywhere in the message
    config = Config(priority=6, identifiers={"test": IdentifierConfig(violations=["failed"])})
    entry = {"SYSLOG_IDENTIFIER": "test", "PRIORITY": 6, "MESSAGE": "authentication failed for user"}
    show, severity = should_show_entry(entry, config)
    assert show is True
    assert severity == "VIOLATION"

    # Should match even if pattern is in the middle
    entry2 = {"SYSLOG_IDENTIFIER": "test", "PRIORITY": 6, "MESSAGE": "prefix failed suffix"}
    show2, severity2 = should_show_entry(entry2, config)
    assert show2 is True
    assert severity2 == "VIOLATION"


def test_load_config_merge_appends_lists():
    # Test that merging configs appends ignore and violations lists
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create main config
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump({
                "identifiers": {
                    "ssh": {
                        "priority": 6,
                        "ignore": ["pattern1"],
                        "violations": ["violation1"]
                    }
                }
            }, f)

        # Create config dir with additional config
        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump({
                "identifiers": {
                    "ssh": {
                        "ignore": ["pattern2"],
                        "violations": ["violation2"]
                    }
                }
            }, f)

        # Mock the default paths
        from journalcheck import journalcheck
        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)
            journalcheck.DEFAULT_CONFIG_DIR = str(config_dir)

            config = load_config()

            # Verify lists were appended
            assert isinstance(config.identifiers["ssh"], IdentifierConfig)
            assert config.identifiers["ssh"].ignore == ["pattern1", "pattern2"]
            assert config.identifiers["ssh"].violations == ["violation1", "violation2"]
            assert config.identifiers["ssh"].priority == 6
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_default_violations_sshd():
    # sshd should have default violations pre-populated when loaded from config
    config = Config.from_dict({
        "identifiers": {
            "sshd": {}
        }
    })
    assert len(config.identifiers["sshd"].violations) > 0
    assert any("Failed password" in v for v in config.identifiers["sshd"].violations)


def test_default_violations_with_custom():
    # Custom violations should be appended to defaults
    config = Config.from_dict({
        "identifiers": {
            "sshd": {
                "violations": ["custom pattern"]
            }
        }
    })
    violations = config.identifiers["sshd"].violations
    assert "custom pattern" in violations
    assert any("Failed password" in v for v in violations)
    assert len(violations) > 1  # Has both default and custom


def test_load_config_merge_no_identifiers_in_main():
    # Test merging when main config has no identifiers section
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump({"priority": 6}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump({"identifiers": {"ssh": {"priority": 4}}}, f)

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)
            journalcheck.DEFAULT_CONFIG_DIR = str(config_dir)

            config = load_config()
            assert isinstance(config.identifiers["ssh"], IdentifierConfig)
            assert config.identifiers["ssh"].priority == 4
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_merge_overrides():
    # Test that config.d can override priority, format, cursor_file
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump(
                {"priority": 6, "format": "short", "cursor_file": "/tmp/cursor1"}, f
            )

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump(
                {"priority": 4, "format": "json", "cursor_file": "/tmp/cursor2"}, f
            )

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)
            journalcheck.DEFAULT_CONFIG_DIR = str(config_dir)

            config = load_config()
            assert config.priority == 4
            assert config.format == "json"
            assert config.cursor_file == "/tmp/cursor2"
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_merge_overrides_no_identifiers():
    # Test config.d overrides when no identifiers in additional config
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump({"priority": 6}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump({"priority": 4, "format": "json", "cursor_file": "/tmp/test"}, f)

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)
            journalcheck.DEFAULT_CONFIG_DIR = str(config_dir)

            config = load_config()
            assert config.priority == 4
            assert config.format == "json"
            assert config.cursor_file == "/tmp/test"
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_merge_non_dict_identifier():
    # Test merging when existing identifier is not a dict (e.g., int priority)
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump({"identifiers": {"ssh": 4}}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump({"identifiers": {"ssh": {"priority": 6}}}, f)

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)
            journalcheck.DEFAULT_CONFIG_DIR = str(config_dir)

            config = load_config()
            assert isinstance(config.identifiers["ssh"], IdentifierConfig)
            assert config.identifiers["ssh"].priority == 6
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir


def test_load_config_merge_dict_to_int_identifier():
    # Test merging when existing is dict but new is int
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        main_config = Path(tmpdir) / "main.yaml"
        with open(main_config, "w") as f:
            yaml.dump({"identifiers": {"ssh": {"priority": 4}}}, f)

        config_dir = Path(tmpdir) / "config.d"
        config_dir.mkdir()

        additional_config = config_dir / "01-additional.yaml"
        with open(additional_config, "w") as f:
            yaml.dump({"identifiers": {"ssh": 6}}, f)

        from journalcheck import journalcheck

        original_default_file = journalcheck.DEFAULT_CONFIG_FILE
        original_default_dir = journalcheck.DEFAULT_CONFIG_DIR

        try:
            journalcheck.DEFAULT_CONFIG_FILE = str(main_config)
            journalcheck.DEFAULT_CONFIG_DIR = str(config_dir)

            config = load_config()
            assert config.identifiers["ssh"] == 6
        finally:
            journalcheck.DEFAULT_CONFIG_FILE = original_default_file
            journalcheck.DEFAULT_CONFIG_DIR = original_default_dir
