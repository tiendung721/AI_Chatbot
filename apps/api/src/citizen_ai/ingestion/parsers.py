import csv
import io
import re
import subprocess
import tempfile
import unicodedata
import zipfile
from pathlib import Path
from typing import Any

from .formats import MIMES, text_decode, validate_file
from .models import Extraction, Limits, ParseFailure, Section


def ocr_image(image: Any, limits: Limits) -> tuple[str, float]:
    if image.width * image.height > limits.max_image_pixels:
        raise ParseFailure("IMAGE_PIXEL_LIMIT")
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "ocr.png"
        image.convert("RGB").save(target)
        try:
            result = subprocess.run(
                ["tesseract", str(target), "stdout", "-l", "vie+eng", "--psm", "6", "tsv"],
                capture_output=True,
                timeout=40,
                check=True,
            )
        except FileNotFoundError as exc:
            raise ParseFailure("OCR_UNAVAILABLE") from exc
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
            raise ParseFailure("OCR_FAILED") from exc
    lines: dict[tuple[str, ...], list[str]] = {}
    confidences = []
    for row in csv.DictReader(io.StringIO(result.stdout.decode("utf-8")), delimiter="\t"):
        word = (row.get("text") or "").strip()
        if not word:
            continue
        key = tuple(row.get(k, "") for k in ("page_num", "block_num", "par_num", "line_num"))
        lines.setdefault(key, []).append(word)
        confidence = float(row.get("conf", "-1"))
        if confidence >= 0:
            confidences.append(confidence)
    return "\n".join(" ".join(words) for words in lines.values()), sum(confidences) / len(
        confidences
    ) if confidences else 0.0


def pdf_sections(data: bytes, limits: Limits) -> Extraction:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ParseFailure("PDF_ENCRYPTED")
    count = len(reader.pages)
    if count > limits.max_pdf_pages:
        raise ParseFailure("PDF_PAGE_LIMIT")
    result = Extraction(sections=[], metadata={"pages_total": count, "pages_read": count, "ocr_pages": []})
    rendered = None
    try:
        for index, page in enumerate(reader.pages):
            warnings: list[str] = []
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
                warnings.append("pdf_text_extraction_failed")
            if len(text.strip()) < 15:
                import pypdfium2 as pdfium

                if rendered is None:
                    rendered = pdfium.PdfDocument(data)
                pdf_page = rendered[index]
                width, height = pdf_page.get_size()
                scale = min(2.5, (limits.max_image_pixels / max(1, width * height)) ** 0.5)
                bitmap = pdf_page.render(scale=scale)
                try:
                    text, confidence = ocr_image(bitmap.to_pil(), limits)
                finally:
                    bitmap.close()
                    pdf_page.close()
                warnings.append("ocr_review_required")
                if confidence < 70:
                    warnings.append("ocr_low_confidence")
                result.metadata["ocr_pages"].append(
                    {"page": index + 1, "mean_confidence": round(confidence, 1)}
                )
            if not text.strip():
                warnings.append("empty_section")
            result.sections.append(
                Section(
                    locator={"kind": "pdf_page", "page_start": index + 1, "page_end": index + 1},
                    text=text.strip(),
                    warnings=warnings,
                )
            )
            enforce_limits(result, limits)
    finally:
        if rendered is not None:
            rendered.close()
    return result


def docx_sections(data: bytes, limits: Limits) -> Extraction:
    from docx import Document
    from docx.table import Table

    document = Document(io.BytesIO(data))
    result = Extraction(sections=[], metadata={"kind": "docx", "pagination": "not_available"})
    heading = "Nội dung"
    paragraphs: list[str] = []

    def flush() -> None:
        if paragraphs:
            result.sections.append(
                Section(locator={"kind": "docx_section", "section": heading}, text="\n".join(paragraphs))
            )
            paragraphs.clear()
            enforce_limits(result, limits)

    table_index = 0
    for block in document.iter_inner_content():
        if isinstance(block, Table):
            flush()
            table_index += 1
            rows = [[cell.text for cell in row.cells] for row in block.rows]
            result.sections.append(
                Section(
                    locator={"kind": "docx_section", "section": heading, "table": table_index},
                    text=heading + "\n" + table_lines(rows),
                )
            )
        else:
            text = block.text.strip()
            if block.style and block.style.name and block.style.name.startswith("Heading"):
                flush()
                heading = text or heading
            if text:
                paragraphs.append(text)
        enforce_limits(result, limits)
    flush()
    seen = set()
    for index, section in enumerate(document.sections, 1):
        for kind in ("header", "footer"):
            part = getattr(section, kind)
            text = "\n".join(
                [p.text for p in part.paragraphs if p.text.strip()]
                + [table_lines([[c.text for c in r.cells] for r in t.rows]) for t in part.tables]
            )
            if text.strip() and (kind, text) not in seen:
                result.sections.append(
                    Section(locator={"kind": "docx_section", "section": f"{kind} {index}"}, text=text)
                )
                seen.add((kind, text))
    enforce_limits(result, limits)
    return result


