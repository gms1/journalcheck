#!/bin/bash
set -e
pytest --cov=journalcheck --cov-report=term-missing --cov-report=xml
