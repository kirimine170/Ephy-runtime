#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_runtime_common.sh"

stop_pid_file "${SEARXNG_PID_FILE}" "searxng"
