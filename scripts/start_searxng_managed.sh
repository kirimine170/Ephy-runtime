#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_runtime_common.sh"

start_managed_process "searxng" "${ROOT_DIR}/scripts/start_searxng.sh" "${SEARXNG_LOG_FILE}" "${SEARXNG_PID_FILE}"
wait_for_http_ready "searxng" "http://${SEARXNG_HOST}:${SEARXNG_PORT}/healthz" "${SEARXNG_PID_FILE}" "${SEARXNG_LOG_FILE}" "X-Forwarded-For: 127.0.0.1"
