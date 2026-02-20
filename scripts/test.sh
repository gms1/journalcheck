#!/bin/bash
DN=$(dirname -- "${BASH_SOURCE[0]}"})
set -e
cd "${DN}/.."

if [ ! -f "tests/fixtures/journal_data/test.journal" -o "tests/fixtures/journal_data/test.export" -nt "tests/fixtures/journal_data/test.journal" ]; then
  echo "Regenerating test.journal ..."
  ./scripts/generate-test-journal.sh
fi

pytest --cov=journalcheck --cov-report=term-missing --cov-report=xml
