import hashlib
import logging
from pathlib import PurePosixPath
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..common import AppError, canonical, chunk_text, new_id, normalize
from ..config import settings
from ..content import audit
from ..db import many, one, run, transaction
from ..storage import get_private, mark_clean, put_private
from .formats import MIMES, validate_file
from .models import Extraction, ExtractionReview, Limits, ParseFailure
from .scanner import scan_bytes


def document_lock(db: Session, document_id: str, *, exclusive: bool = False) -> dict[str, Any]:
    row = one(
        db,
        "SELECT * FROM documents WHERE id=:id" + (" FOR UPDATE" if exclusive else " FOR SHARE"),
        id=document_id,
    )
    if not row or row["revoked_at"] or row["purged_at"]:
        raise AppError("SOURCE_REVOKED", "Tài liệu đã bị thu hồi hoặc xóa.", 409)
    return row


def enqueue(db: Session, tenant_id: str, kind: str, target_id: str) -> None:
    run(
        db,
        "INSERT INTO knowledge_outbox(id,tenant_id,kind,target_id) VALUES(:id,:t,:kind,:target) ON CONFLICT(tenant_id,kind,target_id) DO UPDATE SET last_dispatched_at=NULL",
        id=new_id(),
        t=tenant_id,
        kind=kind,
        target=target_id,
    )


def register_batch(tenant_id: str, actor_id: str, request_id: str, payload_hash: str) -> None:
    with transaction(tenant_id) as db:
        run(
            db,
            "INSERT INTO upload_batches(tenant_id,request_id,actor_id,payload_hash) VALUES(:t,:id,:a,:hash) ON CONFLICT DO NOTHING",
            t=tenant_id,
            id=request_id,
            a=actor_id,
            hash=payload_hash,
        )
        row = one(db, "SELECT actor_id,payload_hash FROM upload_batches WHERE request_id=:id", id=request_id)
        if not row or row["payload_hash"] != payload_hash or str(row["actor_id"]) != actor_id:
            raise AppError("VERSION_CONFLICT", "Mã upload đã được dùng với nội dung khác.", 409)


