import tempfile
import pytest
from pathlib import Path
from journalcheck.journalcheck import save_cursor, JournalFields


def test_save_cursor_success():
    """Test successful cursor save."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cursor_file = Path(tmpdir) / "subdir" / "cursor"
        entry = {JournalFields.CURSOR: "test-cursor-123"}

        save_cursor(cursor_file, entry)

        assert cursor_file.exists()
        assert cursor_file.read_text() == "test-cursor-123"


def test_save_cursor_no_cursor_in_entry():
    """Test that nothing is saved when entry has no cursor."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cursor_file = Path(tmpdir) / "cursor"
        entry = {JournalFields.MESSAGE: "test"}

        save_cursor(cursor_file, entry)

        assert not cursor_file.exists()


def test_save_cursor_creates_parent_directory():
    """Test that parent directories are created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cursor_file = Path(tmpdir) / "a" / "b" / "c" / "cursor"
        entry = {JournalFields.CURSOR: "test-cursor"}

        save_cursor(cursor_file, entry)

        assert cursor_file.exists()
        assert cursor_file.read_text() == "test-cursor"


def test_save_cursor_overwrites_existing():
    """Test that existing cursor file is overwritten."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cursor_file = Path(tmpdir) / "cursor"
        cursor_file.write_text("old-cursor")
        entry = {JournalFields.CURSOR: "new-cursor"}

        save_cursor(cursor_file, entry)

        assert cursor_file.read_text() == "new-cursor"


def test_save_cursor_permission_error():
    """Test that OSError is raised when directory cannot be created."""
    # Try to create a cursor file in a read-only location
    cursor_file = Path("/root/journalcheck/cursor")
    entry = {JournalFields.CURSOR: "test-cursor"}

    with pytest.raises(OSError, match="Failed to create cursor directory"):
        save_cursor(cursor_file, entry)


def test_save_cursor_write_error():
    """Test that OSError is raised when file cannot be written."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a directory where the cursor file should be
        cursor_file = Path(tmpdir) / "cursor"
        cursor_file.mkdir()  # Make it a directory, not a file
        entry = {JournalFields.CURSOR: "test-cursor"}

        with pytest.raises(OSError, match="Failed to write cursor file"):
            save_cursor(cursor_file, entry)
