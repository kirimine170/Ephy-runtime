#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

"${SCRIPT_DIR}/stop_backend_stack.sh"

"${SCRIPT_DIR}/stop_qdrant.sh" >/dev/null
echo "stopped qdrant"
