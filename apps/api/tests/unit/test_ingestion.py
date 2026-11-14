import io
import math
import shutil
import socket
import zipfile
from types import SimpleNamespace

import pytest

from citizen_ai.ai import embeddings
from citizen_ai.common import AppError
from citizen_ai.config import settings
from citizen_ai.ingestion.formats import validate_file
from citizen_ai.ingestion.models import Extraction, Limits, ParseFailure
from citizen_ai.ingestion.parser_app import isolated_extract
from citizen_ai.ingestion.parsers import parse_file
from citizen_ai.ingestion.pipeline import section_chunks
from citizen_ai.ingestion.scanner import scan_bytes
from tests.fixture_files import file_fixture


@pytest.mark.parametrize("extension", [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".csv", ".html"])
def test_real_formats_preserve_text_and_locators(extension: str) -> None:
    result = parse_file(file_fixture(extension), extension)
    assert "SEN-XANH-482" in "\n".join(s.text for s in result.sections)
    assert all(s.locator.get("kind") for s in result.sections)
    if extension == ".pdf":
        assert [s.locator["page_start"] for s in result.sections] == [1, 2]
        assert "MAI-VANG-739" in result.sections[1].text
    if extension == ".docx":
        assert all("page_start" not in s.locator for s in result.sections)
        assert "MAI-739" in "\n".join(s.text for s in result.sections)
    if extension == ".xlsx":
        assert any(s.hidden and s.locator["sheet"] == "Nội bộ" for s in result.sections)
        assert any("formula_cache_missing:C2" in s.warnings for s in result.sections)
        assert any("A1:C3" == s.locator["cell_range"] for s in result.sections)
        assert "Ô gộp minh họa" in result.sections[0].text
    if extension == ".pptx":
        assert [s.locator["slide"] for s in result.sections] == [1, 2]
    if extension == ".html":
        assert "STEAL_SECRET" not in result.sections[0].text
        assert "MENU" not in result.sections[0].text


@pytest.mark.parametrize("extension", [".scan.pdf", ".png", ".jpg"])
@pytest.mark.skipif(not shutil.which("tesseract"), reason="OCR is verified in the Docker test image")
def test_real_vietnamese_ocr_requires_review(extension: str) -> None:
    result = Extraction.model_validate(
        isolated_extract(file_fixture(extension), ".pdf" if extension == ".scan.pdf" else extension, Limits())
    )
    assert "SEN-XANH-482" in "\n".join(s.text for s in result.sections)
    assert "ocr_review_required" in result.sections[0].warnings
    assert "Phường" in result.sections[0].text


def test_office_windows_member_paths_and_collision_are_handled_safely() -> None:
    source = file_fixture(".docx")
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source)) as original, zipfile.ZipFile(output, "w") as target:
        for member in original.infolist():
            target.writestr(member.filename.replace("/", "\\"), original.read(member))
    result = parse_file(output.getvalue(), ".docx")
    assert "SEN-XANH-482" in "\n".join(s.text for s in result.sections)
    assert "office_noncanonical_paths_normalized" in result.warnings
    malicious = io.BytesIO(source)
    with zipfile.ZipFile(malicious, "a") as archive:
        archive.writestr("word\\document.xml", "duplicate normalized path")
    with pytest.raises(ParseFailure, match="FILE_ARCHIVE_UNSAFE"):
        parse_file(malicious.getvalue(), ".docx")


def test_parser_cleans_database_invalid_controls_with_review_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    from citizen_ai.ingestion import parsers

    monkeypatch.setattr(
        parsers,
        "docx_sections",
        lambda *args: Extraction(
            sections=[{"locator": {"kind": "docx_section"}, "text": "Co\u0302ng\x00 khai\x01"}]
        ),
    )
    result = parse_file(file_fixture(".docx"), ".docx")
    assert result.sections[0].text == "Công khai"
    assert "invalid_text_controls_removed" in result.sections[0].warnings