def upload_one(
    tenant_id: str,
    actor_id: str,
    filename: str,
    data: bytes,
    mime: str | None,
    document_id: str | None = None,
    *,
    batch_id: str | None = None,
    operation_id: str | None = None,
) -> dict[str, Any]:
    extension = validate_file(
        filename, data, mime, Limits(max_file_bytes=settings().max_upload_mb * 1024 * 1024)
    )
    digest = hashlib.sha256(data).hexdigest()
    doc_id, version_id, job_id = document_id or new_id(), new_id(), new_id()
    key = f"tenant/{tenant_id}/documents/{version_id}/original{extension}"
    stored = False
    try:
        with transaction(tenant_id) as db:
            # Shared with orphan cleanup; its delete decision cannot race an upload commit.
            run(db, "SELECT pg_advisory_xact_lock(hashtextextended(:scope,0))", scope="storage:" + tenant_id)
            if operation_id:
                run(
                    db,
                    "INSERT INTO upload_receipts(tenant_id,operation_id,batch_id,payload_hash) VALUES(:t,:op,:batch,:hash) ON CONFLICT DO NOTHING",
                    t=tenant_id,
                    op=operation_id,
                    batch=batch_id,
                    hash=digest,
                )
                receipt = one(
                    db, "SELECT * FROM upload_receipts WHERE operation_id=:op FOR UPDATE", op=operation_id
                )
                if not receipt or receipt["payload_hash"] != digest:
                    raise AppError("VERSION_CONFLICT", "Nội dung upload không khớp mã yêu cầu.", 409)
                if receipt["result_json"] is not None:
                    return dict(receipt["result_json"])
            if document_id:
                document_lock(db, document_id, exclusive=True)
                number = one(
                    db,
                    "SELECT COALESCE(max(number),0)+1 AS n FROM document_versions WHERE document_id=:id",
                    id=document_id,
                )
            else:
                run(
                    db,
                    "INSERT INTO documents(id,tenant_id,title) VALUES(:id,:t,:title)",
                    id=doc_id,
                    t=tenant_id,
                    title=filename[:200],
                )
                number = {"n": 1}
            try:
                put_private(key, data, MIMES[extension])
                stored = True
            except Exception as exc:
                raise AppError(
                    "STORAGE_UNAVAILABLE", "Kho file chưa sẵn sàng. Chưa nhận tài liệu.", 503, True
                ) from exc
            run(
                db,
                "INSERT INTO document_versions(id,tenant_id,document_id,number,body,sha256,parse_status,object_key,original_filename,mime_type,byte_size,scan_status) VALUES(:id,:t,:doc,:n,'',:sha,'uploaded',:key,:filename,:mime,:size,'pending')",
                id=version_id,
                t=tenant_id,
                doc=doc_id,
                n=number["n"] if number else 1,
                sha=digest,
                key=key,
                filename=filename,
                mime=MIMES[extension],
                size=len(data),
            )
            run(
                db,
                "INSERT INTO ingestion_jobs(id,tenant_id,version_id,created_by) VALUES(:id,:t,:v,:a)",
                id=job_id,
                t=tenant_id,
                v=version_id,
                a=actor_id,
            )
            enqueue(db, tenant_id, "ingestion", job_id)
            result = {
                "filename": filename,
                "document_id": doc_id,
                "version_id": version_id,
                "job_id": job_id,
                "state": "uploaded",
            }
            if operation_id:
                run(
                    db,
                    "UPDATE upload_receipts SET result_json=CAST(:result AS jsonb) WHERE operation_id=:op",
                    result=canonical(result),
                    op=operation_id,
                )
            audit(
                db,
                tenant_id,
                actor_id,
                "knowledge.file_uploaded",
                doc_id,
                {"version_id": version_id, "job_id": job_id},
            )
        return result
    except Exception:
        if stored:
            # A connection failure during COMMIT has an unknown outcome. Do not delete
            # here: the object may belong to a committed version. The sweeper rechecks.
            logging.getLogger("citizen_ai").warning("upload_commit_unknown version_id=%s", version_id)
        raise


def section_chunks(body: str, locator: dict[str, Any]) -> list[str]:
    kind = locator.get("kind")
    if not body.strip():
        return []
    if kind not in {"xlsx_cells", "csv_rows"}:
        return chunk_text(body)
    lines = body.splitlines()
    if kind == "xlsx_cells":
        context = []
        while lines and lines[0].startswith(("Sheet:", "Cột:", "Vùng ô gộp:")):
            context.append(lines.pop(0))
        prefix = "\n".join(context) + f"\nPhạm vi: {locator['cell_range']}\n"
    else:
        prefix = f"CSV · Dòng {locator['row_start']}–{locator['row_end']}\n"
    # Never split a table row or drop column labels/context to satisfy a token cap.
    if len(prefix) > 1000:
        raise ParseFailure("TABLE_CONTEXT_LIMIT")
    chunks: list[str] = []
    current = prefix
    for line in lines:
        if len(prefix) + len(line) + 1 > 3000:
            raise ParseFailure("TABLE_ROW_LIMIT")
        if len(current) + len(line) + 1 > 3000:
            chunks.append(current.rstrip())
            current = prefix
        current += line + "\n"
    if current != prefix:
        chunks.append(current.rstrip())
    return chunks


