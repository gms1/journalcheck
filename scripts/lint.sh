#!/bin/bash
DN=$(dirname -- "${BASH_SOURCE[0]}")
set -e
cd "${DN}/.."


black src/ tests/
flake8 src
mypy src
