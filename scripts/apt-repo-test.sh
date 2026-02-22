#!/bin/bash
DN=$(dirname -- "${BASH_SOURCE[0]}")
cd "${DN}/.."


WORKSPACE_ROOT="$(pwd)"
TEST_DIR="${WORKSPACE_ROOT}/tmp/apt-repo-test-key"

if [ ! -f "${TEST_DIR}/gpg_passphrase" -o ! -f "${TEST_DIR}/gpg_private_key.asc" ]; then

  GPG_EXPORT=$(which gms-gpg-export)
  GEN_PASSWD=$(which gen-passwd)

  if [ -z "${GPG_EXPORT}" -o  -z "${GEN_PASSWD}" ]; then
    echo skipping
    exit 0
  fi

  set -e

  mkdir -p "${TEST_DIR}"

  export GPG_PASSPHRASE=$("${GEN_PASSWD}")
  echo "${GPG_PASSPHRASE}" >"${TEST_DIR}/gpg_passphrase"

  echo "please set password to: ${GPG_PASSPHRASE}"

  "${GPG_EXPORT}" "${TEST_DIR}/gpg_private_key"


else

  set -e
  export GPG_PASSPHRASE=$(cat "${TEST_DIR}/gpg_passphrase")

fi

export GPG_PRIVATE_KEY=$(cat "${TEST_DIR}/gpg_private_key.asc")


export GNUPGHOME="${WORKSPACE_ROOT}/tmp/apt-repo-test"

rm -rf "${GNUPGHOME}"
mkdir -p "${GNUPGHOME}"
chmod 700 "${GNUPGHOME}"

./scripts/apt-repo.sh


FPR=$(gpg --list-secret-keys --with-colons | grep "^fpr" | head -n 1 | cut -d: -f10)
if [ -n "${FPR}" ]; then
  echo "key having fingerprint ${FPR} is not cleaned up"
  RC=1
fi

GNUPGHOME=
RC=0
if ! gpg --verify repo/apt/InRelease; then
  echo "InRelease is not signed"
  RC=1
fi

if ! gpg --verify repo/apt/Release.gpg repo/apt/Release; then
  echo "Release.gpg is not signed"
  RC=1
fi


exit "${RC}"
