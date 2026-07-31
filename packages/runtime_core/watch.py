from __future__ import annotations

import time
from pathlib import Path

from packages.rag_core.schemas import IngestRequest
from packages.rag_core.service import RagService


def run_watch_loop(
    rag_service: RagService,
    paths: list[str],
    project: str | None,
    recursive: bool,
    tags: list[str],
    interval_seconds: float,
    max_cycles: int | None = None,
) -> list[dict]:
    target_paths = [Path(path).resolve() for path in paths]
    snapshots = _build_snapshot(target_paths, recursive=recursive)
    events: list[dict] = []

    initial = rag_service.ingest(
        IngestRequest(
            paths=[str(path) for path in target_paths],
            project=project,
            recursive=recursive,
            tags=tags,
        )
    )
    events.append({"event": "initial_ingest", "result": initial})

    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        cycles += 1
        time.sleep(interval_seconds)
        current = _build_snapshot(target_paths, recursive=recursive)
        if current != snapshots:
            result = rag_service.ingest(
                IngestRequest(
                    paths=[str(path) for path in target_paths],
                    project=project,
                    recursive=recursive,
                    tags=tags,
                )
            )
            events.append({"event": "reingest", "result": result})
            snapshots = current
        else:
            events.append({"event": "noop"})

    return events


def _build_snapshot(paths: list[Path], recursive: bool) -> dict[str, tuple[float, int]]:
    snapshot: dict[str, tuple[float, int]] = {}
    for path in paths:
        for file_path in _iter_supported_files(path, recursive=recursive):
            stat = file_path.stat()
            snapshot[str(file_path)] = (stat.st_mtime, stat.st_size)
    return snapshot


def _iter_supported_files(path: Path, recursive: bool) -> list[Path]:
    supported = {".md", ".markdown", ".txt", ".pdf", ".docx"}
    if path.is_file():
        return [path] if path.suffix.lower() in supported else []
    pattern = "**/*" if recursive else "*"
    return [candidate for candidate in path.glob(pattern) if candidate.is_file() and candidate.suffix.lower() in supported]
