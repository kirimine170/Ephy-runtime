#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/check_runtime_setup.sh"
"${SCRIPT_DIR}/apply_full_feature_overrides.sh"
"${SCRIPT_DIR}/start_backend_stack.sh" --with-embedding --with-qdrant
exec "${SCRIPT_DIR}/start_wails.sh"
