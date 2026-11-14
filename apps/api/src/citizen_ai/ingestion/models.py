from dataclasses import dataclass
from datetime import date
from typing import Any, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from ..schemas import StrictModel


@dataclass(frozen=True)
class Limits:
    max_file_bytes: int = 25 * 1024 * 1024
    max_uncompressed_bytes: int = 100 * 1024 * 1024
    max_text_bytes: int = 8 * 1024 * 1024
    max_pdf_pages: int = 300
    max_image_pixels: int = 25_000_000
    max_sheets: int = 100
    max_rows: int = 100_000
    max_sections: int = 10000


class ParseFailure(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class Section(StrictModel):
    locator: dict[str, Any]
    text: str
    warnings: list[str] = Field(default_factory=list)
    hidden: bool = False


class Extraction(StrictModel):
    sections: list[Section]
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SectionEdit(StrictModel):
    section_id: UUID
    text: str = Field(max_length=1_000_000)


class ExtractionReview(StrictModel):
    revision: int = Field(ge=1)
    selected_section_ids: list[UUID] = Field(min_length=1, max_length=10000)
    edits: list[SectionEdit] = Field(default_factory=list, max_length=10000)
    acknowledge_warnings: bool


class FileMetadata(StrictModel):
    revision: int = Field(ge=0)
    document_number: str | None = Field(default=None, max_length=120)
    issuer: str | None = Field(default=None, max_length=300)
    issued_on: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    source_url: str | None = Field(default=None, max_length=2048)
    source_collected_on: date | None = None
    jurisdiction: Literal["national", "current_tenant"] = "current_tenant"
    classification: Literal["public", "internal", "restricted"] = "public"
    topic_tags: list[str] = Field(default_factory=list, max_length=20)
    supersedes_version_id: UUID | None = None
    allow_public_download: bool = False

    @field_validator("document_number", "issuer", "source_url", mode="before")
    @classmethod
    def empty_is_unknown(cls, value: Any) -> Any:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("source_url")
    @classmethod
    def safe_source_url(cls, value: str | None) -> str | None:
        if value is not None:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"https", "http"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or any(ord(c) < 32 for c in value)
            ):
                raise ValueError("Source must be an HTTP(S) URL without credentials")
        return value

    @field_validator("topic_tags")
    @classmethod
    def bounded_tags(cls, values: list[str]) -> list[str]:
        tags = list(dict.fromkeys(t.strip() for t in values))
        if any(not t or len(t) > 80 for t in tags):
            raise ValueError("Tags require 1–80 characters")
        return tags

    @model_validator(mode="after")
    def valid_dates(self) -> "FileMetadata":
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Invalid effective date range")
        return self


class UploadResult(StrictModel):
    filename: str
    document_id: UUID | None = None
    version_id: UUID | None = None
    job_id: UUID | None = None
    state: str
    error_code: str | None = None


class UploadBatch(StrictModel):
    items: list[UploadResult]
    client_request_id: UUID | None = None
