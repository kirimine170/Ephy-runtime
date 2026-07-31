from __future__ import annotations

import csv
import json
from pathlib import Path
from html.parser import HTMLParser
from xml.etree import ElementTree
from zipfile import ZipFile


def load_document_sections(file_path: Path) -> list[tuple[list[str], str]]:
    suffix = file_path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        from .chunker import split_markdown_sections

        sections = split_markdown_sections(file_path.read_text(encoding="utf-8"))
        return [(section.heading_path, section.content) for section in sections]

    if suffix == ".pdf":
        return _load_pdf_sections(file_path)

    if suffix == ".docx":
        text = _load_docx_text(file_path)
        return [([], text)] if text.strip() else []

    if suffix in {".html", ".htm"}:
        text = _load_html_text(file_path)
        return [([], text)] if text.strip() else []

    if suffix in {".csv", ".tsv"}:
        sections = _load_delimited_sections(file_path, delimiter="\t" if suffix == ".tsv" else ",")
        return [(heading_path, text) for heading_path, text in sections if text.strip()]

    if suffix == ".json":
        text = _load_json_text(file_path)
        return [([], text)] if text.strip() else []

    text = file_path.read_text(encoding="utf-8")
    return [([], text.strip())] if text.strip() else []


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self._parts.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self._parts)


def _load_pdf_text(file_path: Path) -> str:
    return "\n\n".join(text for _, text in _load_pdf_sections(file_path))


def _load_pdf_sections(file_path: Path) -> list[tuple[list[str], str]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF ingest requires `pypdf` to be available in the Python environment") from exc

    try:
        reader = PdfReader(str(file_path))
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception as exc:
                raise ValueError(f"PDF is encrypted and cannot be read: {file_path}") from exc

        sections: list[tuple[list[str], str]] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                sections.append(([f"Page {page_number}"], text))
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"PDF text extraction failed for {file_path}: {exc}") from exc

    if not sections:
        raise ValueError(
            f"PDF contains no extractable text: {file_path}. "
            "Scanned PDFs require OCR, which is not enabled."
        )
    return sections


def _load_docx_text(file_path: Path) -> str:
    try:
        with ZipFile(file_path) as archive:
            xml_bytes = archive.read("word/document.xml")
    except KeyError as exc:
        raise ValueError("DOCX ingest could not find word/document.xml") from exc

    root = ElementTree.fromstring(xml_bytes)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        joined = "".join(texts).strip()
        if joined:
            paragraphs.append(joined)
    return "\n\n".join(paragraphs)


def _load_html_text(file_path: Path) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(file_path.read_text(encoding="utf-8"))
    parser.close()
    return parser.get_text()


def _load_delimited_sections(file_path: Path, delimiter: str) -> list[tuple[list[str], str]]:
    with file_path.open("r", encoding="utf-8", newline="") as file_obj:
        reader = csv.reader(file_obj, delimiter=delimiter)
        rows = list(reader)

    if not rows:
        return []

    header = rows[0]
    data_rows = rows[1:] if header else rows
    sections: list[tuple[list[str], str]] = []
    for index, row in enumerate(data_rows, start=1):
        values = row if header else row[:]
        if header:
            pairs = [f"{column}: {value}" for column, value in zip(header, values) if value.strip()]
        else:
            pairs = [value.strip() for value in values if value.strip()]
        text = "\n".join(pairs).strip()
        if text:
            sections.append(([f"row {index}"], text))
    return sections


def _load_json_text(file_path: Path) -> str:
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    return json.dumps(payload, ensure_ascii=False, indent=2)
