from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from packages.config_core.loader import ModelConfig, RagConfig
from .schemas import SearchResult


class Reranker:
    def rerank(self, query: str, results: list[SearchResult], limit: int) -> list[SearchResult]:
        raise NotImplementedError


@dataclass
class LocalOverlapReranker(Reranker):
    def rerank(self, query: str, results: list[SearchResult], limit: int) -> list[SearchResult]:
        query_terms = _tokenize(query)
        rescored: list[SearchResult] = []
        for result in results:
            text_terms = _tokenize(" ".join(result.heading_path) + "\n" + result.chunk_text)
            overlap = sum(1 for term in query_terms if term in text_terms)
            bonus = overlap / max(len(query_terms), 1) if query_terms else 0.0
            rescored.append(result.model_copy(update={"score": round(result.score + bonus, 4)}))
        rescored.sort(key=lambda item: item.score, reverse=True)
        return rescored[:limit]


@dataclass
class OpenAICompatibleReranker(Reranker):
    model_config: ModelConfig
    endpoint_path: str
    client: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=30.0))

    def rerank(self, query: str, results: list[SearchResult], limit: int) -> list[SearchResult]:
        if not results:
            return []
        if not self.model_config.base_url:
            raise ValueError("Reranker model config requires base_url")

        payload = {
            "model": self.model_config.model,
            "query": query,
            "documents": [self._document_text(result) for result in results],
            "top_n": min(limit, len(results)),
        }
        response = self.client.post(self._build_url(), json=payload)
        response.raise_for_status()
        data = response.json().get("results", [])

        rescored: list[SearchResult] = []
        for item in data:
            index = int(item.get("index", -1))
            if 0 <= index < len(results):
                score = float(item.get("relevance_score", item.get("score", 0.0)))
                rescored.append(results[index].model_copy(update={"score": round(score, 4)}))

        if not rescored:
            return results[:limit]
        rescored.sort(key=lambda item: item.score, reverse=True)
        return rescored[:limit]

    def _build_url(self) -> str:
        base = self.model_config.base_url.rstrip("/")
        if self.endpoint_path.startswith("/"):
            parsed = urlparse(base)
            return f"{parsed.scheme}://{parsed.netloc}{self.endpoint_path}"
        return f"{base}/{self.endpoint_path.lstrip('/')}"

    @staticmethod
    def _document_text(result: SearchResult) -> str:
        heading = " > ".join(result.heading_path)
        if heading:
            return f"{heading}\n{result.chunk_text}"
        return result.chunk_text


def build_reranker(
    config: RagConfig,
    models: dict[str, ModelConfig],
    client: httpx.Client | None = None,
) -> Reranker:
    if config.reranker_provider == "local_overlap":
        return LocalOverlapReranker()
    if config.reranker_provider == "openai_compatible":
        try:
            model_config = models[config.reranker_model_alias]
        except KeyError as exc:
            raise ValueError(f"Unknown reranker model alias '{config.reranker_model_alias}'") from exc
        return OpenAICompatibleReranker(
            model_config=model_config,
            endpoint_path=config.reranker_endpoint_path,
            client=client or httpx.Client(timeout=30.0),
        )
    raise ValueError(f"Unsupported reranker provider '{config.reranker_provider}'")


def _tokenize(text: str) -> set[str]:
    normalized = text.lower()
    latin_tokens = re.findall(r"[a-z0-9_]+", normalized)
    japanese_runs = re.findall(r"[\u3040-\u30ff\u3400-\u9fff]+", normalized)
    japanese_tokens = [run for run in japanese_runs if len(run) > 1]
    return {token for token in [*latin_tokens, *japanese_tokens] if len(token) > 1}
