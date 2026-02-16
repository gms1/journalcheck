#!/bin/bash
DN=$(dirname -- "${BASH_SOURCE[0]}"})
cd "${DN}/.."
google-chrome htmlcov/index.html &
