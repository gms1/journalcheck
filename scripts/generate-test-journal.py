#!/usr/bin/env python3
"""Generate test journal files for unit tests."""
import subprocess
import sys
from pathlib import Path

JOURNAL_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "journal_data"
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)

def create_journal_file():
    """Create test journal file using systemd-journal-remote."""
    journal_file = JOURNAL_DIR / "test.journal"
    export_file = JOURNAL_DIR / "test.export"

    # Check if export file exists
    if not export_file.exists():
        print(f"✗ Export file not found: {export_file}", file=sys.stderr)
        print("Create it manually or copy from test.export.sample", file=sys.stderr)
        return 1

    try:
        # Read from export file
        with open(export_file) as f:
            result = subprocess.run(
                ["/usr/lib/systemd/systemd-journal-remote", "-o", str(journal_file), "--split-mode=none", "-"],
                stdin=f,
                capture_output=True,
                check=True
            )
        print(f"✓ Created {journal_file} from {export_file}")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create journal file: {e.stderr.decode()}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print("✗ systemd-journal-remote not found at /usr/lib/systemd/systemd-journal-remote", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(create_journal_file())