def test_parser_subprocess_and_limits() -> None:
    result = isolated_extract(file_fixture(".txt"), ".txt", Limits())
    assert result["sections"][0]["text"].endswith("SEN-XANH-482.")
    assert isolated_extract(file_fixture(".pdf"), ".pdf", Limits(max_pdf_pages=1)) == {
        "error_code": "PDF_PAGE_LIMIT"
    }
    with pytest.raises(ParseFailure, match="EXTRACTION_OUTPUT_LIMIT"):
        parse_file(b"x" * 100, ".txt", Limits(max_text_bytes=20))


def test_upload_magic_archive_xml_and_size_fail_closed() -> None:
    for name, data, mime, code in [
        ("a.pdf", b"notpdf", "application/pdf", "FILE_MIME_MISMATCH"),
        ("a.exe", b"test", None, "FILE_UNSUPPORTED"),
        ("a.txt", b"a\x00b", None, "FILE_MIME_MISMATCH"),
        ("a.txt", b"ok", "image/png", "FILE_MIME_MISMATCH"),
    ]:
        with pytest.raises(ParseFailure, match=code):
            validate_file(name, data, mime)
    with pytest.raises(ParseFailure, match="FILE_TOO_LARGE"):
        validate_file("a.txt", b"large", None, Limits(max_file_bytes=2))
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"x" * 2_000_000)
    with pytest.raises(ParseFailure, match="FILE_ARCHIVE_LIMIT"):
        validate_file("bomb.docx", output.getvalue(), None)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "word/document.xml", '<!DOCTYPE a [<!ENTITY leak SYSTEM "file:///etc/passwd">]><a>&leak;</a>'
        )
    with pytest.raises(ParseFailure, match="FILE_ARCHIVE_UNSAFE"):
        parse_file(output.getvalue(), ".docx")


def test_scanner_unavailable_is_not_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(*args, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr(socket, "create_connection", unavailable)
    with pytest.raises(AppError, match="SCANNER_UNAVAILABLE"):
        scan_bytes(b"anything")


def test_table_chunks_repeat_context_and_preserve_whole_rows() -> None:
    body = "Sheet: Công khai\nCột: A=Tên | B=Mã\n" + "\n".join(
        f"A{i} (Tên): {'sen ' * 80}|B{i} (Mã): ID-{i}" for i in range(1, 41)
    )
    chunks = section_chunks(body, {"kind": "xlsx_cells", "cell_range": "A1:B40"})
    assert len(chunks) > 1 and all(len(c) <= 3000 for c in chunks)
    assert all(c.startswith("Sheet: Công khai\nCột: A=Tên | B=Mã\nPhạm vi: A1:B40\n") for c in chunks)
    for i in range(1, 41):
        assert sum(f"B{i} (Mã): ID-{i}" in c for c in chunks) == 1
    with pytest.raises(ParseFailure, match="TABLE_ROW_LIMIT"):
        section_chunks("A: " + "x" * 4000, {"kind": "csv_rows", "row_start": 1, "row_end": 1})


def test_embedding_contract_dimensions_and_provider_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = settings().model_copy(
        update={
            "embedding_provider": "openai",
            "openai_embedding_model": "developer-selected",
            "embedding_dimensions": 3,
        }
    )
    monkeypatch.setattr(embeddings, "settings", lambda: cfg)
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[1.0, 0.0, 0.0])])

    sdk = SimpleNamespace(embeddings=SimpleNamespace(create=create))
    assert embeddings.embed(["source"], client=sdk) == [[1.0, 0.0, 0.0]]
    assert calls[0]["model"] == "developer-selected" and calls[0]["dimensions"] == 3
    for vector in [[0.0, 0.0, 0.0], [1.0, 2.0], [math.nan, 0.0, 1.0]]:
        with pytest.raises(AppError, match="EMBEDDING_PROFILE_MISMATCH"):
            embeddings.validate_vectors([vector], 1, 3)
