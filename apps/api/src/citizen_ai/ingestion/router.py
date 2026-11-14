import hashlib
import io
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid5

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from ..auth import admin_context, rate_limit
from ..common import AppError, fingerprint, new_id
from ..config import settings
from ..content import audit
from ..db import many, one, run, transaction
from ..knowledge import update_metadata, version_diff
from ..schemas import Reason
from ..storage import get_private
from .models import ExtractionReview, FileMetadata, ParseFailure, UploadBatch, UploadResult
from .pipeline import document_lock, enqueue, register_batch, review_extraction, upload_one

router = APIRouter(prefix="/api/v1/admin/knowledge", tags=["Knowledge files"])


@router.post("/uploads", response_model=UploadBatch, status_code=202)
async def uploads(request: Request) -> UploadBatch:
    admin = admin_context(request)
    rate_limit("upload:" + admin.tenant_id, 20)
    cfg = settings()
    items = []
    async with request.form(
        max_files=cfg.max_upload_files_per_batch, max_fields=3, max_part_size=cfg.max_upload_mb * 1024 * 1024
    ) as form:
        if set(form.keys()) - {"files", "document_id", "client_request_id"}:
            raise AppError("VALIDATION_ERROR", "Upload chứa trường không được phép.", 422)
        files = form.getlist("files")
        try:
            document_id = str(UUID(str(form["document_id"]))) if form.get("document_id") else None
            request_id = (
                str(UUID(str(form["client_request_id"]))) if form.get("client_request_id") else new_id()
            )
        except ValueError as exc:
            raise AppError("VALIDATION_ERROR", "Mã tài liệu hoặc mã upload không hợp lệ.", 422) from exc
        if not files or len(files) > cfg.max_upload_files_per_batch or (document_id and len(files) != 1):
            raise AppError(
                "VALIDATION_ERROR", "Chọn tối đa 10 file; cập nhật phiên bản chỉ nhận một file.", 422
            )
        prepared: list[tuple[str, UploadFile, str]] = []
        for file in files:
            if not isinstance(file, UploadFile):
                raise AppError("VALIDATION_ERROR", "Dữ liệu upload không hợp lệ.", 422)
            filename = PurePosixPath((file.filename or "").replace("\\", "/")).name[:240]
            data = await file.read(cfg.max_upload_mb * 1024 * 1024 + 1)
            prepared.append((filename, file, hashlib.sha256(data).hexdigest()))
            await file.seek(0)
        manifest = {
            "document_id": document_id,
            "files": [
                {"name": name, "mime": file.content_type, "size": file.size, "sha256": digest}
                for name, file, digest in prepared
            ],
        }
        await run_in_threadpool(
            register_batch, admin.tenant_id, admin.account_id, request_id, fingerprint(manifest)
        )
        for index, (filename, file, _) in enumerate(prepared):
            data = await file.read(cfg.max_upload_mb * 1024 * 1024 + 1)
            try:
                operation_id = str(uuid5(UUID(request_id), str(index)))
                value = await run_in_threadpool(
                    upload_one,
                    admin.tenant_id,
                    admin.account_id,
                    filename,
                    data,
                    file.content_type,
                    document_id,
                    batch_id=request_id,
                    operation_id=operation_id,
                )
                items.append(UploadResult.model_validate(value))
            except (AppError, ParseFailure) as exc:
                if isinstance(exc, AppError) and exc.code == "VERSION_CONFLICT":
                    raise
                items.append(UploadResult(filename=filename, state="rejected", error_code=exc.code))
    return UploadBatch(items=items, client_request_id=UUID(request_id))


@router.get("/jobs/{job_id}")
def job(job_id: UUID, request: Request) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        row = one(
            db,
            "SELECT id,version_id,state,progress,error_code,attempts,updated_at FROM ingestion_jobs WHERE id=:id",
            id=job_id,
        )
    if not row:
        raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy job xử lý.", 404)
    return row


@router.post("/jobs/{job_id}/retry")
def retry(job_id: UUID, request: Request) -> dict[str, str]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        ref = one(
            db,
            "SELECT v.document_id FROM ingestion_jobs j JOIN document_versions v ON (v.tenant_id,v.id)=(j.tenant_id,j.version_id) WHERE j.id=:id",
            id=job_id,
        )
        if not ref:
            raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy job.", 404)
        document_lock(db, str(ref["document_id"]))
        row = one(
            db,
            "SELECT j.*,d.revoked_at,d.purged_at FROM ingestion_jobs j JOIN document_versions v ON (v.tenant_id,v.id)=(j.tenant_id,j.version_id) JOIN documents d ON (d.tenant_id,d.id)=(v.tenant_id,v.document_id) WHERE j.id=:id FOR UPDATE OF j",
            id=job_id,
        )
        if not row:
            raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy job.", 404)
        if row["state"] != "failed" or row["revoked_at"] or row["purged_at"]:
            raise AppError(
                "VERSION_CONFLICT",
                "Chỉ thử lại job lỗi của tài liệu chưa thu hồi; file cách ly không được bỏ qua kiểm soát.",
                409,
            )
        run(
            db,
            "UPDATE ingestion_jobs SET state='uploaded',progress=0,claim_id=NULL,lease_until=NULL,error_code=NULL,updated_at=now() WHERE id=:id",
            id=job_id,
        )
        run(
            db,
            "UPDATE document_versions SET parse_status='uploaded',scan_status='pending' WHERE id=:v",
            v=row["version_id"],
        )
        enqueue(db, admin.tenant_id, "ingestion", str(job_id))
        audit(db, admin.tenant_id, admin.account_id, "knowledge.retry_requested", str(job_id))
    return {"state": "uploaded"}