def index_sections(db: Session, tenant_id: str, version_id: str, title: str) -> None:
    if one(db, "SELECT 1 AS published FROM release_documents WHERE document_version_id=:v", v=version_id):
        raise AppError(
            "VERSION_CONFLICT", "Phiên bản đã xuất bản không thể bị ghi đè. Hãy tạo phiên bản mới.", 409
        )
    sections = many(
        db, "SELECT * FROM document_sections WHERE version_id=:v AND selected ORDER BY ordinal", v=version_id
    )
    if not any((s["review_text"] if s["review_text"] is not None else s["body"]).strip() for s in sections):
        raise AppError("EXTRACTION_EMPTY", "Chưa chọn phần nội dung có thể lập chỉ mục.", 409)
    run(db, "DELETE FROM knowledge_chunks WHERE version_id=:v", v=version_id)
    ordinal = 0
    combined = []
    for section in sections:
        body = section["review_text"] if section["review_text"] is not None else section["body"]
        combined.append(body)
        for chunk in section_chunks(body, section["locator"]):
            ordinal += 1
            run(
                db,
                "INSERT INTO knowledge_chunks(id,tenant_id,version_id,ordinal,body,normalized_text,section_id,locator) VALUES(:id,:t,:v,:n,:body,:normalized,:s,CAST(:locator AS jsonb))",
                id=new_id(),
                t=tenant_id,
                v=version_id,
                n=ordinal,
                body=chunk,
                normalized=normalize(title + " " + chunk),
                s=section["id"],
                locator=canonical(section["locator"]),
            )
    run(
        db,
        "UPDATE document_versions SET body=:body,parse_status='ready' WHERE id=:v AND purged_at IS NULL",
        body="\n\n".join(combined),
        v=version_id,
    )
    run(
        db,
        "UPDATE ingestion_jobs SET state='ready',progress=100,lease_until=NULL,updated_at=now() WHERE version_id=:v",
        v=version_id,
    )


