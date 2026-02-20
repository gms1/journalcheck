#!/bin/bash
DN=$(dirname -- "${BASH_SOURCE[0]}"})
set -e
cd "${DN}/.."

if command -v apt-get &> /dev/null; then
    dpkg -s systemd-journal-remote &> /dev/null || sudo apt-get install -y systemd-journal-remote
elif command -v dnf &> /dev/null; then
    rpm -q ssystemd-journal-remote &> /dev/null || sudo dnf install -y systemd-journal-remote
fi


echo "Generating test journal file..."
python3 scripts/generate-test-journal.py

