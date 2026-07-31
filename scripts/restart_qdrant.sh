#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/stop_qdrant.sh" || true
exec "${SCRIPT_DIR}/start_qdrant.sh"
