#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/stop_searxng.sh"
exec "${SCRIPT_DIR}/start_searxng_managed.sh"
