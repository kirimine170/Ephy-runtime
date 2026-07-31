#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_runtime_common.sh"

stop_pid_file "${PID_DIR}/gateway.pid" "gateway"
stop_pid_file "${SEARXNG_PID_FILE}" "searxng"
stop_pid_file "${PID_DIR}/embedding.pid" "embedding"
stop_pid_file "${PID_DIR}/code.pid" "code"
stop_pid_file "${PID_DIR}/work.pid" "work"
stop_pid_file "${PID_DIR}/fast.pid" "fast"
