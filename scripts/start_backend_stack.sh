#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_runtime_common.sh"

WITH_EMBEDDING=1
WITH_QDRANT=1

for arg in "$@"; do
  case "${arg}" in
    --with-embedding)
      WITH_EMBEDDING=1
      ;;
    --without-embedding)
      WITH_EMBEDDING=0
      ;;
    --with-qdrant)
      WITH_QDRANT=1
      ;;
    --without-qdrant)
      WITH_QDRANT=0
      ;;
    *)
      echo "unknown argument: ${arg}" >&2
      echo "usage: ./scripts/start_backend_stack.sh [--with-embedding] [--without-embedding] [--with-qdrant] [--without-qdrant]" >&2
      exit 1
      ;;
  esac
done

cd "${ROOT_DIR}"

start_managed_process "fast" "${ROOT_DIR}/scripts/start_llama_fast.sh" "${LOG_DIR}/fast.log" "${PID_DIR}/fast.pid"
start_managed_process "work" "${ROOT_DIR}/scripts/start_llama_work.sh" "${LOG_DIR}/work.log" "${PID_DIR}/work.pid"
start_managed_process "code" "${ROOT_DIR}/scripts/start_llama_code.sh" "${LOG_DIR}/code.log" "${PID_DIR}/code.pid"

if [[ "${WITH_EMBEDDING}" -eq 1 ]]; then
  start_managed_process "embedding" "${ROOT_DIR}/scripts/start_llama_embedding.sh" "${LOG_DIR}/embedding.log" "${PID_DIR}/embedding.pid"
else
  echo "embedding skipped (--without-embedding)"
fi

wait_for_http_ready "fast model" "http://127.0.0.1:8081/health" "${PID_DIR}/fast.pid" "${LOG_DIR}/fast.log"
wait_for_http_ready "work model" "http://127.0.0.1:8082/health" "${PID_DIR}/work.pid" "${LOG_DIR}/work.log"
wait_for_http_ready "code model" "http://127.0.0.1:8083/health" "${PID_DIR}/code.pid" "${LOG_DIR}/code.log"
if [[ "${WITH_EMBEDDING}" -eq 1 ]]; then
  wait_for_http_ready "embedding model" "http://127.0.0.1:8090/health" "${PID_DIR}/embedding.pid" "${LOG_DIR}/embedding.log"
fi

if [[ "${WITH_QDRANT}" -eq 1 ]]; then
  "${ROOT_DIR}/scripts/start_qdrant.sh"
  wait_for_http_ready "qdrant" "http://127.0.0.1:${QDRANT_HTTP_PORT}/healthz" "${QDRANT_PID_FILE}" "${QDRANT_LOG_FILE}"
else
  echo "qdrant skipped (--without-qdrant)"
fi

if web_search_enabled; then
  start_managed_process "searxng" "${ROOT_DIR}/scripts/start_searxng.sh" "${SEARXNG_LOG_FILE}" "${SEARXNG_PID_FILE}"
  wait_for_http_ready "searxng" "http://${SEARXNG_HOST}:${SEARXNG_PORT}/healthz" "${SEARXNG_PID_FILE}" "${SEARXNG_LOG_FILE}" "X-Forwarded-For: 127.0.0.1"
else
  echo "searxng skipped (web_search.enabled=false)"
fi

start_managed_process "gateway" "${ROOT_DIR}/scripts/start_gateway.sh" "${LOG_DIR}/gateway.log" "${PID_DIR}/gateway.pid"
wait_for_http_ready "gateway" "http://127.0.0.1:8000/health" "${PID_DIR}/gateway.pid" "${LOG_DIR}/gateway.log"

cat <<EOF

backend stack started
logs:
  ${LOG_DIR}/fast.log
  ${LOG_DIR}/work.log
  ${LOG_DIR}/code.log
  ${LOG_DIR}/gateway.log
$(if web_search_enabled; then printf '  %s\n' "${SEARXNG_LOG_FILE}"; fi)
$(if [[ "${WITH_EMBEDDING}" -eq 1 ]]; then printf '  %s\n' "${LOG_DIR}/embedding.log"; fi)

stop:
  ./scripts/stop_backend_stack.sh

health check:
  curl http://127.0.0.1:8000/health
EOF
