from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import yaml

from packages.rag_core.schemas import IngestRequest
from packages.rag_core.service import RagService
from .schemas import KarteBundle, KarteCard


def import_karte_bundle(
    *,
    rag_service: RagService,
    bundle_path: str,
    output_dir: str,
    default_project: str | None = None,
    default_tags: list[str] | None = None,
) -> dict:
    bundle_file = Path(bundle_path).resolve()
    bundle = _load_bundle(bundle_file)
    destination_root = Path(output_dir).resolve()
    destination_root.mkdir(parents=True, exist_ok=True)

    imported_cards = 0
    indexed_documents = 0
    indexed_chunks = 0
    written_paths: list[str] = []
    projects: set[str] = set()

    for index, card in enumerate(bundle.cards, start=1):
        project = (card.project or default_project or "karte").strip()
        tags = _normalize_tags([*(default_tags or []), *card.tags])
        projects.add(project)

        project_dir = destination_root / project
        project_dir.mkdir(parents=True, exist_ok=True)
        stem = _safe_stem(card.id or card.title or f"karte-card-{index}")
        file_path = project_dir / f"{stem}.md"
        file_path.write_text(_render_card_markdown(card), encoding="utf-8")
        written_paths.append(str(file_path))

        ingest_result = rag_service.ingest(
            IngestRequest(
                paths=[str(file_path)],
                project=project,
                recursive=False,
                tags=tags,
            )
        )
        imported_cards += 1
        indexed_documents += int(ingest_result.get("indexed_documents", 0))
        indexed_chunks += int(ingest_result.get("indexed_chunks", 0))

    return {
        "bundle_path": str(bundle_file),
        "output_dir": str(destination_root),
        "imported_cards": imported_cards,
        "indexed_documents": indexed_documents,
        "indexed_chunks": indexed_chunks,
        "projects": sorted(projects),
        "written_paths": written_paths,
    }


def export_karte_bundle(
    *,
    rag_service: RagService,
    output_path: str,
    project: str | None = None,
    source_query: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    chunks = rag_service._vector_store.load_chunks(project=project)  # noqa: SLF001
    normalized_source_query = (source_query or "").strip().lower()
    required_tags = set(_normalize_tags(tags or []))

    grouped: dict[str, list] = defaultdict(list)
    for chunk in chunks:
        if normalized_source_query and normalized_source_query not in chunk.source_path.lower():
            continue
        if required_tags and not required_tags.issubset(set(chunk.tags)):
            continue
        grouped[chunk.source_path].append(chunk)

    cards: list[KarteCard] = []
    for source_path, source_chunks in sorted(grouped.items()):
        source_chunks.sort(key=lambda item: (tuple(item.heading_path), item.chunk_id))
        first = source_chunks[0]
        title = first.heading_path[-1] if first.heading_path else Path(source_path).stem
        body = "\n\n".join(
            _format_chunk_body(chunk.heading_path, chunk.chunk_text)
            for chunk in source_chunks
        ).strip()
        cards.append(
            KarteCard(
                id=_safe_stem(Path(source_path).stem),
                title=title,
                body=body,
                project=first.project,
                tags=_normalize_tags([tag for chunk in source_chunks for tag in chunk.tags]),
                source_path=source_path,
            )
        )

    bundle = KarteBundle(version=1, cards=cards)
    output_file = Path(output_path).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(bundle.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "output_path": str(output_file),
        "exported_cards": len(cards),
        "project": project,
        "source_query": source_query,
        "tags": sorted(required_tags),
    }


def _load_bundle(path: Path) -> KarteBundle:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(text) or {}
    else:
        payload = json.loads(text)
    return KarteBundle.model_validate(payload)


def _render_card_markdown(card: KarteCard) -> str:
    title = card.title.strip()
    body = card.body.strip()
    lines = [f"# {title}", "", body]
    if card.source_uri:
        lines.extend(["", f"Source URI: {card.source_uri}"])
    if card.updated_at:
        lines.extend(["", f"Updated At: {card.updated_at}"])
    return "\n".join(line for line in lines if line is not None).strip() + "\n"


def _safe_stem(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._")
    return normalized or "karte-card"


def _normalize_tags(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for tag in tags:
        value = str(tag or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _format_chunk_body(heading_path: list[str], chunk_text: str) -> str:
    if heading_path:
        return f"{' > '.join(heading_path)}\n{chunk_text}".strip()
    return chunk_text.strip()
