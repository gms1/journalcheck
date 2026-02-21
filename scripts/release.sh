#!/bin/bash
DN=$(dirname -- "${BASH_SOURCE[0]}"})
set -e
cd "${DN}/.."

#!/bin/bash
set -e

NEW_VERSION_TAG="${1}"
NEW_VERSION="${NEW_VERSION_TAG#v}"
REPO_URL="https://github.com/gms1/journalcheck"
CHANGELOG="CHANGELOG.md"
VERSION_FILE="src/journalcheck/__init__.py"
DATE=$(date +%Y-%m-%d)

if [[ -z "${NEW_VERSION_TAG}" ]]; then
    echo "Usage: ./release.sh <version tag>"
    exit 1
fi

if ! grep -q "## \[Unreleased\]" "${CHANGELOG}"; then
    echo "ERROR: No [Unreleased] section found in ${CHANGELOG}"
    exit 1
fi

# Update version in VERSION_FILE
sed -i "s/__version__ = .*/__version__ = \"${NEW_VERSION}\"/" "${VERSION_FILE}"

# Update/Create the version header in CHANGELOG.md
# Replaces '## [Unreleased]' with the new version and adds a fresh Unreleased above it
sed -i "s/## \[Unreleased\]/## [Unreleased]\n\n## [${NEW_VERSION_TAG#v}] - ${DATE}/" "${CHANGELOG}"

# Update Link References
OLD_VERSION_TAG=$(grep -oP '\[v?\d+\.\d+\.\d+\]: .*tag/\K(v?\d+\.\d+\.\d+)' "${CHANGELOG}" | head -n 1 || true)

if [ -n "${OLD_VERSION_TAG}" ]; then
  # Update existing Unreleased comparison
  sed -i "s|${OLD_VERSION_TAG}...HEAD|${NEW_VERSION_TAG}...HEAD|" "${CHANGELOG}"
  # Insert new tag link below Unreleased
  sed -i "/\[Unreleased\]:/a [${NEW_VERSION_TAG#v}]: ${REPO_URL}/releases/tag/${NEW_VERSION_TAG}" "${CHANGELOG}"
else
  echo -e "\n[Unreleased]: ${REPO_URL}/compare/${NEW_VERSION_TAG}...HEAD" >> "${CHANGELOG}"
  echo "[${NEW_VERSION_TAG#v}]: ${REPO_URL}/releases/tag/${NEW_VERSION_TAG}" >> "${CHANGELOG}"
fi

echo "Committing and tagging ${NEW_VERSION_TAG}..."
git add "${CHANGELOG}" "${VERSION_FILE}"
git commit -m "Prepare release ${NEW_VERSION_TAG}"
git tag -a "${NEW_VERSION_TAG}" -m "Release ${NEW_VERSION_TAG}"

cat << EOT

Done.

Version ${NEW_VERSION_TAG} is ready.

Review the changes and run: git push origin main --tags

EOT
