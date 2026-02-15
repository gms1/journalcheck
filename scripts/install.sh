#!/bin/bash
set -e

if command -v apt-get &> /dev/null; then
    dpkg -s libsystemd-dev libsqlite3-dev &> /dev/null || sudo apt-get install -y libsystemd-dev libsqlite3-dev
elif command -v dnf &> /dev/null; then
    rpm -q systemd-devel sqlite-devel &> /dev/null || sudo dnf install -y systemd-devel sqlite-devel
fi

pyenv install -s
pyenv local
pip install -e .
pip install -r requirements.txt
