import json

import httpx

from packages.config_core.loader import ModelConfig, RagConfig
from packages.rag_core.embedding import OpenAICompatibleEmbedder, build_embedder


def test_openai_compatible_embedder_calls_embeddings_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/embeddings"
        assert request.method == "POST"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "qwen3-embedding-0.6b"
        inputs = payload["input"]
        assert inputs == ["employee roster"]
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "index": 0,
                        "embedding": [0.1, 0.2, 0.3],
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://testserver")
    embedder = OpenAICompatibleEmbedder(
        model_config=ModelConfig(
            provider="llama_cpp",
            model="qwen3-embedding-0.6b",
            base_url="http://testserver/v1",
        ),
        client=client,
    )

    embedding = embedder.embed("employee roster")

    assert embedding == [0.1, 0.2, 0.3]


def test_openai_compatible_embedder_batches_and_restores_index_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["input"] == ["first", "second"]
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [2.0]},
                    {"index": 0, "embedding": [1.0]},
                ]
            },
        )

    embedder = OpenAICompatibleEmbedder(
        model_config=ModelConfig(
            provider="llama_cpp",
            model="qwen3-embedding-0.6b",
            base_url="http://testserver/v1",
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler), base_url="http://testserver"),
    )

    assert embedder.embed_many(["first", "second"]) == [[1.0], [2.0]]


def test_build_embedder_uses_model_alias_for_openai_compatible() -> None:
    embedder = build_embedder(
        RagConfig(embedding_provider="openai_compatible", embedding_model_alias="embedding"),
        models={
            "embedding": ModelConfig(
                provider="llama_cpp",
                model="qwen3-embedding-0.6b",
                base_url="http://localhost:8090/v1",
            )
        },
        client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.5]}]}))),
    )

    assert embedder.embed("test") == [0.5]