@router.get("/versions/{version_id}")
def version(version_id: UUID, request: Request) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        row = one(
            db,
            "SELECT v.id,v.document_id,v.number,v.body,v.sha256,v.parse_status,v.scan_status,v.original_filename,v.mime_type,v.byte_size,v.extraction_revision,v.metadata_json,v.approved_for_public,v.approved_at,v.supersedes_version_id,v.effective_from,v.effective_to,v.updated_at,v.purged_at,d.title,d.revoked_at,EXISTS(SELECT 1 FROM release_documents rd WHERE rd.document_version_id=v.id) AS published FROM document_versions v JOIN documents d ON (d.tenant_id,d.id)=(v.tenant_id,v.document_id) WHERE v.id=:id",
            id=version_id,
        )
        if not row:
            raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy phiên bản tài liệu.", 404)
        row["sections"] = many(
            db,
            "SELECT id,ordinal,locator,body,review_text,warnings,hidden,selected FROM document_sections WHERE version_id=:id ORDER BY ordinal",
            id=version_id,
        )
    return row


@router.patch("/versions/{version_id}/metadata")
def metadata(version_id: UUID, payload: FileMetadata, request: Request) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        return update_metadata(db, admin.tenant_id, admin.account_id, version_id, payload)


@router.get("/versions/{version_id}/diff")
def diff(version_id: UUID, against: UUID, request: Request) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        return version_diff(db, version_id, against)


@router.post("/versions/{version_id}/review")
def review(version_id: UUID, payload: ExtractionReview, request: Request) -> dict[str, str]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        review_extraction(db, admin.tenant_id, admin.account_id, str(version_id), payload)
    return {"state": "ready"}


@router.get("/versions/{version_id}/original")
def original(version_id: UUID, request: Request) -> StreamingResponse:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        row = one(
            db,
            "SELECT v.object_key,v.original_filename,v.mime_type FROM document_versions v JOIN documents d ON (d.tenant_id,d.id)=(v.tenant_id,v.document_id) WHERE v.id=:id AND v.scan_status='clean' AND v.purged_at IS NULL AND d.revoked_at IS NULL AND v.object_key IS NOT NULL",
            id=version_id,
        )
    if not row:
        raise AppError(
            "RESOURCE_NOT_FOUND",
            "File chưa được quét sạch, đã thu hồi hoặc không thuộc phạm vi truy cập.",
            404,
        )
    data = get_private(row["object_key"])
    return StreamingResponse(
        io.BytesIO(data),
        media_type=row["mime_type"],
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''" + quote(row["original_filename"]),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/documents/{document_id}/delete-request", status_code=202)
def request_delete(document_id: UUID, payload: Reason, request: Request) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        doc = one(db, "SELECT * FROM documents WHERE id=:id FOR UPDATE", id=document_id)
        if not doc:
            raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy tài liệu.", 404)
        existing = one(db, "SELECT * FROM deletion_jobs WHERE document_id=:id", id=document_id)
        if existing and existing["state"] == "completed":
            return {"job_id": existing["id"], "state": "completed"}
        run(db, "UPDATE documents SET revoked_at=COALESCE(revoked_at,now()) WHERE id=:id", id=document_id)
        run(db, "UPDATE tenants SET security_epoch=security_epoch+1")
        job_id = str(existing["id"]) if existing else new_id()
        if not existing:
            run(
                db,
                "INSERT INTO deletion_jobs(id,tenant_id,document_id,created_by) VALUES(:id,:t,:doc,:a)",
                id=job_id,
                t=admin.tenant_id,
                doc=document_id,
                a=admin.account_id,
            )
        elif existing["state"] == "failed":
            run(
                db,
                "UPDATE deletion_jobs SET state='queued',claim_id=NULL,lease_until=NULL,error_code=NULL WHERE id=:id",
                id=job_id,
            )
        enqueue(db, admin.tenant_id, "purge", job_id)
        audit(
            db,
            admin.tenant_id,
            admin.account_id,
            "knowledge.purge_requested",
            str(document_id),
            {"reason": payload.reason, "job_id": job_id},
        )
    return {"job_id": job_id, "state": "queued"}


@router.get("/deletions/{job_id}")
def deletion(job_id: UUID, request: Request) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        row = one(
            db,
            "SELECT id,document_id,state,error_code,created_at,completed_at FROM deletion_jobs WHERE id=:id",
            id=job_id,
        )
    if not row:
        raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy yêu cầu xóa.", 404)
    return row
