from packages.config_core.loader import AppConfig, RagConfig, VectorDBConfig
from packages.rag_core.service import RagService
from packages.runtime_core.watch import run_watch_loop


def test_watch_loop_reingests_on_change(tmp_path, monkeypatch) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    note = docs_dir / "note.md"
    note.write_text("# Notes\n\nfirst version", encoding="utf-8")

    monkeypatch.setattr("packages.runtime_core.watch.time.sleep", lambda _: None)

    config = AppConfig(
        rag=RagConfig(embedding_provider="local_hash", embedding_dimensions=32),
        vector_db=VectorDBConfig(provider="local_json", store_path=str(tmp_path / "index.json")),
    )
    service = RagService(config=config)

    original_build_snapshot = None
    import packages.runtime_core.watch as watch_module

    original_build_snapshot = watch_module._build_snapshot
    call_count = {"count": 0}

    def fake_snapshot(paths, recursive):
        call_count["count"] += 1
        if call_count["count"] == 2:
            note.write_text("# Notes\n\nsecond version", encoding="utf-8")
        return original_build_snapshot(paths, recursive)

    monkeypatch.setattr(watch_module, "_build_snapshot", fake_snapshot)

    events = run_watch_loop(
        rag_service=service,
        paths=[str(docs_dir)],
        project="lab",
        recursive=True,
        tags=[],
        interval_seconds=0,
        max_cycles=2,
    )

    assert events[0]["event"] == "initial_ingest"
    assert any(event["event"] == "reingest" for event in events[1:])
