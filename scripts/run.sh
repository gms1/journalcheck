#!/bin/bash
DN=$(dirname -- "${BASH_SOURCE[0]}"})
cd "${DN}/.."
python -m journalcheck.journalcheck
