#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
usage: ./scripts/start_full_feature.sh [command]

commands:
  start      start full feature stack: llama.cpp x4 + qdrant + gateway + wails
  check      verify runtime files and resolved model paths
  commands   print startup command summary and manual llama.cpp commands
  backend    start backend stack only with embedding + qdrant
  ui         start Wails UI only
  stop       stop managed backend processes and qdrant

notes:
  - default command is: start
  - model files are resolved from ./llama.cpp/models/
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || "${1:-}" == "help" ]]; then
  usage
  exit 0
fi

COMMAND="${1:-start}"

case "${COMMAND}" in
  start)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" start-full "$@"
    ;;
  check)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" check "$@"
    ;;
  commands)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" commands "$@"
    ;;
  backend)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" start-backend --with-embedding --with-qdrant "$@"
    ;;
  ui)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" start-ui "$@"
    ;;
  stop)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" stop-full "$@"
    ;;
  *)
    echo "unknown command: ${COMMAND}" >&2
    usage >&2
    exit 1
    ;;
esac