def table_lines(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    headers = [value or f"Cột {i}" for i, value in enumerate(rows[0], 1)]
    return "\n".join(
        f"Dòng {i}: "
        + " | ".join(
            f"{headers[j] if j < len(headers) else f'Cột {j + 1}'}: {value}" for j, value in enumerate(row)
        )
        for i, row in enumerate(rows, 1)
    )


def xlsx_sections(data: bytes, limits: Limits) -> Extraction:
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter

    formulas = load_workbook(io.BytesIO(data), data_only=False, keep_links=False)
    cached = load_workbook(io.BytesIO(data), data_only=True, keep_links=False)
    result = Extraction(sections=[], metadata={"sheets": []})
    try:
        if (
            len(formulas.worksheets) > limits.max_sheets
            or sum(s.max_row for s in formulas.worksheets) > limits.max_rows
        ):
            raise ParseFailure("XLSX_WORKBOOK_LIMIT")
        for sheet in formulas.worksheets:
            if sheet.max_column > 1000 or sheet.max_column * sheet.max_row > 1_000_000:
                raise ParseFailure("XLSX_WORKBOOK_LIMIT")
            hidden = sheet.sheet_state != "visible"
            result.metadata["sheets"].append({"name": sheet.title, "hidden": hidden, "rows": sheet.max_row})
            merged = list(sheet.merged_cells.ranges)
            if len(merged) > 1000:
                raise ParseFailure("XLSX_WORKBOOK_LIMIT")
            first_rows = list(sheet.iter_rows(min_row=1, max_row=min(5, sheet.max_row)))
            header_cells: Any = max(
                first_rows, key=lambda cells: sum(c.value is not None for c in cells), default=[]
            )
            headers = {c.column: str(c.value) for c in header_cells if c.value is not None}
            prefix = f"Sheet: {sheet.title}\nCột: " + " | ".join(
                f"{get_column_letter(i)}={headers.get(i, '')}" for i in range(1, sheet.max_column + 1)
            )
            if merged:
                prefix += "\nVùng ô gộp: " + ", ".join(map(str, merged))
            for start in range(1, sheet.max_row + 1, 40):
                end = min(start + 39, sheet.max_row)
                lines, warnings = [], ["hidden_sheet_requires_selection"] if hidden else []
                for row in sheet.iter_rows(min_row=start, max_row=end):
                    values = []
                    for cell in row:
                        value = cell.value
                        if value is None:
                            for region in merged:
                                if cell.coordinate in region:
                                    value = sheet.cell(region.min_row, region.min_col).value
                                    break
                        if cell.data_type == "f":
                            value = cached[sheet.title][cell.coordinate].value
                            if value is None:
                                value = f"[Chưa có giá trị lưu; công thức: {cell.value}]"
                                warnings.append("formula_cache_missing:" + cell.coordinate)
                        if value is not None:
                            values.append(
                                f"{cell.coordinate} ({headers.get(cell.column, get_column_letter(cell.column))}): {value}"
                            )
                    if values:
                        lines.append(" | ".join(values))
                text = prefix + "\n" + "\n".join(lines) if lines else ""
                if not text:
                    warnings.append("empty_section")
                result.sections.append(
                    Section(
                        locator={
                            "kind": "xlsx_cells",
                            "sheet": sheet.title,
                            "cell_range": f"A{start}:{get_column_letter(sheet.max_column)}{end}",
                            "row_start": start,
                            "row_end": end,
                        },
                        text=text,
                        hidden=hidden,
                        warnings=warnings,
                    )
                )
                enforce_limits(result, limits)
    finally:
        formulas.close()
        cached.close()
    return result


def pptx_sections(data: bytes, limits: Limits) -> Extraction:
    from pptx import Presentation

    result = Extraction(sections=[])
    presentation = Presentation(io.BytesIO(data))

    def texts(shapes: Any) -> list[str]:
        output = []
        for shape in shapes:
            if getattr(shape, "has_text_frame", False):
                output.append(shape.text)
            if getattr(shape, "has_table", False):
                output.append(table_lines([[c.text for c in r.cells] for r in shape.table.rows]))
            if hasattr(shape, "shapes"):
                output.extend(texts(shape.shapes))
        return output

    if len(presentation.slides) > limits.max_pdf_pages:
        raise ParseFailure("SLIDE_LIMIT")
    for index, slide in enumerate(presentation.slides, 1):
        text = "\n".join(texts(slide.shapes)).strip()
        result.sections.append(
            Section(
                locator={"kind": "pptx_slide", "slide": index},
                text=text,
                warnings=[] if text else ["empty_section"],
            )
        )
        enforce_limits(result, limits)
    result.metadata = {"slides_total": len(presentation.slides), "slides_read": len(result.sections)}
    return result


def text_sections(data: bytes, extension: str, limits: Limits) -> Extraction:
    decoded, inferred = text_decode(data)
    result = Extraction(sections=[], warnings=["encoding_detected_requires_review"] if inferred else [])
    if extension == ".html":
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(decoded, "html.parser")
        for node in soup(["script", "style", "iframe", "object", "embed", "svg", "form", "nav"]):
            node.decompose()
        main = soup.find("main") or soup.find("article") or soup.body or soup
        decoded = main.get_text("\n", strip=True)
    if extension == ".csv":
        csv.field_size_limit(limits.max_text_bytes)
        try:
            dialect = csv.Sniffer().sniff(decoded[:8192], delimiters=",;\t|")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","
        reader = csv.reader(io.StringIO(decoded), delimiter=delimiter)
        rows = []
        headers: list[str] = []
        first = 1
        count = 0
        for count, row in enumerate(reader, 1):
            if count > limits.max_rows:
                raise ParseFailure("CSV_ROW_LIMIT")
            if not headers:
                headers = row
            rows.append(
                " | ".join(
                    f"{headers[i] if i < len(headers) else f'Cột {i + 1}'}: {v}" for i, v in enumerate(row)
                )
            )
            if len(rows) == 40:
                result.sections.append(
                    Section(
                        locator={"kind": "csv_rows", "row_start": first, "row_end": count},
                        text="\n".join(rows),
                    )
                )
                first = count + 1
                rows = []
                enforce_limits(result, limits)
        if rows:
            result.sections.append(
                Section(
                    locator={"kind": "csv_rows", "row_start": first, "row_end": count}, text="\n".join(rows)
                )
            )
        result.metadata = {"delimiter": delimiter, "rows_read": count}
    else:
        parts = re.split(r"(?m)(?=^#{1,6} )", decoded) if extension == ".md" else [decoded]
        for index, part in enumerate(parts, 1):
            if part.strip():
                heading = part.splitlines()[0].lstrip("# ")[:200] if extension == ".md" else f"Mục {index}"
                result.sections.append(
                    Section(locator={"kind": "text_section", "section": heading}, text=part.strip())
                )
    enforce_limits(result, limits)
    return result


def enforce_limits(result: Extraction, limits: Limits) -> None:
    if (
        len(result.sections) > limits.max_sections
        or sum(len(s.text.encode("utf-8")) for s in result.sections) > limits.max_text_bytes
    ):
        raise ParseFailure("EXTRACTION_OUTPUT_LIMIT")


def parse_file(data: bytes, extension: str, limits: Limits = Limits()) -> Extraction:
    validate_file("source" + extension, data, MIMES.get(extension), limits, deep=True)
    office_warnings = []
    if extension in {".docx", ".xlsx", ".pptx"}:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if any("_xmlsignatures/" in m.filename.replace("\\", "/").lower() for m in archive.infolist()):
                office_warnings.append("office_digital_signature_not_verified")
            if any("\\" in m.orig_filename for m in archive.infolist()):
                # Some signed Office packages use Windows separators. Normalize
                # only the parser's in-memory copy, never the stored original.
                canonical = io.BytesIO()
                with zipfile.ZipFile(
                    canonical, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1
                ) as output:
                    for member in archive.infolist():
                        output.writestr(member.filename.replace("\\", "/"), archive.read(member))
                data = canonical.getvalue()
                office_warnings.append("office_noncanonical_paths_normalized")
    try:
        if extension == ".pdf":
            result = pdf_sections(data, limits)
        elif extension == ".docx":
            result = docx_sections(data, limits)
        elif extension == ".xlsx":
            result = xlsx_sections(data, limits)
        elif extension == ".pptx":
            result = pptx_sections(data, limits)
        elif extension in {".png", ".jpg", ".jpeg"}:
            from PIL import Image

            with Image.open(io.BytesIO(data)) as image:
                text, confidence = ocr_image(image, limits)
            result = Extraction(
                sections=[
                    Section(
                        locator={"kind": "image_ocr", "section": "Ảnh 1"},
                        text=text,
                        warnings=["ocr_review_required"]
                        + (["ocr_low_confidence"] if confidence < 70 else []),
                    )
                ],
                metadata={"mean_confidence": round(confidence, 1)},
            )
        else:
            result = text_sections(data, extension, limits)
        enforce_limits(result, limits)
        result.warnings.extend(office_warnings)
        for section in result.sections:
            cleaned = "".join(c for c in section.text if ord(c) >= 32 or c in "\n\r\t")
            if cleaned != section.text:
                section.warnings.append("invalid_text_controls_removed")
            section.text = unicodedata.normalize("NFC", cleaned)
        enforce_limits(result, limits)
        if not any(s.text.strip() for s in result.sections):
            raise ParseFailure("EXTRACTION_EMPTY")
        return result
    except ParseFailure:
        raise
    except Exception as exc:
        raise ParseFailure("EXTRACTION_FAILED") from exc
