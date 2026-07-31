from __future__ import annotations

import json
from pathlib import Path

from .schemas import IndexedChunk


class JsonChunkStore:
    def __init__(self, path: Path, *, prune_missing_sources: bool = False) -> None:
        self._path = path
        self._prune_missing_sources = prune_missing_sources
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[IndexedChunk]:
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        chunks = [IndexedChunk.model_validate(item) for item in payload]
        if not self._prune_missing_sources:
            return chunks
        return [chunk for chunk in chunks if Path(chunk.source_path).is_file()]

    def save(self, chunks: list[IndexedChunk]) -> None:
        payload = [chunk.model_dump() for chunk in chunks]
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
