"""Tenant-scoped document management; never fetch metadata URLs."""

import difflib
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .common import AppError, canonical
from .content import audit
from .db import many, one, run
from .ingestion.models import FileMetadata
from .ingestion.pipeline import document_lock


def catalog(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    q: str = "",
    status: str | None = None,
    approved: bool | None = None,
    file_type: str | None = None,
    effectivity: str | None = None,
) -> dict[str, Any]:
    clauses = ["true"]
    params: dict[str, Any] = {"limit": page_size, "offset": (page - 1) * page_size}
    if q:
        params["q"] = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        clauses.append(
            "(d.title ILIKE :q OR v.metadata_json->>'document_number' ILIKE :q OR v.metadata_json->>'topic_tags' ILIKE :q)"
        )
    if status == "revoked":
        clauses.append("d.revoked_at IS NOT NULL AND d.purged_at IS NULL")
    elif status == "purged":
        clauses.append("d.purged_at IS NOT NULL")
    elif status:
        clauses.append("v.parse_status=:status AND d.revoked_at IS NULL AND d.purged_at IS NULL")
        params["status"] = status
    if approved is not None:
        clauses.append("v.approved_for_public=:approved")
        params["approved"] = approved
    if file_type == "text":
        clauses.append("v.original_filename IS NULL AND v.purged_at IS NULL")
    elif file_type:
        clauses.append("lower(v.original_filename) LIKE :extension")
        params["extension"] = "%." + file_type
    if effectivity == "active":
        clauses.append(
            "(v.effective_from IS NULL OR v.effective_from<=CURRENT_DATE) AND (v.effective_to IS NULL OR v.effective_to>=CURRENT_DATE)"
        )
    elif effectivity == "future":
        clauses.append("v.effective_from>CURRENT_DATE")
    elif effectivity == "expired":
        clauses.append("v.effective_to<CURRENT_DATE")
    elif effectivity == "unknown":
        clauses.append("v.effective_from IS NULL AND v.effective_to IS NULL")
    source = " FROM documents d JOIN document_versions v ON (v.tenant_id,v.document_id)=(d.tenant_id,d.id) "
    where = " WHERE " + " AND ".join(clauses)
    total = one(db, "SELECT count(*) AS n" + source + where, **params)
    items = many(
        db,
        "SELECT d.id,d.title,d.revoked_at,d.purged_at,v.id AS version_id,v.number,v.approved_for_public,v.parse_status,v.scan_status,v.original_filename,v.byte_size,v.metadata_json,v.effective_from,v.effective_to,v.created_at,v.updated_at,j.id AS job_id,j.progress,j.error_code"
        + source
        + " LEFT JOIN ingestion_jobs j ON (j.tenant_id,j.version_id)=(v.tenant_id,v.id)"
        + where
        + " ORDER BY v.updated_at DESC,v.id DESC LIMIT :limit OFFSET :offset",
        **params,
    )
    count = int(total["n"]) if total else 0
    return {
        "items": items,
        "total": count,
        "page": page,
        "page_size": page_size,
        "next_cursor": str(page + 1) if page * page_size < count else None,
    }


def update_metadata(
    db: Session, tenant_id: str, actor_id: str, version_id: UUID, payload: FileMetadata
) -> dict[str, int]:
    ref = one(db, "SELECT document_id FROM document_versions WHERE id=:id", id=version_id)
    if not ref:
        raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy phiên bản.", 404)
    document_lock(db, str(ref["document_id"]), exclusive=True)
    row = one(db, "SELECT * FROM document_versions WHERE id=:id FOR UPDATE", id=version_id)
    assert row
    if (
        row["parse_status"] not in {"ready", "needs_review"}
        or row["extraction_revision"] != payload.revision
        or one(
            db, "SELECT 1 AS published FROM release_documents WHERE document_version_id=:id", id=version_id
        )
    ):
        raise AppError(
            "VERSION_CONFLICT",
            "Phiên bản đang xử lý, đã thay đổi hoặc đã xuất bản. Hãy tạo phiên bản mới.",
            409,
        )
    previous = payload.supersedes_version_id
    if previous:
        old = one(
            db,
            "SELECT id FROM document_versions WHERE id=:id AND document_id=:doc AND number<:number AND purged_at IS NULL",
            id=previous,
            doc=row["document_id"],
            number=row["number"],
        )
        if not old:
            raise AppError(
                "VALIDATION_ERROR", "Bản được thay thế phải là phiên bản trước của cùng tài liệu.", 422
            )
    values = payload.model_dump(
        mode="json", exclude={"revision", "effective_from", "effective_to", "supersedes_version_id"}
    )
    run(
        db,
        "UPDATE document_versions SET metadata_json=metadata_json || CAST(:metadata AS jsonb),effective_from=:ef,effective_to=:et,supersedes_version_id=:previous,extraction_revision=extraction_revision+1,approved_for_public=false,approved_by=NULL,approved_at=NULL,updated_at=now() WHERE id=:id",
        id=version_id,
        metadata=canonical(values),
        ef=payload.effective_from,
        et=payload.effective_to,
        previous=previous,
    )
    audit(db, tenant_id, actor_id, "knowledge.metadata_updated", str(version_id))
    return {"revision": payload.revision + 1}


def version_diff(db: Session, version_id: UUID, against: UUID) -> dict[str, Any]:
    current = one(db, "SELECT * FROM document_versions WHERE id=:id AND purged_at IS NULL", id=version_id)
    if not current:
        raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy phiên bản.", 404)
    other = one(
        db,
        "SELECT * FROM document_versions WHERE id=:id AND document_id=:doc AND purged_at IS NULL",
        id=against,
        doc=current["document_id"],
    )
    if not other:
        raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy phiên bản cùng tài liệu để so sánh.", 404)

    def body(row: dict[str, Any]) -> str:
        sections = many(
            db,
            "SELECT body,review_text,selected FROM document_sections WHERE version_id=:id ORDER BY ordinal",
            id=row["id"],
        )
        return (
            "\n\n".join(
                s["review_text"] if s["review_text"] is not None else s["body"]
                for s in sections
                if s["selected"]
            )
            if sections
            else row["body"]
        )

    # Bound the diff before constructing SequenceMatcher for hostile/large documents.
    before, after = body(other), body(current)
    maximum = 100_000
    before_lines, after_lines = before[:maximum].splitlines()[:2000], after[:maximum].splitlines()[:2000]
    lines = list(
        difflib.unified_diff(
            before_lines, after_lines, fromfile=f"V{other['number']}", tofile=f"V{current['number']}", n=3
        )
    )
    changed = {
        k: {"before": other["metadata_json"].get(k), "after": current["metadata_json"].get(k)}
        for k in set(other["metadata_json"]) | set(current["metadata_json"])
        if other["metadata_json"].get(k) != current["metadata_json"].get(k)
    }
    for k in ("effective_from", "effective_to", "supersedes_version_id"):
        if other[k] != current[k]:
            changed[k] = {"before": other[k], "after": current[k]}
    return {
        "version_id": version_id,
        "against": against,
        "diff": "\n".join(lines)[:200_000],
        "metadata_changes": changed,
        "truncated": len(before) > maximum
        or len(after) > maximum
        or len(before.splitlines()) > 2000
        or len(after.splitlines()) > 2000
        or sum(map(len, lines)) > 200_000,
    }