def process_ingestion(tenant_id: str, job_id: str) -> None:
    claim = new_id()
    scan_confirmed = False
    document_id: str | None = None
    try:
        with transaction(tenant_id) as db:
            ref = one(
                db,
                "SELECT v.document_id FROM ingestion_jobs j JOIN document_versions v ON (v.tenant_id,v.id)=(j.tenant_id,j.version_id) WHERE j.id=:id",
                id=job_id,
            )
            if not ref:
                return
            document_id = str(ref["document_id"])
            doc = document_lock(db, document_id)
            job = one(
                db,
                "SELECT j.*,v.object_key,v.original_filename FROM ingestion_jobs j JOIN document_versions v ON (v.tenant_id,v.id)=(j.tenant_id,j.version_id) WHERE j.id=:id FOR UPDATE OF j",
                id=job_id,
            )
            if not job or job["state"] not in {"uploaded", "scanning", "extracting", "indexing"}:
                return
            if one(db, "SELECT 1 AS busy FROM ingestion_jobs WHERE id=:id AND lease_until>now()", id=job_id):
                return
            run(
                db,
                "UPDATE ingestion_jobs SET state='scanning',progress=10,attempts=attempts+1,claim_id=:claim,lease_until=now()+interval '6 minutes',updated_at=now(),error_code=NULL WHERE id=:id",
                claim=claim,
                id=job_id,
            )
            run(
                db,
                "UPDATE document_versions SET parse_status='scanning',scan_status='pending' WHERE id=:v",
                v=job["version_id"],
            )
        data = get_private(job["object_key"])
        scan_bytes(data)
        scan_confirmed = True
        mark_clean(job["object_key"])
        with transaction(tenant_id) as db:
            document_lock(db, document_id)
            current = one(db, "SELECT claim_id FROM ingestion_jobs WHERE id=:id FOR UPDATE", id=job_id)
            if not current or str(current["claim_id"]) != claim:
                return
            run(
                db,
                "UPDATE ingestion_jobs SET state='extracting',progress=35,updated_at=now() WHERE id=:id",
                id=job_id,
            )
            run(
                db,
                "UPDATE document_versions SET parse_status='extracting',scan_status='clean' WHERE id=:v",
                v=job["version_id"],
            )
        extension = PurePosixPath(job["original_filename"]).suffix.lower()
        try:
            with httpx.Client(timeout=settings().extraction_timeout_seconds + 15, trust_env=False) as client:
                response = client.post(
                    settings().parser_url.rstrip("/") + "/extract",
                    content=data,
                    headers={"X-File-Extension": extension, "Content-Type": "application/octet-stream"},
                )
            packet = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AppError(
                "PARSER_UNAVAILABLE", "Dịch vụ trích xuất chưa sẵn sàng. Có thể thử lại job.", 503, True
            ) from exc
        if response.status_code != 200:
            raise ParseFailure(packet.get("error_code", "EXTRACTION_FAILED"))
        extraction = Extraction.model_validate(packet)
        if (
            len(extraction.sections) > Limits().max_sections
            or sum(len(s.text.encode()) for s in extraction.sections) > Limits().max_text_bytes
        ):
            raise ParseFailure("EXTRACTION_OUTPUT_LIMIT")
        with transaction(tenant_id) as db:
            doc = document_lock(db, document_id)
            current = one(db, "SELECT claim_id FROM ingestion_jobs WHERE id=:id FOR UPDATE", id=job_id)
            if not current or str(current["claim_id"]) != claim:
                return
            if one(
                db,
                "SELECT 1 AS published FROM release_documents WHERE document_version_id=:v",
                v=job["version_id"],
            ):
                raise AppError("VERSION_CONFLICT", "Không ghi đè bản đã xuất bản.", 409)
            run(db, "DELETE FROM document_sections WHERE version_id=:v", v=job["version_id"])
            warnings = list(extraction.warnings)
            for ordinal, section in enumerate(extraction.sections, 1):
                warnings.extend(section.warnings)
                run(
                    db,
                    "INSERT INTO document_sections(id,tenant_id,version_id,ordinal,locator,body,warnings,hidden,selected) VALUES(:id,:t,:v,:n,CAST(:locator AS jsonb),:body,CAST(:warnings AS jsonb),:hidden,:selected)",
                    id=new_id(),
                    t=tenant_id,
                    v=job["version_id"],
                    n=ordinal,
                    locator=canonical(section.locator),
                    body=section.text,
                    warnings=canonical(section.warnings),
                    hidden=section.hidden,
                    selected=not section.hidden,
                )
            metadata = {
                **extraction.metadata,
                "warnings": list(dict.fromkeys(warnings)),
                "sections_total": len(extraction.sections),
            }
            state = "needs_review" if warnings else "indexing"
            run(
                db,
                "UPDATE document_versions SET metadata_json=CAST(:metadata AS jsonb),extraction_revision=extraction_revision+1,parse_status=:state WHERE id=:v",
                metadata=canonical(metadata),
                state=state,
                v=job["version_id"],
            )
            run(
                db,
                "UPDATE ingestion_jobs SET state=:state,progress=80,lease_until=NULL,updated_at=now() WHERE id=:id",
                state=state,
                id=job_id,
            )
            if state == "indexing":
                index_sections(db, tenant_id, str(job["version_id"]), doc["title"])
                state = "ready"
            audit(
                db,
                tenant_id,
                str(job["created_by"]),
                "knowledge.extracted",
                document_id,
                {"version_id": str(job["version_id"]), "state": state},
            )
    except Exception as exc:
        code = exc.code if isinstance(exc, (AppError, ParseFailure)) else "EXTRACTION_FAILED"
        logging.getLogger("citizen_ai").warning(
            "ingestion_failed job_id=%s code=%s type=%s", job_id, code, type(exc).__name__
        )
        with transaction(tenant_id) as db:
            if document_id:
                failed_doc = one(db, "SELECT * FROM documents WHERE id=:id FOR SHARE", id=document_id)
            else:
                failed_doc = None
            job = one(db, "SELECT * FROM ingestion_jobs WHERE id=:id FOR UPDATE", id=job_id)
            if not job or (job["claim_id"] is not None and str(job["claim_id"]) != claim):
                return
            state = (
                "cancelled"
                if not failed_doc or failed_doc["revoked_at"] or failed_doc["purged_at"]
                else "quarantined"
                if code == "FILE_QUARANTINED"
                else "failed"
            )
            run(
                db,
                "UPDATE ingestion_jobs SET state=:state,error_code=:code,lease_until=NULL,updated_at=now() WHERE id=:id",
                state=state,
                code=code,
                id=job_id,
            )
            if state != "cancelled":
                scan_state = "infected" if state == "quarantined" else "clean" if scan_confirmed else "error"
                run(
                    db,
                    "UPDATE document_versions SET parse_status=:state,scan_status=:scan WHERE id=:v AND purged_at IS NULL",
                    state=state,
                    scan=scan_state,
                    v=job["version_id"],
                )


