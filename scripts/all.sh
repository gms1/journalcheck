#!/bin/bash
DN=$(dirname -- "${BASH_SOURCE[0]}"})
set -e
cd "${DN}/.."

./scripts/lint.sh
./scripts/test.sh
./scripts/build.sh
./scripts/debian.sh

if [ -d .last ]; then
  rm -rf .last
  mkdir -p .last
  cp -a dist/*.deb .last/
fi
