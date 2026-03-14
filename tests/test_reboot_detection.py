import tempfile
import yaml
import io
import sys
from pathlib import Path
from journalcheck.journalcheck import run, JournalFields, BOOT_MARKER
from journalcheck.config import ConfigKeys, OutputFormat
from systemd import journal


TEST_JOURNAL_DATA_DIR_PATH = Path("tests/fixtures/journal_data/")


class MockReader:
    """Mock journal reader for testing reboot detection."""

    def __init__(self, entries, cursor_entry=None, empty_get_next=False):
        self.entries = entries
        self.index = 0
        self.cursor_entry = (
            cursor_entry  # entry returned by get_next() after seek_cursor
        )
        self.empty_get_next = empty_get_next  # simulate get_next returning empty dict

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.entries):
            raise StopIteration
        entry = self.entries[self.index]
        self.index += 1
        return entry

    def seek_cursor(self, cursor):
        pass

    def get_next(self):
        if self.empty_get_next:
            return {}
        return self.cursor_entry or {}

    def seek_realtime(self, since):
        pass


def test_reboot_marker_inserted_on_boot_id_change():
    """Test that reboot marker is inserted when boot ID changes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(
                {ConfigKeys.PRIORITY: 6, ConfigKeys.FORMAT: OutputFormat.SHORT.value}, f
            )

        # Create mock entries with different boot IDs
        entries = [
            {
                JournalFields.BOOT_ID: "boot-id-1",
                JournalFields.PRIORITY: 3,
                JournalFields.MESSAGE: "First message",
                JournalFields.SYSLOG_IDENTIFIER: "test",
                JournalFields.HOSTNAME: "host",
            },
            {
                JournalFields.BOOT_ID: "boot-id-1",
                JournalFields.PRIORITY: 3,
                JournalFields.MESSAGE: "Second message",
                JournalFields.SYSLOG_IDENTIFIER: "test",
                JournalFields.HOSTNAME: "host",
            },
            {
                JournalFields.BOOT_ID: "boot-id-2",
                JournalFields.PRIORITY: 3,
                JournalFields.MESSAGE: "After reboot",
                JournalFields.SYSLOG_IDENTIFIER: "test",
                JournalFields.HOSTNAME: "host",
            },
        ]

        reader = MockReader(entries)
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            run(reader, ["-c", str(config_file)])
            output = captured_output.getvalue()

            # Should contain reboot marker
            assert BOOT_MARKER in output
            # Should have all messages
            assert "First message" in output
            assert "Second message" in output
            assert "After reboot" in output
            # Reboot marker should be between second and third message
            lines = output.strip().split("\n")
            assert len(lines) == 4  # 3 messages + 1 reboot marker
            assert BOOT_MARKER in lines[2]
        finally:
            sys.stdout = sys.__stdout__


def test_no_reboot_marker_for_json_format():
    """Test that reboot marker is NOT inserted for JSON format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(
                {ConfigKeys.PRIORITY: 6, ConfigKeys.FORMAT: OutputFormat.JSON.value}, f
            )

        # Create mock entries with different boot IDs
        entries = [
            {
                JournalFields.BOOT_ID: "boot-id-1",
                JournalFields.PRIORITY: 3,
                JournalFields.MESSAGE: "First message",
                JournalFields.SYSLOG_IDENTIFIER: "test",
            },
            {
                JournalFields.BOOT_ID: "boot-id-2",
                JournalFields.PRIORITY: 3,
                JournalFields.MESSAGE: "After reboot",
                JournalFields.SYSLOG_IDENTIFIER: "test",
            },
        ]

        reader = MockReader(entries)
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            run(reader, ["-c", str(config_file)])
            output = captured_output.getvalue()

            # Should NOT contain reboot marker
            assert BOOT_MARKER not in output
            # Should have both messages
            assert "First message" in output
            assert "After reboot" in output
        finally:
            sys.stdout = sys.__stdout__


def test_no_reboot_marker_at_start():
    """Test that reboot marker is not inserted if no previous entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(
                {ConfigKeys.PRIORITY: 6, ConfigKeys.FORMAT: OutputFormat.SHORT.value}, f
            )

        # Create mock entries where first entry has different boot ID
        # but there's no previous entry to compare
        entries = [
            {
                JournalFields.BOOT_ID: "boot-id-2",
                JournalFields.PRIORITY: 3,
                JournalFields.MESSAGE: "First message",
                JournalFields.SYSLOG_IDENTIFIER: "test",
                JournalFields.HOSTNAME: "host",
            },
        ]

        reader = MockReader(entries)
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            run(reader, ["-c", str(config_file)])
            output = captured_output.getvalue()

            # Should NOT contain reboot marker
            assert BOOT_MARKER not in output
            # Should have the message
            assert "First message" in output
        finally:
            sys.stdout = sys.__stdout__


def test_multiple_reboots():
    """Test that multiple reboot markers are inserted correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(
                {ConfigKeys.PRIORITY: 6, ConfigKeys.FORMAT: OutputFormat.SHORT.value}, f
            )

        # Create mock entries with multiple boot ID changes
        entries = [
            {
                JournalFields.BOOT_ID: "boot-id-1",
                JournalFields.PRIORITY: 3,
                JournalFields.MESSAGE: "Message 1",
                JournalFields.SYSLOG_IDENTIFIER: "test",
                JournalFields.HOSTNAME: "host",
            },
            {
                JournalFields.BOOT_ID: "boot-id-2",
                JournalFields.PRIORITY: 3,
                JournalFields.MESSAGE: "Message 2",
                JournalFields.SYSLOG_IDENTIFIER: "test",
                JournalFields.HOSTNAME: "host",
            },
            {
                JournalFields.BOOT_ID: "boot-id-3",
                JournalFields.PRIORITY: 3,
                JournalFields.MESSAGE: "Message 3",
                JournalFields.SYSLOG_IDENTIFIER: "test",
                JournalFields.HOSTNAME: "host",
            },
        ]

        reader = MockReader(entries)
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            run(reader, ["-c", str(config_file)])
            output = captured_output.getvalue()

            # Should contain two reboot markers
            assert output.count(BOOT_MARKER) == 2
            # Should have all messages
            assert "Message 1" in output
            assert "Message 2" in output
            assert "Message 3" in output
        finally:
            sys.stdout = sys.__stdout__


