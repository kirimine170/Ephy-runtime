from __future__ import annotations

from dataclasses import dataclass

import httpx

from packages.config_core.loader import AppConfig, ModelConfig


@dataclass
class SmokeCheck:
    name: str
    ok: bool
    detail: str


class SmokeRunner:
    def __init__(self, config: AppConfig, gateway_url: str = "http://127.0.0.1:8000", client: httpx.Client | None = None) -> None:
        self._config = config
        self._gateway_url = gateway_url.rstrip("/")
        self._client = client or httpx.Client(timeout=15.0)

    def run(self, include_embedding: bool = True, include_reranker: bool = True, include_qdrant: bool = True) -> dict:
        checks: list[SmokeCheck] = []
        checks.append(self._check_gateway_health())
        checks.append(self._check_gateway_models())
        if include_qdrant and self._config.vector_db.provider == "qdrant":
            checks.append(self._check_qdrant())
        if include_embedding and self._config.rag.embedding_provider == "openai_compatible":
            checks.append(self._check_embeddings())
        if include_reranker and self._config.rag.reranker_provider == "openai_compatible":
            checks.append(self._check_reranker())

        return {
            "ok": all(check.ok for check in checks),
            "checks": [check.__dict__ for check in checks],
        }

    def _check_gateway_health(self) -> SmokeCheck:
        try:
            response = self._client.get(f"{self._gateway_url}/health")
            response.raise_for_status()
            status = response.json().get("status")
            return SmokeCheck("gateway_health", status == "ok", f"status={status}")
        except Exception as exc:
            return SmokeCheck("gateway_health", False, str(exc))

    def _check_gateway_models(self) -> SmokeCheck:
        try:
            response = self._client.get(f"{self._gateway_url}/v1/models")
            response.raise_for_status()
            count = len(response.json().get("data", []))
            return SmokeCheck("gateway_models", count > 0, f"models={count}")
        except Exception as exc:
            return SmokeCheck("gateway_models", False, str(exc))

    def _check_qdrant(self) -> SmokeCheck:
        try:
            url = (self._config.vector_db.url or "http://localhost:6333").rstrip("/")
            response = self._client.get(f"{url}/collections/{self._config.vector_db.collection}")
            response.raise_for_status()
            return SmokeCheck("qdrant_collection", True, f"collection={self._config.vector_db.collection}")
        except Exception as exc:
            return SmokeCheck("qdrant_collection", False, str(exc))

    def _check_embeddings(self) -> SmokeCheck:
        try:
            model = self._require_model(self._config.rag.embedding_model_alias)
            response = self._client.post(
                f"{model.base_url.rstrip('/')}/embeddings",
                json={"model": model.model, "input": "smoke check"},
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            dims = len(data[0].get("embedding", [])) if data else 0
            return SmokeCheck("embedding_endpoint", dims > 0, f"dims={dims}")
        except Exception as exc:
            return SmokeCheck("embedding_endpoint", False, str(exc))

    def _check_reranker(self) -> SmokeCheck:
        try:
            model = self._require_model(self._config.rag.reranker_model_alias)
            endpoint = self._config.rag.reranker_endpoint_path
            base = model.base_url.rstrip("/")
            if endpoint.startswith("/"):
                from urllib.parse import urlparse

                parsed = urlparse(base)
                url = f"{parsed.scheme}://{parsed.netloc}{endpoint}"
            else:
                url = f"{base}/{endpoint.lstrip('/')}"
            response = self._client.post(
                url,
                json={
                    "model": model.model,
                    "query": "smoke check",
                    "documents": ["first document", "second document"],
                    "top_n": 1,
                },
            )
            response.raise_for_status()
            count = len(response.json().get("results", []))
            return SmokeCheck("reranker_endpoint", count > 0, f"results={count}")
        except Exception as exc:
            return SmokeCheck("reranker_endpoint", False, str(exc))

    def _require_model(self, alias: str) -> ModelConfig:
        try:
            return self._config.models[alias]
        except KeyError as exc:
            raise ValueError(f"Unknown model alias '{alias}'") from exc
