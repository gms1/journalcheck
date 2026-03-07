import tempfile
import yaml
from journalcheck.journalcheck import run, parse_args, load_config
from journalcheck.config import ConfigKeys, IdentifierConfigKeys, OutputFormat
from systemd import journal
from pathlib import Path
import io
import sys

TEST_CONFIG_DATA_DIR_PATH = Path("tests/fixtures/config_data/")
TEST_JOURNAL_DATA_DIR_PATH = Path("tests/fixtures/journal_data/")


def test_show_config():
    """Test --show-config displays merged configuration."""
    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        reader = journal.Reader(path=str(TEST_JOURNAL_DATA_DIR_PATH))
        run(
            reader,
            ["--show-config", "-c", str(TEST_CONFIG_DATA_DIR_PATH / "default.yaml")],
        )
        output = captured_output.getvalue()

        assert "priority:" in output
        assert "format:" in output
        assert "identifiers:" in output
    finally:
        sys.stdout = sys.__stdout__


def test_run_with_cursor_file():
    """Test with cursor file - should not print same lines again."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cursor_file = Path(tmpdir) / "cursor"
        config_file = Path(tmpdir) / "config.yaml"

        # Create config with violations and ignore patterns
        config_data = {
            ConfigKeys.PRIORITY: "emerg",
            ConfigKeys.FORMAT: OutputFormat.SHORT.value,
            ConfigKeys.CURSOR_FILE: str(cursor_file),
            ConfigKeys.IDENTIFIERS: {
                "sshd": {
                    IdentifierConfigKeys.PRIORITY: "info",
                    IdentifierConfigKeys.IGNORE: ["Accepted publickey.*"],
                    IdentifierConfigKeys.VIOLATIONS: ["Failed password"],
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Write empty cursor to start from beginning
        cursor_file.write_text("")

        # First run - should show violations
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            reader = journal.Reader(path=str(TEST_JOURNAL_DATA_DIR_PATH))
            run(reader, ["-c", str(config_file)])
            first_output = captured_output.getvalue()

            # Should show violation (Failed password)
            assert "Failed password" in first_output
            # Should not show ignored message
            assert "Accepted publickey" not in first_output
            # Cursor file should have content now
            assert cursor_file.read_text() != ""

            # Second run - should not show same entries
            captured_output = io.StringIO()
            sys.stdout = captured_output

            reader = journal.Reader(path=str(TEST_JOURNAL_DATA_DIR_PATH))
            run(reader, ["-c", str(config_file)])
            second_output = captured_output.getvalue()

            # Should be empty (no new entries)
            assert second_output == ""
        finally:
            sys.stdout = sys.__stdout__


def test_run_with_not_existing_cursor_file():
    """Test with not existing cursor file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cursor_file = Path(tmpdir) / "cursor"
        config_file = Path(tmpdir) / "config.yaml"

        # Create config with violations and ignore patterns
        config_data = {
            ConfigKeys.PRIORITY: "emerg",
            ConfigKeys.FORMAT: OutputFormat.SHORT.value,
            ConfigKeys.CURSOR_FILE: str(cursor_file),
            ConfigKeys.IDENTIFIERS: {
                "sshd": {
                    IdentifierConfigKeys.PRIORITY: "info",
                    IdentifierConfigKeys.IGNORE: ["Accepted publickey.*"],
                    IdentifierConfigKeys.VIOLATIONS: ["Failed password"],
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # First run - should not show outdated violations
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            reader = journal.Reader(path=str(TEST_JOURNAL_DATA_DIR_PATH))
            run(reader, ["-c", str(config_file)])
            first_output = captured_output.getvalue()

            # Should show violation (Failed password)
            assert "Failed password" not in first_output
        finally:
            sys.stdout = sys.__stdout__


def test_run_without_cursor_file():
    """Test without cursor file - should print same lines again."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "config.yaml"

        # Create config with violations and ignore patterns
        config_data = {
            ConfigKeys.PRIORITY: "emerg",
            ConfigKeys.FORMAT: OutputFormat.SHORT.value,
            ConfigKeys.CURSOR_FILE: None,
            ConfigKeys.IDENTIFIERS: {
                "sshd": {
                    IdentifierConfigKeys.PRIORITY: "info",
                    IdentifierConfigKeys.IGNORE: ["Accepted publickey.*"],
                    IdentifierConfigKeys.VIOLATIONS: ["Failed password"],
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # First run
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            reader = journal.Reader(path=str(TEST_JOURNAL_DATA_DIR_PATH))
            run(reader, ["-c", str(config_file)])
            first_output = captured_output.getvalue()

            # Should show violation
            assert "Failed password" in first_output
            # Should not show ignored message
            assert "Accepted publickey" not in first_output

            # Second run - should show same entries again
            captured_output = io.StringIO()
            sys.stdout = captured_output

            reader = journal.Reader(path=str(TEST_JOURNAL_DATA_DIR_PATH))
            run(reader, ["-c", str(config_file)])
            second_output = captured_output.getvalue()

            # Should show same violation again
            assert "Failed password" in second_output
            assert "Accepted publickey" not in second_output
        finally:
            sys.stdout = sys.__stdout__