def test_reboot_marker_tracks_all_entries():
    """Test that reboot marker tracks boot ID changes even for filtered entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(
                {ConfigKeys.PRIORITY: 3, ConfigKeys.FORMAT: OutputFormat.SHORT.value}, f
            )

        # Create mock entries where middle entry is filtered out
        entries = [
            {
                JournalFields.BOOT_ID: "boot-id-1",
                JournalFields.PRIORITY: 3,
                JournalFields.MESSAGE: "Message 1",
                JournalFields.SYSLOG_IDENTIFIER: "test",
                JournalFields.HOSTNAME: "host",
            },
            {
                JournalFields.BOOT_ID: "boot-id-2",
                JournalFields.PRIORITY: 6,
                JournalFields.MESSAGE: "Filtered message",
                JournalFields.SYSLOG_IDENTIFIER: "test",
                JournalFields.HOSTNAME: "host",
            },
            {
                JournalFields.BOOT_ID: "boot-id-2",
                JournalFields.PRIORITY: 3,
                JournalFields.MESSAGE: "Message 2",
                JournalFields.SYSLOG_IDENTIFIER: "test",
                JournalFields.HOSTNAME: "host",
            },
        ]

        reader = MockReader(entries)
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            run(reader, ["-c", str(config_file)])
            output = captured_output.getvalue()

            # Should contain reboot marker (boot ID changed even though entry was filtered)
            assert BOOT_MARKER in output
            # Should have shown messages
            assert "Message 1" in output
            assert "Message 2" in output
            assert "Filtered message" not in output
        finally:
            sys.stdout = sys.__stdout__


def test_boot_marker_after_cursor_with_boot_id_change():
    """Test that boot marker is inserted when boot ID changes after cursor seek."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cursor_file = Path(tmpdir) / "cursor"
        cursor_file.write_text("some-cursor")
        config_file = Path(tmpdir) / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(
                {
                    ConfigKeys.PRIORITY: 6,
                    ConfigKeys.FORMAT: OutputFormat.SHORT.value,
                    "cursor_file": str(cursor_file),
                },
                f,
            )

        # cursor_entry is from previous boot, new entries are from a different boot
        cursor_entry = {
            JournalFields.BOOT_ID: "boot-id-1",
            JournalFields.CURSOR: "some-cursor",
        }
        entries = [
            {
                JournalFields.BOOT_ID: "boot-id-2",
                JournalFields.PRIORITY: 3,
                JournalFields.MESSAGE: "First new entry",
                JournalFields.SYSLOG_IDENTIFIER: "test",
                JournalFields.HOSTNAME: "host",
            },
        ]

        reader = MockReader(entries, cursor_entry=cursor_entry)
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            run(reader, ["-c", str(config_file), "-t"])
            output = captured_output.getvalue()

            # Boot marker should appear before the first new entry
            assert BOOT_MARKER in output
            assert "First new entry" in output
            lines = output.strip().split("\n")
            assert lines[0] == BOOT_MARKER
        finally:
            sys.stdout = sys.__stdout__


def test_no_boot_marker_when_get_next_returns_empty():
    """Test that no boot marker is inserted when get_next returns empty dict."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cursor_file = Path(tmpdir) / "cursor"
        cursor_file.write_text("some-cursor")
        config_file = Path(tmpdir) / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(
                {
                    ConfigKeys.PRIORITY: 6,
                    ConfigKeys.FORMAT: OutputFormat.SHORT.value,
                    "cursor_file": str(cursor_file),
                },
                f,
            )

        entries = [
            {
                JournalFields.BOOT_ID: "boot-id-2",
                JournalFields.PRIORITY: 3,
                JournalFields.MESSAGE: "First new entry",
                JournalFields.SYSLOG_IDENTIFIER: "test",
                JournalFields.HOSTNAME: "host",
            },
        ]

        # get_next returns empty dict (cursor entry no longer exists, e.g. rotated)
        reader = MockReader(entries, empty_get_next=True)
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            run(reader, ["-c", str(config_file), "-t"])
            output = captured_output.getvalue()

            # No boot marker since we couldn't read previous boot ID
            assert BOOT_MARKER not in output
            assert "First new entry" in output
        finally:
            sys.stdout = sys.__stdout__
