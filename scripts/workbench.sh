#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
usage: ./scripts/workbench.sh <command> [args]

commands:
  check                 verify runtime files and resolved model paths
  commands              print startup command summary and manual llama.cpp commands
  doctor                alias of check
  start-full            start full feature stack: llama.cpp x4 + qdrant + gateway + wails
  start-phase1          start Docker-independent phase1 stack: llama.cpp x3 + gateway + wails
  start-backend         start backend stack only; pass through args such as --with-embedding --with-qdrant
  start-qdrant          start qdrant only
  start-ui              start Wails UI only
  start-default         start default stack: fast/work/code/gateway + wails
  stop-backend          stop managed backend processes
  stop-qdrant           stop qdrant only
  stop-full             stop managed backend processes and qdrant
  restart-full          restart full feature stack including qdrant
  restart-qdrant        restart qdrant only
  start-searxng         start local SearXNG only
  stop-searxng          stop local SearXNG only
  restart-searxng       restart local SearXNG only
  setup-searxng         install pinned Docker-free SearXNG runtime
  apply-overrides       write full-feature local override configs

notes:
  - model files in this workspace live under ./llama.cpp/models/
  - Docker-independent startup: ./scripts/workbench.sh start-phase1
  - full feature startup with Qdrant: ./scripts/workbench.sh start-full
EOF
}

COMMAND="${1:-}"

case "${COMMAND}" in
  check|doctor)
    shift
    exec "${SCRIPT_DIR}/check_runtime_setup.sh" "$@"
    ;;
  commands)
    shift
    exec "${SCRIPT_DIR}/print_startup_commands.sh" "$@"
    ;;
  start-full)
    shift
    exec "${SCRIPT_DIR}/start_full_feature_stack.sh" "$@"
    ;;
  start-phase1)
    shift
    exec "${SCRIPT_DIR}/start_full_stack.sh" "$@"
    ;;
  start-backend)
    shift
    exec "${SCRIPT_DIR}/start_backend_stack.sh" "$@"
    ;;
  start-qdrant)
    shift
    exec "${SCRIPT_DIR}/start_qdrant.sh" "$@"
    ;;
  start-ui)
    shift
    exec "${SCRIPT_DIR}/start_wails.sh" "$@"
    ;;
  start-default)
    shift
    exec "${SCRIPT_DIR}/start_full_stack.sh" "$@"
    ;;
  stop-backend)
    shift
    exec "${SCRIPT_DIR}/stop_backend_stack.sh" "$@"
    ;;
  stop-qdrant)
    shift
    exec "${SCRIPT_DIR}/stop_qdrant.sh" "$@"
    ;;
  stop-full)
    shift
    exec "${SCRIPT_DIR}/stop_complete_stack.sh" "$@"
    ;;
  restart-full)
    shift
    "${SCRIPT_DIR}/stop_complete_stack.sh" "$@"
    exec "${SCRIPT_DIR}/start_full_feature_stack.sh"
    ;;
  restart-qdrant)
    shift
    exec "${SCRIPT_DIR}/restart_qdrant.sh" "$@"
    ;;
  start-searxng)
    shift
    exec "${SCRIPT_DIR}/start_searxng_managed.sh" "$@"
    ;;
  stop-searxng)
    shift
    exec "${SCRIPT_DIR}/stop_searxng.sh" "$@"
    ;;
  restart-searxng)
    shift
    exec "${SCRIPT_DIR}/restart_searxng.sh" "$@"
    ;;
  setup-searxng)
    shift
    exec "${SCRIPT_DIR}/setup_searxng.sh" "$@"
    ;;
  apply-overrides)
    shift
    exec "${SCRIPT_DIR}/apply_full_feature_overrides.sh" "$@"
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "unknown command: ${COMMAND}" >&2
    usage >&2
    exit 1
    ;;
esac
