#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_runtime_common.sh"

SEARXNG_REPOSITORY="${SEARXNG_REPOSITORY:-https://github.com/searxng/searxng.git}"
# SearXNG is rolling-release software; keep a reviewed revision instead of tracking main.
SEARXNG_REF="${SEARXNG_REF:-9e25585aecd9f6ab1fdf30922da64fd91eb25425}"

mkdir -p "${SEARXNG_ROOT_DIR}"
if [[ ! -d "${SEARXNG_SOURCE_DIR}/.git" ]]; then
  git clone --filter=blob:none "${SEARXNG_REPOSITORY}" "${SEARXNG_SOURCE_DIR}"
fi

if ! git -C "${SEARXNG_SOURCE_DIR}" cat-file -e "${SEARXNG_REF}^{commit}" 2>/dev/null; then
  git -C "${SEARXNG_SOURCE_DIR}" fetch --depth 1 origin "${SEARXNG_REF}"
fi
git -C "${SEARXNG_SOURCE_DIR}" checkout --detach "${SEARXNG_REF}"

python3 -m venv "${SEARXNG_VENV_DIR}"
"${SEARXNG_VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel
"${SEARXNG_VENV_DIR}/bin/python" -m pip install pyyaml msgspec typing-extensions pybind11
"${SEARXNG_VENV_DIR}/bin/python" -m pip install --use-pep517 --no-build-isolation -e "${SEARXNG_SOURCE_DIR}"

if [[ ! -f "${ROOT_DIR}/configs/web.local.yaml" ]]; then
  cp "${ROOT_DIR}/configs/web.local.yaml.example" "${ROOT_DIR}/configs/web.local.yaml"
  echo "enabled web search: ${ROOT_DIR}/configs/web.local.yaml"
fi

write_searxng_config
cat <<EOF
SearXNG installed at ${SEARXNG_SOURCE_DIR}
revision: ${SEARXNG_REF}

start:
  ./scripts/phase1.sh searxng

full stack:
  ./scripts/phase1.sh restart
EOF
