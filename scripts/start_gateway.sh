#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

UVICORN_ARGS=(apps.gateway.main:app --host 127.0.0.1 --port 8000)
if [[ "${GATEWAY_RELOAD:-0}" == "1" ]]; then
  UVICORN_ARGS+=(--reload)
fi

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  exec "${ROOT_DIR}/.venv/bin/python" -m uvicorn "${UVICORN_ARGS[@]}"
fi

exec python3 -m uvicorn "${UVICORN_ARGS[@]}"
