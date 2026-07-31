from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Section:
    heading_path: list[str]
    content: str


def split_markdown_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    heading_stack: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        content = "\n".join(buffer).strip()
        if content:
            sections.append(Section(heading_path=heading_stack.copy(), content=content))
        buffer.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if 1 <= level <= 6 and stripped[level:level + 1] == " ":
                flush()
                heading = stripped[level + 1 :].strip()
                heading_stack[:] = heading_stack[: level - 1]
                heading_stack.append(heading)
                continue
        buffer.append(line)

    flush()
    if not sections and text.strip():
        sections.append(Section(heading_path=[], content=text.strip()))
    return sections


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    length = len(normalized)

    while start < length:
        end = min(length, start + chunk_size)
        chunks.append(normalized[start:end].strip())
        if end >= length:
            break
        start = max(end - overlap, start + 1)

    return [chunk for chunk in chunks if chunk]

