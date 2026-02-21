#!/bin/bash
DN=$(dirname -- "${BASH_SOURCE[0]}"})
set -e
cd "${DN}/.."

#!/bin/bash
set -e

NEW_VERSION="${1}"
REPO_URL="https://github.com/gms1/journalcheck"
CHANGELOG="CHANGELOG.md"
DATE=$(date +%Y-%m-%d)

if [[ -z "${NEW_VERSION}" ]]; then
    echo "Usage: ./release.sh <version tag>"
    exit 1
fi

if ! grep -q "## \[Unreleased\]" "${CHANGELOG}"; then
    echo "ERROR: No [Unreleased] section found in ${CHANGELOG}"
    exit 1
fi

# 1. Update/Create the version header
# Replaces '## [Unreleased]' with the new version and adds a fresh Unreleased above it
sed -i "s/## \[Unreleased\]/## [Unreleased]\n\n## [${NEW_VERSION#v}] - ${DATE}/" "${CHANGELOG}"

# 2. Update Link References
OLD_VERSION_TAG=$(grep -oP '\[v?\d+\.\d+\.\d+\]: .*tag/\K(v?\d+\.\d+\.\d+)' "${CHANGELOG}" | head -n 1 || true)

if [ -n "${OLD_VERSION_TAG}" ]; then
  # Update existing Unreleased comparison
  sed -i "s|${OLD_VERSION_TAG}...HEAD|${NEW_VERSION}...HEAD|" "${CHANGELOG}"
  # Insert new tag link below Unreleased
  sed -i "/\[Unreleased\]:/a [${NEW_VERSION#v}]: ${REPO_URL}/releases/tag/${NEW_VERSION}" "${CHANGELOG}"
else
  echo -e "\n[Unreleased]: ${REPO_URL}/compare/${NEW_VERSION}...HEAD" >> "${CHANGELOG}"
  echo "[${NEW_VERSION#v}]: ${REPO_URL}/releases/tag/${NEW_VERSION}" >> "${CHANGELOG}"
fi

echo "Committing and tagging ${NEW_VERSION}..."
git add "${CHANGELOG}"
git commit -m "Prepare release ${NEW_VERSION}"
git tag -a "${NEW_VERSION}" -m "Release ${NEW_VERSION}"

cat << EOT

Done.

Version ${NEW_VERSION} is ready.

Review the changes and run: git push origin main --tags

EOT
