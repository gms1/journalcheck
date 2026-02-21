#!/bin/bash
DN=$(dirname -- "${BASH_SOURCE[0]}"})
set -e
cd "${DN}/.."

export PATH=$(echo "${PATH}" | sed -e 's|/opt/hostedtoolcache/[^:]*:||g')

# Get workspace root
WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION=$(grep '^__version__ = ' "${WORKSPACE_ROOT}/src/journalcheck/__init__.py" | sed 's/__version__ = "\(.*\)"/\1/')
PKG_DIR="${WORKSPACE_ROOT}/journalcheck-${VERSION}"
DIST_DIR="${WORKSPACE_ROOT}/dist"

BUILD_PACKAGES=(build-essential devscripts debhelper dh-python python3-all python3-setuptools pybuild-plugin-pyproject python3-build python3-installer)


if ! dpkg -s "${BUILD_PACKAGES[@]}" &> /dev/null; then

  sudo apt-get update
  sudo apt-get install -y "${BUILD_PACKAGES[@]}"

fi

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

# Generate debian/changelog from CHANGELOG.md
if [ -f "${WORKSPACE_ROOT}/CHANGELOG.md" ]; then
  python3 - "${WORKSPACE_ROOT}" "${PKG_DIR}" <<'EOF'
import re
import sys
from datetime import datetime

WORKSPACE_ROOT = sys.argv[1]
PKG_DIR = sys.argv[2]

with open(f"{WORKSPACE_ROOT}/CHANGELOG.md") as f:
    content = f.read()

# Extract version sections
version_pattern = r'## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})\n\n(.*?)(?=\n## |\Z)'
matches = re.findall(version_pattern, content, re.DOTALL)

changelog_entries = []
for version, date, changes in matches:
    # Parse date
    dt = datetime.strptime(date, "%Y-%m-%d")
    deb_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

    # Extract changes
    change_lines = []
    for line in changes.strip().split('\n'):
        line = line.strip()
        if line.startswith('###'):
            continue
        if line.startswith('- '):
            change_lines.append(f"  * {line[2:]}")

    if not change_lines:
        change_lines = ["  * Release"]

    entry = f"""journalcheck ({version}-1) unstable; urgency=low

{chr(10).join(change_lines)}

 -- Guenter Sandner <www.gms@gmx.at>  {deb_date}
"""
    changelog_entries.append(entry)

with open(f"{PKG_DIR}/debian/changelog", "w") as f:
    f.write("\n".join(changelog_entries))
EOF
fi

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
