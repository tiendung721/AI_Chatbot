import io
import struct
import unicodedata
import zipfile
from pathlib import PurePosixPath

from charset_normalizer import from_bytes
from defusedxml import ElementTree

from .models import Limits, ParseFailure

MIMES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".html": "text/html",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def text_decode(data: bytes) -> tuple[str, bool]:
    if b"\x00" in data and not data.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise ParseFailure("FILE_MIME_MISMATCH")
    try:
        decoded = data.decode("utf-8-sig")
        inferred = False
    except UnicodeDecodeError:
        candidate = from_bytes(data).best()
        if candidate is None or candidate.chaos > 0.1:
            raise ParseFailure("FILE_ENCODING_UNSUPPORTED") from None
        decoded, inferred = str(candidate), True
    if sum(ord(c) < 32 and c not in "\n\r\t" for c in decoded) > max(2, len(decoded) // 100):
        raise ParseFailure("FILE_MIME_MISMATCH")
    return unicodedata.normalize("NFC", decoded).replace("\x00", ""), inferred


def office_preflight(data: bytes, extension: str, limits: Limits, *, validate_xml: bool = True) -> None:
    expected = {".docx": "word/document.xml", ".xlsx": "xl/workbook.xml", ".pptx": "ppt/presentation.xml"}
    try:
        # Bound central-directory allocation before ZipFile constructs ZipInfo objects.
        end = data.rfind(b"PK\x05\x06", max(0, len(data) - 65557))
        if end < 0 or len(data) - end < 22:
            raise ParseFailure("FILE_ARCHIVE_UNSAFE")
        record = struct.unpack_from("<4s4H2LH", data, end)
        if record[1] or record[2] or record[3] != record[4] or end + 22 + record[7] != len(data):
            raise ParseFailure("FILE_ARCHIVE_UNSAFE")
        if record[4] > 10000 or record[5] > 4 * 1024 * 1024:
            raise ParseFailure("FILE_ARCHIVE_LIMIT")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > 10000 or sum(m.file_size for m in members) > limits.max_uncompressed_bytes:
                raise ParseFailure("FILE_ARCHIVE_LIMIT")
            names = [m.filename.replace("\\", "/") for m in members]
            if len(names) != len(set(names)):
                raise ParseFailure("FILE_ARCHIVE_UNSAFE")
            if expected[extension] not in names:
                raise ParseFailure("FILE_MIME_MISMATCH")
            for member in members:
                path = PurePosixPath(member.filename.replace("\\", "/"))
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or member.flag_bits & 1
                    or "\x00" in member.orig_filename
                ):
                    raise ParseFailure("FILE_ARCHIVE_UNSAFE")
                if "vbaproject" in member.filename.lower() or "macros" in member.filename.lower():
                    raise ParseFailure("FILE_MACRO_UNSUPPORTED")
                if member.file_size > limits.max_uncompressed_bytes or (
                    member.file_size > 1024 * 1024 and member.file_size > max(1, member.compress_size) * 250
                ):
                    raise ParseFailure("FILE_ARCHIVE_LIMIT")
                if validate_xml and member.filename.endswith((".xml", ".rels")):
                    ElementTree.fromstring(archive.read(member))
    except ParseFailure:
        raise
    except Exception as exc:
        raise ParseFailure("FILE_ARCHIVE_UNSAFE") from exc


def validate_file(
    filename: str, data: bytes, claimed_mime: str | None, limits: Limits = Limits(), *, deep: bool = False
) -> str:
    extension = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    if extension not in MIMES:
        raise ParseFailure("FILE_UNSUPPORTED")
    if not data:
        raise ParseFailure("FILE_EMPTY")
    if len(data) > limits.max_file_bytes:
        raise ParseFailure("FILE_TOO_LARGE")
    magic = {
        ".pdf": b"%PDF-",
        ".png": b"\x89PNG\r\n\x1a\n",
        ".jpg": b"\xff\xd8\xff",
        ".jpeg": b"\xff\xd8\xff",
    }
    if extension in magic and not data.startswith(magic[extension]):
        raise ParseFailure("FILE_MIME_MISMATCH")
    if extension in {".docx", ".xlsx", ".pptx"}:
        office_preflight(data, extension, limits, validate_xml=deep)
    elif extension in {".txt", ".md", ".csv", ".html"}:
        text_decode(data)
    allowed = {MIMES[extension], "application/octet-stream", ""}
    if extension in {".md", ".csv"}:
        allowed.add("text/plain")
    if (claimed_mime or "").split(";", 1)[0].lower() not in allowed:
        raise ParseFailure("FILE_MIME_MISMATCH")
    return extension
