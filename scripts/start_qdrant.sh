#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_runtime_common.sh"

cd "${ROOT_DIR}"
require_qdrant_bin >/dev/null
start_managed_process "qdrant" "${ROOT_DIR}/scripts/run_qdrant.sh" "${QDRANT_LOG_FILE}" "${QDRANT_PID_FILE}"
