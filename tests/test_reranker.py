import json

import httpx

from packages.config_core.loader import ModelConfig, RagConfig
from packages.rag_core.reranker import build_reranker
from packages.rag_core.schemas import SearchResult


def test_local_overlap_reranker_promotes_overlap() -> None:
    reranker = build_reranker(RagConfig(reranker_provider="local_overlap"), models={})
    results = [
        SearchResult(
            chunk_id="a",
            source_path="/tmp/a.md",
            heading_path=["Meeting"],
            project="lab",
            tags=[],
            chunk_text="general notes",
            score=0.8,
        ),
        SearchResult(
            chunk_id="b",
            source_path="/tmp/b.md",
            heading_path=["Employee Roster"],
            project="lab",
            tags=[],
            chunk_text="employee roster was reviewed",
            score=0.6,
        ),
    ]

    reranked = reranker.rerank("employee roster", results, limit=2)

    assert reranked[0].chunk_id == "b"


def test_openai_compatible_reranker_uses_endpoint_and_indices() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rerank"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "qwen3-reranker-0.6b"
        assert payload["query"] == "employee roster"
        assert len(payload["documents"]) == 2
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 1, "relevance_score": 0.91},
                    {"index": 0, "relevance_score": 0.22},
                ]
            },
        )

    reranker = build_reranker(
        RagConfig(
            reranker_provider="openai_compatible",
            reranker_model_alias="reranker",
            reranker_endpoint_path="/rerank",
        ),
        models={
            "reranker": ModelConfig(
                provider="llama_cpp",
                model="qwen3-reranker-0.6b",
                base_url="http://testserver/v1",
            )
        },
        client=httpx.Client(transport=httpx.MockTransport(handler), base_url="http://testserver"),
    )
    results = [
        SearchResult(
            chunk_id="a",
            source_path="/tmp/a.md",
            heading_path=["Meeting"],
            project="lab",
            tags=[],
            chunk_text="general notes",
            score=0.8,
        ),
        SearchResult(
            chunk_id="b",
            source_path="/tmp/b.md",
            heading_path=["Employee Roster"],
            project="lab",
            tags=[],
            chunk_text="employee roster was reviewed",
            score=0.6,
        ),
    ]

    reranked = reranker.rerank("employee roster", results, limit=2)

    assert reranked[0].chunk_id == "b"
    assert reranked[0].score == 0.91
