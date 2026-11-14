from typing import Any

from sqlalchemy.orm import Session

from .common import AppError, canonical, chunk_text, fingerprint, new_id, normalize
from .config import settings
from .db import many, one, run
from .schemas import AssistantConfig, KnowledgeText


def audit(
    db: Session,
    tenant_id: str,
    actor_id: str | None,
    kind: str,
    resource_id: str,
    detail: dict[str, Any] | None = None,
) -> None:
    run(
        db,
        "INSERT INTO audit_events(id,tenant_id,actor_id,event_type,resource_id,detail) VALUES(:id,:t,:actor,:kind,:r,CAST(:detail AS jsonb))",
        id=new_id(),
        t=tenant_id,
        actor=actor_id,
        kind=kind,
        r=resource_id,
        detail=canonical(detail or {}),
    )


def assistant(db: Session, *, lock: bool = False) -> dict[str, Any]:
    row = one(db, "SELECT * FROM assistants" + (" FOR UPDATE" if lock else ""))
    if not row:
        raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy trợ lý.", 404)
    return row


def draft(db: Session) -> dict[str, Any]:
    row = one(db, "SELECT * FROM assistant_drafts")
    if not row:
        raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy bản nháp.", 404)
    return row


def require_revision(db: Session, etag: str | None) -> dict[str, Any]:
    row = draft(db)
    if etag != f'"{row["revision"]}"':
        raise AppError("VERSION_CONFLICT", "Bản nháp đã thay đổi. Hãy tải lại trước khi lưu.", 412)
    return row


def check_versions(db: Session, config: dict[str, Any], *, public: bool) -> list[dict[str, Any]]:
    ids = config.get("knowledge_version_ids", [])
    if not ids:
        raise AppError("KNOWLEDGE_NOT_READY", "Cần chọn ít nhất một tài liệu để kiểm tra và xuất bản.", 409)
    rows = many(
        db,
        "SELECT v.*,d.revoked_at,d.title FROM document_versions v JOIN documents d ON (d.tenant_id,d.id)=(v.tenant_id,v.document_id) WHERE v.id = ANY(CAST(:ids AS uuid[])) AND v.parse_status='ready' AND v.scan_status IN ('clean','not_required') AND d.revoked_at IS NULL AND d.purged_at IS NULL AND (v.effective_from IS NULL OR v.effective_from <= CURRENT_DATE) AND (v.effective_to IS NULL OR v.effective_to >= CURRENT_DATE) ORDER BY d.id,v.id FOR SHARE OF d,v",
        ids=ids,
    )
    if len(rows) != len(ids) or (public and any(not r["approved_for_public"] for r in rows)):
        raise AppError(
            "KNOWLEDGE_NOT_READY",
            "Tài liệu chưa sẵn sàng, chưa xác nhận công khai, đã thu hồi hoặc ngoài hiệu lực.",
            409,
        )
    if settings().embedding_provider != "disabled":
        from .ai.embeddings import require_profile

        require_profile(db)
        missing = one(
            db,
            "SELECT count(*) AS n FROM knowledge_chunks c WHERE c.version_id=ANY(CAST(:ids AS uuid[])) AND NOT EXISTS(SELECT 1 FROM chunk_embeddings e WHERE (e.tenant_id,e.chunk_id)=(c.tenant_id,c.id) AND e.embedding_profile_id=CAST(:profile AS uuid))",
            ids=ids,
            profile=settings().embedding_profile_id,
        )
        if missing and missing["n"]:
            raise AppError(
                "KNOWLEDGE_NOT_READY", "Developer cần reindex tài liệu theo profile vector hiện hành.", 409
            )
    return rows


def create_text(
    db: Session, tenant_id: str, actor_id: str, payload: KnowledgeText, *, document_id: str | None = None
) -> dict[str, Any]:
    doc_id, version_id = document_id or new_id(), new_id()
    if document_id:
        doc = one(db, "SELECT * FROM documents WHERE id=:id FOR UPDATE", id=document_id)
        if not doc or doc["revoked_at"]:
            raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy tài liệu có thể cập nhật.", 404)
        version = one(
            db,
            "SELECT COALESCE(max(number),0)+1 AS n FROM document_versions WHERE document_id=:id",
            id=doc_id,
        )
        number = version["n"] if version else 1
    else:
        run(
            db,
            "INSERT INTO documents(id,tenant_id,title) VALUES(:id,:t,:title)",
            id=doc_id,
            t=tenant_id,
            title=payload.title,
        )
        number = 1
    run(
        db,
        "INSERT INTO document_versions(id,tenant_id,document_id,number,body,sha256,parse_status,effective_from,effective_to) VALUES(:id,:t,:doc,:n,:body,:sha,'ready',:ef,:et)",
        id=version_id,
        t=tenant_id,
        doc=doc_id,
        n=number,
        body=payload.body,
        sha=fingerprint(payload.body),
        ef=payload.effective_from,
        et=payload.effective_to,
    )
    for ordinal, body in enumerate(chunk_text(payload.body), start=1):
        run(
            db,
            "INSERT INTO knowledge_chunks(id,tenant_id,version_id,ordinal,body,normalized_text) VALUES(:id,:t,:v,:n,:body,:normalized)",
            id=new_id(),
            t=tenant_id,
            v=version_id,
            n=ordinal,
            body=body,
            normalized=normalize(payload.title + " " + body),
        )
    audit(db, tenant_id, actor_id, "knowledge.text_created", doc_id, {"version_id": version_id})
    return {
        "document_id": doc_id,
        "version_id": version_id,
        "parse_status": "ready",
        "approved_for_public": False,
    }


def publish_snapshot(
    db: Session, tenant_id: str, actor_id: str, config: dict[str, Any], reason: str
) -> dict[str, Any]:
    a = assistant(db, lock=True)
    checked = AssistantConfig.model_validate(config).model_dump(mode="json")
    check_versions(db, checked, public=True)
    sequence = one(
        db, "SELECT COALESCE(max(sequence),0)+1 AS n FROM content_releases WHERE assistant_id=:id", id=a["id"]
    )
    release_id = new_id()
    run(
        db,
        "INSERT INTO content_releases(id,tenant_id,assistant_id,sequence,snapshot,content_hash,runtime_fingerprint,created_by,reason) VALUES(:id,:t,:a,:seq,CAST(:snapshot AS jsonb),:hash,:runtime,:actor,:reason)",
        id=release_id,
        t=tenant_id,
        a=a["id"],
        seq=sequence["n"] if sequence else 1,
        snapshot=canonical(checked),
        hash=fingerprint(checked),
        runtime=settings().runtime_fingerprint,
        actor=actor_id,
        reason=reason,
    )
    for version_id in checked["knowledge_version_ids"]:
        run(
            db,
            "INSERT INTO release_documents(tenant_id,release_id,document_version_id) VALUES(:t,:r,:v)",
            t=tenant_id,
            r=release_id,
            v=version_id,
        )
    run(db, "UPDATE assistants SET active_release_id=:r WHERE id=:a", r=release_id, a=a["id"])
    audit(db, tenant_id, actor_id, "release.published", release_id, {"content_hash": fingerprint(checked)})
    return {
        "id": release_id,
        "sequence": sequence["n"] if sequence else 1,
        "content_hash": fingerprint(checked),
    }
