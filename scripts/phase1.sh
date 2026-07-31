#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
usage: ./scripts/phase1.sh [command]

commands:
  start      start phase1 default stack: llama.cpp x4 + qdrant + gateway + wails
  full       start full feature stack: llama.cpp x4 + qdrant + gateway + wails
  check      verify runtime files and resolved model paths
  commands   print startup command summary and manual llama.cpp commands
  backend    start backend stack with embedding and local qdrant enabled by default
  ui         start Wails UI only
  stop       stop managed backend processes and qdrant
  restart    restart full feature stack including qdrant
  qdrant     start qdrant only
  qdrant-stop stop qdrant only
  qdrant-restart restart qdrant only
  searxng    start local SearXNG only
  searxng-stop stop local SearXNG only
  searxng-restart restart local SearXNG only
  searxng-setup install pinned SearXNG into tools/searxng and enable web search

notes:
  - default command is: start
  - model files are resolved from ./llama.cpp/models/
  - this path is Docker-independent by default
  - qdrant local binary is included by default; pass --without-qdrant to skip it
  - embedding is included by default; pass --without-embedding to skip it
EOF
}

COMMAND="${1:-start}"

case "${COMMAND}" in
  start)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" start-default "$@"
    ;;
  full)
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
    exec "${SCRIPT_DIR}/workbench.sh" start-backend "$@"
    ;;
  ui)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" start-ui "$@"
    ;;
  stop)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" stop-full "$@"
    ;;
  restart)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" restart-full "$@"
    ;;
  qdrant)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" start-qdrant "$@"
    ;;
  qdrant-stop)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" stop-qdrant "$@"
    ;;
  qdrant-restart)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" restart-qdrant "$@"
    ;;
  searxng)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" start-searxng "$@"
    ;;
  searxng-stop)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" stop-searxng "$@"
    ;;
  searxng-restart)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" restart-searxng "$@"
    ;;
  searxng-setup)
    shift || true
    exec "${SCRIPT_DIR}/workbench.sh" setup-searxng "$@"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "unknown command: ${COMMAND}" >&2
    usage >&2
    exit 1
    ;;
esac
