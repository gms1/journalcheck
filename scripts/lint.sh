#!/bin/bash
set -e
black src
flake8 src
mypy src
