import httpx

from packages.config_core.loader import AppConfig, ModelConfig, RagConfig, VectorDBConfig
from packages.runtime_core.smoke import SmokeRunner


def test_smoke_runner_reports_backend_checks() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "fast"}]})
        if request.url.path == "/collections/local_docs":
            return httpx.Response(200, json={"result": {"status": "green"}})
        if request.url.path == "/v1/embeddings":
            return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2]}]})
        if request.url.path == "/rerank":
            return httpx.Response(200, json={"results": [{"index": 0, "relevance_score": 0.9}]})
        raise AssertionError(f"Unexpected request: {request.url.path}")

    config = AppConfig(
        models={
            "embedding": ModelConfig(provider="llama_cpp", model="embed", base_url="http://testserver/v1"),
            "reranker": ModelConfig(provider="llama_cpp", model="rerank", base_url="http://testserver/v1"),
        },
        rag=RagConfig(
            embedding_provider="openai_compatible",
            embedding_model_alias="embedding",
            reranker_provider="openai_compatible",
            reranker_model_alias="reranker",
            reranker_endpoint_path="/rerank",
        ),
        vector_db=VectorDBConfig(provider="qdrant", url="http://testserver", collection="local_docs"),
    )
    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://testserver")
    runner = SmokeRunner(config=config, gateway_url="http://testserver", client=client)

    report = runner.run()

    assert report["ok"] is True
    assert {item["name"] for item in report["checks"]} == {
        "gateway_health",
        "gateway_models",
        "qdrant_collection",
        "embedding_endpoint",
        "reranker_endpoint",
    }
