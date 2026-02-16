#!/bin/bash
set -e

# Get workspace root
WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION=$(grep '^__version__ = ' "${WORKSPACE_ROOT}/src/journalcheck/__init__.py" | sed 's/__version__ = "\(.*\)"/\1/')
PKG_DIR="${WORKSPACE_ROOT}/journalcheck-${VERSION}"
DIST_DIR="${WORKSPACE_ROOT}/dist"

# Recreate dist folder
rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

# Copy source to pkg directory
rm -rf "${PKG_DIR}"
mkdir -p "${PKG_DIR}"
cp -a "${WORKSPACE_ROOT}/src" "${PKG_DIR}/"
cp -a "${WORKSPACE_ROOT}/debian" "${PKG_DIR}/"
cp -a "${WORKSPACE_ROOT}/systemd" "${PKG_DIR}/"
cp -a "${WORKSPACE_ROOT}/pyproject.toml" "${PKG_DIR}/"
cp -a "${WORKSPACE_ROOT}/README.md" "${PKG_DIR}/"
cp -a "${WORKSPACE_ROOT}/LICENSE" "${PKG_DIR}/"
cp -a "${WORKSPACE_ROOT}/config.yaml.sample" "${PKG_DIR}/"

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
