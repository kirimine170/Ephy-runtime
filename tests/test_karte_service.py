import json

from packages.config_core.loader import AppConfig, RagConfig, VectorDBConfig
from packages.karte_core.service import export_karte_bundle, import_karte_bundle
from packages.rag_core.schemas import IngestRequest, SearchRequest
from packages.rag_core.service import RagService


def test_import_karte_bundle_indexes_cards_with_project_and_tags(tmp_path) -> None:
    bundle = tmp_path / "karte.json"
    bundle.write_text(
        json.dumps(
            {
                "version": 1,
                "cards": [
                    {
                        "id": "board-meeting",
                        "title": "Board Meeting",
                        "body": "Employee roster was confirmed in the NPO board meeting.",
                        "project": "npo",
                        "tags": ["meeting", "roster"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    config = AppConfig(
        rag=RagConfig(embedding_provider="local_hash", embedding_dimensions=32),
        vector_db=VectorDBConfig(provider="local_json", store_path=str(tmp_path / "index.json")),
    )
    service = RagService(config=config)

    result = import_karte_bundle(
        rag_service=service,
        bundle_path=str(bundle),
        output_dir=str(tmp_path / "imported"),
    )
    search = service.search(SearchRequest(query="employee roster", project="npo", tags=["meeting"], top_k=5))

    assert result["imported_cards"] == 1
    assert result["indexed_documents"] == 1
    assert search["results"]
    assert search["results"][0]["project"] == "npo"
    assert "meeting" in search["results"][0]["tags"]


def test_export_karte_bundle_groups_indexed_sources(tmp_path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    notes = docs_dir / "notes.md"
    notes.write_text("# Research\n\nVector search for employee roster is documented here.", encoding="utf-8")

    config = AppConfig(
        rag=RagConfig(embedding_provider="local_hash", embedding_dimensions=32),
        vector_db=VectorDBConfig(provider="local_json", store_path=str(tmp_path / "index.json")),
    )
    service = RagService(config=config)
    service.ingest(IngestRequest(paths=[str(notes)], project="lab", recursive=False, tags=["research"]))

    output = tmp_path / "exported-karte.json"
    result = export_karte_bundle(
        rag_service=service,
        output_path=str(output),
        project="lab",
        tags=["research"],
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result["exported_cards"] == 1
    assert payload["cards"][0]["project"] == "lab"
    assert payload["cards"][0]["source_path"].endswith("/notes.md")
    assert "research" in payload["cards"][0]["tags"]
