#!/bin/bash
set -e

# Get workspace root
WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PKG_DIR="${WORKSPACE_ROOT}/pkg"
DIST_DIR="${WORKSPACE_ROOT}/dist"

# Recreate dist folder
rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

# Copy source to pkg directory
rsync -a --exclude=pkg --exclude=dist --exclude=.git --exclude=__pycache__ --exclude='*.pyc' --exclude=.pybuild --exclude=htmlcov "${WORKSPACE_ROOT}/" "${PKG_DIR}/"

# Disable pyenv to use system Python
export PATH=$(echo $PATH | tr ':' '\n' | grep -v pyenv | tr '\n' ':')
unset PYENV_ROOT
unset PYENV_VERSION

cd "${PKG_DIR}"
dpkg-buildpackage -us -uc

# Move all artifacts to dist
mv ../*.deb "${DIST_DIR}/" 2>/dev/null || true
mv ../*.buildinfo "${DIST_DIR}/" 2>/dev/null || true
mv ../*.changes "${DIST_DIR}/" 2>/dev/null || true
mv ../*.tar.* "${DIST_DIR}/" 2>/dev/null || true
mv ../*.dsc "${DIST_DIR}/" 2>/dev/null || true

# Clean up pkg directory
rm -rf "${PKG_DIR}"
