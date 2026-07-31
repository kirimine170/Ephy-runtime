import builtins
import sys
import types

import pytest

from packages.rag_core.loaders import _load_pdf_text


def test_load_pdf_text_requires_pypdf(monkeypatch, tmp_path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pypdf":
            raise ImportError("missing pypdf")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ValueError, match="PDF ingest requires `pypdf`"):
        _load_pdf_text(pdf_path)


def test_load_pdf_text_uses_pypdf_when_available(monkeypatch, tmp_path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class FakeReader:
        def __init__(self, path: str) -> None:
            assert path == str(pdf_path)
            self.pages = [FakePage("Employee roster"), FakePage("Confirmed in meeting")]

    fake_module = types.SimpleNamespace(PdfReader=FakeReader)
    monkeypatch.setitem(sys.modules, "pypdf", fake_module)

    assert _load_pdf_text(pdf_path) == "Employee roster\n\nConfirmed in meeting"