def review_extraction(
    db: Session, tenant_id: str, actor_id: str, version_id: str, payload: ExtractionReview
) -> None:
    version = one(db, "SELECT * FROM document_versions WHERE id=:v", v=version_id)
    if not version:
        raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy phiên bản tài liệu.", 404)
    doc = document_lock(db, str(version["document_id"]), exclusive=True)
    version = one(db, "SELECT * FROM document_versions WHERE id=:v FOR UPDATE", v=version_id)
    assert version
    if (
        version["parse_status"] not in {"needs_review", "ready"}
        or version["scan_status"] not in {"clean", "not_required"}
        or version["extraction_revision"] != payload.revision
        or one(db, "SELECT 1 AS published FROM release_documents WHERE document_version_id=:v", v=version_id)
    ):
        raise AppError("VERSION_CONFLICT", "Trích xuất đã thay đổi hoặc không ở trạng thái chờ duyệt.", 409)
    sections = many(db, "SELECT * FROM document_sections WHERE version_id=:v", v=version_id)
    allowed = {str(s["id"]) for s in sections}
    selected = {str(s) for s in payload.selected_section_ids}
    edits = {str(e.section_id): e.text for e in payload.edits}
    if (
        not payload.acknowledge_warnings
        or len(selected) != len(payload.selected_section_ids)
        or not selected.issubset(allowed)
        or not set(edits).issubset(selected)
        or len(edits) != len(payload.edits)
    ):
        raise AppError(
            "VALIDATION_ERROR", "Cần xác nhận cảnh báo và chọn các phần hợp lệ của đúng phiên bản.", 422
        )
    total = sum(
        len(edits.get(str(s["id"]), s["body"]).encode()) for s in sections if str(s["id"]) in selected
    )
    if total > Limits().max_text_bytes:
        raise AppError("EXTRACTION_OUTPUT_LIMIT", "Nội dung duyệt vượt giới hạn.", 422)
    for section in sections:
        section_id = str(section["id"])
        run(
            db,
            "UPDATE document_sections SET selected=:selected,review_text=:body WHERE id=:id",
            id=section_id,
            selected=section_id in selected,
            body=edits.get(section_id),
        )
    run(
        db,
        "INSERT INTO extraction_reviews(id,tenant_id,version_id,revision,actor_id,review_json) VALUES(:id,:t,:v,:revision,:a,CAST(:review AS jsonb))",
        id=new_id(),
        t=tenant_id,
        v=version_id,
        revision=payload.revision,
        a=actor_id,
        review=canonical(payload.model_dump(mode="json")),
    )
    index_sections(db, tenant_id, version_id, doc["title"])
    run(
        db,
        "UPDATE document_versions SET extraction_revision=extraction_revision+1,approved_for_public=false,approved_by=NULL,approved_at=NULL,updated_at=now() WHERE id=:v",
        v=version_id,
    )
    audit(
        db,
        tenant_id,
        actor_id,
        "knowledge.extraction_reviewed",
        str(version["document_id"]),
        {"version_id": version_id, "selected_sections": len(selected)},
    )
