from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field

import httpx

from packages.config_core.loader import ModelConfig, RagConfig


class Embedder:
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


@dataclass
class LocalHashEmbedder(Embedder):
    dimensions: int = 64

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        terms = re.findall(r"[\w\u3040-\u30ff\u3400-\u9fff]+", text.lower())
        features = list(terms)
        normalized_text = "".join(terms)
        features.extend(_character_ngrams(normalized_text, 2))
        features.extend(_character_ngrams(normalized_text, 3))
        if not features:
            return vector

        for feature in features:
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            for index in range(self.dimensions):
                byte = digest[index % len(digest)]
                vector[index] += (byte / 255.0) - 0.5

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


@dataclass
class OpenAICompatibleEmbedder(Embedder):
    model_config: ModelConfig
    client: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=30.0))

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.model_config.base_url:
            raise ValueError("Embedding model config requires base_url")
        try:
            response = self.client.post(
                f"{self.model_config.base_url.rstrip('/')}/embeddings",
                json={
                    "model": self.model_config.model,
                    "input": texts,
                },
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data", [])
            if not data:
                raise ValueError("Embedding endpoint returned no data")
            ordered = sorted(data, key=lambda item: int(item.get("index", 0)))
            embeddings: list[list[float]] = []
            for item in ordered:
                embedding = item.get("embedding")
                if not isinstance(embedding, list):
                    raise ValueError("Embedding endpoint returned invalid embedding payload")
                embeddings.append([float(value) for value in embedding])
            if len(embeddings) != len(texts):
                raise ValueError(
                    f"Embedding endpoint returned {len(embeddings)} vectors for {len(texts)} inputs"
                )
            return embeddings
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Embedding backend request failed for model '{self.model_config.model}': {exc}") from exc


@dataclass
class ResilientEmbedder(Embedder):
    primary: Embedder
    fallback: Embedder

    def embed(self, text: str) -> list[float]:
        try:
            return self.primary.embed(text)
        except (RuntimeError, ValueError):
            return self.fallback.embed(text)


def build_embedder(
    config: RagConfig,
    models: dict[str, ModelConfig],
    client: httpx.Client | None = None,
) -> Embedder:
    if config.embedding_provider == "local_hash":
        return LocalHashEmbedder(dimensions=config.embedding_dimensions)
    if config.embedding_provider == "openai_compatible":
        try:
            model_config = models[config.embedding_model_alias]
        except KeyError as exc:
            raise ValueError(f"Unknown embedding model alias '{config.embedding_model_alias}'") from exc
        # Index and query vectors must always come from the same embedding space.
        # Falling back per request can silently make an existing index unsearchable.
        return OpenAICompatibleEmbedder(
            model_config=model_config,
            client=client or httpx.Client(timeout=30.0),
        )
    raise ValueError(f"Unsupported embedding provider '{config.embedding_provider}'")


def _character_ngrams(text: str, size: int) -> list[str]:
    if len(text) < size:
        return [text] if text else []
    return [text[index : index + size] for index in range(len(text) - size + 1)]
