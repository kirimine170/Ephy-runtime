#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/start_backend_stack.sh" "$@"
exec "${SCRIPT_DIR}/start_wails.sh"
