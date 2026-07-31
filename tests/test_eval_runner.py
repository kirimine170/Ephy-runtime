import asyncio
from unittest.mock import AsyncMock

from packages.config_core.loader import AppConfig, RagConfig, VectorDBConfig
from packages.eval_core.runner import EvalRunner
from packages.rag_core.schemas import IngestRequest
from packages.rag_core.service import RagService


def test_eval_runner_reports_source_hits(tmp_path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    notes = docs_dir / "meeting.md"
    notes.write_text("# Meeting\n\nThe employee roster was confirmed with Nagao.", encoding="utf-8")

    dataset = tmp_path / "eval.yaml"
    dataset.write_text(
        """
cases:
  - id: roster-check
    query: employee roster
    expected_sources:
      - meeting.md
""".strip(),
        encoding="utf-8",
    )

    config = AppConfig(
        rag=RagConfig(embedding_provider="local_hash", embedding_dimensions=32),
        vector_db=VectorDBConfig(provider="local_json", store_path=str(tmp_path / "index.json")),
    )
    rag_service = RagService(config=config)
    rag_service.ingest(IngestRequest(paths=[str(docs_dir)], project="lab"))

    runner = EvalRunner(config=config)
    report = asyncio.run(runner.run_dataset(str(dataset), project="lab", top_k=3, with_answer=False))

    assert report.total_cases == 1
    assert report.source_hit_rate == 1.0
    assert report.results[0].source_hit is True


def test_eval_runner_can_filter_to_single_source(tmp_path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    notes = docs_dir / "meeting.md"
    notes.write_text("# Meeting\n\nThe employee roster was confirmed with Nagao.", encoding="utf-8")
    other = docs_dir / "other.md"
    other.write_text("# Other\n\nAnother document.", encoding="utf-8")

    dataset = tmp_path / "eval.yaml"
    dataset.write_text(
        """
cases:
  - id: roster-check
    query: employee roster
    expected_sources:
      - meeting.md
""".strip(),
        encoding="utf-8",
    )

    config = AppConfig(
        rag=RagConfig(embedding_provider="local_hash", embedding_dimensions=32),
        vector_db=VectorDBConfig(provider="local_json", store_path=str(tmp_path / "index.json")),
    )
    rag_service = RagService(config=config)
    rag_service.ingest(IngestRequest(paths=[str(docs_dir)], project="lab"))

    runner = EvalRunner(config=config)
    report = asyncio.run(
        runner.run_dataset(
            str(dataset),
            project="lab",
            source_path=str(notes.resolve()),
            top_k=3,
            with_answer=False,
        )
    )

    assert report.total_cases == 1
    assert report.source_hit_rate == 1.0
    assert report.results[0].top_source.endswith("/meeting.md")


def test_eval_runner_reports_latency_and_token_usage_when_answer_enabled(tmp_path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    notes = docs_dir / "meeting.md"
    notes.write_text("# Meeting\n\nThe employee roster was confirmed with Nagao.", encoding="utf-8")

    dataset = tmp_path / "eval.yaml"
    dataset.write_text(
        """
cases:
  - id: roster-check
    query: employee roster
    expected_sources:
      - meeting.md
    expected_keywords:
      - employee
""".strip(),
        encoding="utf-8",
    )

    config = AppConfig(
        rag=RagConfig(embedding_provider="local_hash", embedding_dimensions=32),
        vector_db=VectorDBConfig(provider="local_json", store_path=str(tmp_path / "index.json")),
    )
    rag_service = RagService(config=config)
    rag_service.ingest(IngestRequest(paths=[str(docs_dir)], project="lab"))

    runner = EvalRunner(config=config)
    runner._rag_service.query = AsyncMock(return_value={
        "answer": "employee roster was confirmed",
        "sources": [{"source_path": str(notes.resolve())}],
        "raw_response": {
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 7,
                "total_tokens": 18,
            },
        },
    })
    report = asyncio.run(runner.run_dataset(str(dataset), project="lab", top_k=3, with_answer=True))

    assert report.total_cases == 1
    assert report.average_latency_ms is not None
    assert report.total_prompt_tokens == 11
    assert report.total_completion_tokens == 7
    assert report.total_tokens == 18
    assert report.style_pass_rate == 1.0
    assert report.results[0].latency_ms is not None
    assert report.results[0].total_tokens == 18
    assert report.results[0].style_pass is True
    assert report.results[0].style_violations == []
