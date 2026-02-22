#!/bin/bash
DN=$(dirname -- "${BASH_SOURCE[0]}")
set -e
cd "${DN}/.."

BASE_PATH="apt"
REPO_PATH=repo/${BASE_PATH}

if ! dpkg -s "apt-utils" &> /dev/null; then

  sudo apt-get update
  sudo apt-get install -y "apt-utils"

fi

mkdir -p "${REPO_PATH}"

cp -a dist/*.deb "${REPO_PATH}/"
cp -a public.gpg "${REPO_PATH}/"
cd "${REPO_PATH}"

apt-ftparchive packages . > Packages
gzip -n -k -f Packages

apt-ftparchive release . > Release


function cleanup {
  set +e
  trap '' "EXIT"
  if [ -z "${FPR}" ]; then
    echo "FINGERPRINT is not available, skipping GPG cleanup."
    return
  fi
  echo "GPG KEYS cleaning..."
  gpg --batch --yes --delete-secret-keys "${FPR}"
  gpg --batch --yes --delete-keys "${FPR}"
  echo "GPG KEYS deleted"
}


echo "${GPG_PRIVATE_KEY}" | gpg --batch --import &>/dev/null
FPR=$(gpg --with-colons --list-secret-keys | awk -F: '$1 == "fpr" {print $10; exit}')
if [[ ${#FPR} -ne 40 ]]; then
    echo "failed to get fingerpring, got: ${FPR}"
    exit 1
fi
trap cleanup EXIT

echo "${GPG_PASSPHRASE}" | gpg --batch --yes --pinentry-mode loopback \
  --default-key "${FPR}" --passphrase-fd 0 --clearsign -o InRelease Release

echo "${GPG_PASSPHRASE}" | gpg --batch --yes --pinentry-mode loopback \
  --default-key "${FPR}" --passphrase-fd 0 -abs -o Release.gpg Release


cleanup
echo "done"
