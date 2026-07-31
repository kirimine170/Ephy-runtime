#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_DIR="${ROOT_DIR}/configs"

MODELS_LOCAL="${CONFIG_DIR}/models.local.yaml"
RAG_LOCAL="${CONFIG_DIR}/rag.local.yaml"

backup_if_exists() {
  local target="$1"

  if [[ -f "${target}" ]]; then
    local backup_path="${target}.bak.$(date +%Y%m%d-%H%M%S)"
    cp "${target}" "${backup_path}"
    echo "backed up ${target} -> ${backup_path}"
  fi
}

mkdir -p "${CONFIG_DIR}"

backup_if_exists "${MODELS_LOCAL}"
backup_if_exists "${RAG_LOCAL}"

cat >"${MODELS_LOCAL}" <<EOF
models:
  embedding:
    provider: llama_cpp
    model: qwen3-embedding-0.6b
    base_url: http://localhost:8090/v1
EOF

cat >"${RAG_LOCAL}" <<EOF
rag:
  embedding_provider: openai_compatible
  embedding_model_alias: embedding
  reranker_provider: local_overlap
  reranker_model_alias: reranker

vector_db:
  provider: qdrant
  url: http://localhost:6333
  collection: local_docs
  store_path: data/index/local_docs.json
EOF

cat <<EOF
applied full feature local overrides:
  ${MODELS_LOCAL}
  ${RAG_LOCAL}

notes:
  - embedding uses llama.cpp on http://127.0.0.1:8090/v1
  - vector db uses qdrant on http://127.0.0.1:6333
  - reranker stays local_overlap because no local reranker endpoint is configured in this workspace
EOF
