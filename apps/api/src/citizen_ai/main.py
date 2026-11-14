import asyncio
import logging
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal
from uuid import UUID

from fastapi import FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.exc import IntegrityError

from .auth import (
    COOKIE_NAME,
    DUMMY_HASH,
    admin_context,
    bearer_context,
    passwords,
    rate_limit,
    redis_client,
    require_origin,
    verify_password,
)
from .chat import event, owned_turn, turn_view
from .common import AppError, canonical, digest, fingerprint, new_id
from .config import settings
from .content import assistant, audit, check_versions, create_text, draft, publish_snapshot, require_revision
from .db import many, one, run, transaction
from .ingestion.router import router as knowledge_router
from .knowledge import catalog
from .schemas import (
    AdminAssistantView,
    Approval,
    AssistantConfig,
    FeedbackInput,
    KnowledgeText,
    Login,
    PasswordChange,
    Publish,
    Reason,
    SessionView,
    TurnInput,
    TurnView,
)


def check_runtime() -> None:
    with transaction() as db:
        role = one(db, "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user")
        unsafe = one(
            db,
            "SELECT count(*) AS n FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND c.relname NOT IN ('alembic_version','embedding_profiles') AND (NOT c.relrowsecurity OR NOT c.relforcerowsecurity OR pg_get_userbyid(c.relowner)=current_user)",
        )
        if not role or role["rolsuper"] or role["rolbypassrls"] or not unsafe or unsafe["n"]:
            raise RuntimeError("Unsafe database role or missing tenant RLS")
        if not one(
            db, "SELECT 1 AS ok FROM pg_tables WHERE schemaname='public' AND tablename='ingestion_jobs'"
        ):
            raise RuntimeError("Database migration is not ready")
    redis_client().ping()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings()
    check_runtime()
    yield


app = FastAPI(
    title="AI Cổng thông tin đa phường",
    version="0.1.0",
    lifespan=lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)
app.include_router(knowledge_router)


@app.middleware("http")
async def envelope(request: Request, call_next: Any) -> Response:
    request.state.request_id = new_id()
    content_length = request.headers.get("content-length", "0")
    if not content_length.isdecimal():
        return await app_error(request, AppError("VALIDATION_ERROR", "Độ dài yêu cầu không hợp lệ.", 422))
    limit = (
        settings().max_upload_mb * settings().max_upload_files_per_batch * 1024 * 1024 + 1048576
        if request.url.path == "/api/v1/admin/knowledge/uploads"
        else 512000
    )
    if int(content_length) > limit:
        return JSONResponse(
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Yêu cầu vượt giới hạn dung lượng.",
                    "request_id": request.state.request_id,
                    "retryable": False,
                }
            },
            status_code=413,
        )
    receive = request._receive
    received = 0

    async def bounded_receive() -> Any:
        nonlocal received
        message = await receive()
        received += len(message.get("body", b""))
        if received > limit:
            raise AppError("FILE_TOO_LARGE", "Yêu cầu vượt giới hạn dung lượng.", 413)
        return message

    request._receive = bounded_receive
    try:
        response = await call_next(request)
    except Exception as exc:
        logging.getLogger("citizen_ai").error(
            "request_failed request_id=%s type=%s", request.state.request_id, type(exc).__name__
        )
        response = await app_error(
            request,
            AppError("INTERNAL_ERROR", "Hệ thống chưa thể xử lý yêu cầu. Vui lòng thử lại sau.", 500, True),
        )
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(AppError)
async def app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        {
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request.state.request_id,
                "retryable": exc.retryable,
            }
        },
        status_code=exc.status,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return await app_error(
        request,
        AppError("VALIDATION_ERROR", "Dữ liệu không đúng định dạng hoặc chứa trường không được phép.", 422),
    )


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    return await app_error(
        request, AppError("VERSION_CONFLICT", "Dữ liệu vừa thay đổi hoặc xung đột. Vui lòng tải lại.", 409)
    )


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return await app_error(
        request,
        AppError("INTERNAL_ERROR", "Hệ thống chưa thể xử lý yêu cầu. Vui lòng thử lại sau.", 500, True),
    )


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    check_runtime()
    return {"status": "ready"}


@app.post("/api/v1/auth/admin/login")
def login(payload: Login, request: Request, response: Response) -> dict[str, Any]:
    require_origin(request)
    rate_limit("login-ip:" + (request.client.host if request.client else "unknown"), 30, 900)
    rate_limit("login-account:" + payload.email.lower(), 10, 900)
    with transaction() as db:
        account = one(db, "SELECT * FROM resolve_login(:email)", email=payload.email.lower())
    ok = verify_password(account["password_hash"] if account else DUMMY_HASH, payload.password)
    if not account or not ok:
        raise AppError("AUTH_REQUIRED", "Thông tin đăng nhập không hợp lệ.", 401)
    token, session_id = secrets.token_urlsafe(40), new_id()
    csrf = digest("csrf:" + token)
    with transaction(str(account["tenant_id"])) as db:
        run(
            db,
            "INSERT INTO admin_sessions(id,tenant_id,account_id,token_hash,csrf_hash,expires_at) VALUES(:id,:t,:a,:token,:csrf,now()+interval '8 hours')",
            id=session_id,
            t=account["tenant_id"],
            a=account["account_id"],
            token=digest(token),
            csrf=digest(csrf),
        )
        profile = one(db, "SELECT must_change_password FROM accounts WHERE id=:id", id=account["account_id"])
        audit(db, str(account["tenant_id"]), str(account["account_id"]), "admin.login", session_id)
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=settings().cookie_secure,
        samesite="lax",
        max_age=28800,
        path="/",
    )
    return {"csrf_token": csrf, "must_change_password": profile["must_change_password"] if profile else True}


@app.get("/api/v1/auth/me")
def me(request: Request) -> dict[str, Any]:
    admin = admin_context(request, allow_password_change=True)
    with transaction(admin.tenant_id) as db:
        profile = one(db, "SELECT email,must_change_password FROM accounts WHERE id=:id", id=admin.account_id)
    return {
        "role": "tenant_admin",
        "csrf_token": digest("csrf:" + request.cookies[COOKIE_NAME]),
        **(profile or {}),
    }


@app.post("/api/v1/auth/admin/change-password")
def change_password(payload: PasswordChange, request: Request) -> dict[str, bool]:
    admin = admin_context(request, allow_password_change=True)
    with transaction(admin.tenant_id) as db:
        account = one(db, "SELECT password_hash FROM accounts WHERE id=:id FOR UPDATE", id=admin.account_id)
        if not account or not verify_password(account["password_hash"], payload.current_password):
            raise AppError("AUTH_REQUIRED", "Mật khẩu hiện tại không đúng.", 401)
        run(
            db,
            "UPDATE accounts SET password_hash=:pw,must_change_password=false WHERE id=:id",
            id=admin.account_id,
            pw=passwords.hash(payload.new_password),
        )
        run(
            db,
            "UPDATE admin_sessions SET revoked_at=now() WHERE account_id=:a AND id<>:session",
            a=admin.account_id,
            session=admin.session_id,
        )
        audit(db, admin.tenant_id, admin.account_id, "admin.password_changed", admin.account_id)
    return {"changed": True}


@app.post("/api/v1/auth/logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    admin = admin_context(request, allow_password_change=True)
    with transaction(admin.tenant_id) as db:
        run(db, "UPDATE admin_sessions SET revoked_at=now() WHERE id=:id", id=admin.session_id)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"logged_out": True}


@app.get("/api/v1/admin/assistant", response_model=AdminAssistantView)
def get_assistant(request: Request, response: Response) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        a, d = assistant(db), draft(db)
        tenant = one(db, "SELECT display_name FROM tenants")
    response.headers["ETag"] = f'"{d["revision"]}"'
    return {
        "tenant_name": tenant["display_name"] if tenant else "",
        "public_key": a["public_key"],
        "revision": d["revision"],
        "config": d["config_json"],
        "active_release_id": a["active_release_id"],
        "testing": settings().ai_provider == "mock",
    }


@app.patch("/api/v1/admin/assistant/draft")
def save_draft(
    payload: AssistantConfig, request: Request, if_match: str | None = Header(default=None)
) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        assistant(db, lock=True)
        d = require_revision(db, if_match)
        config = payload.model_dump(mode="json")
        if config["knowledge_version_ids"]:
            # Existing but unapproved text is allowed in draft; foreign-tenant IDs never are.
            existing = many(
                db,
                "SELECT id FROM document_versions WHERE id=ANY(CAST(:ids AS uuid[]))",
                ids=config["knowledge_version_ids"],
            )
            if len(existing) != len(config["knowledge_version_ids"]):
                raise AppError("FORBIDDEN", "Có tài liệu không thuộc phạm vi được phép.", 403)
        run(
            db,
            "UPDATE assistant_drafts SET config_json=CAST(:config AS jsonb),revision=revision+1,updated_at=now() WHERE assistant_id=:id",
            config=canonical(config),
            id=d["assistant_id"],
        )
        audit(
            db,
            admin.tenant_id,
            admin.account_id,
            "draft.saved",
            str(d["assistant_id"]),
            {"revision": d["revision"] + 1},
        )
    return {"revision": d["revision"] + 1}


@app.get("/api/v1/admin/knowledge/documents")
def list_documents(
    request: Request,
    page: int = Query(default=1, ge=1, le=1000000),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str = Query(default="", max_length=200),
    status: Literal[
        "uploaded",
        "scanning",
        "extracting",
        "needs_review",
        "indexing",
        "ready",
        "quarantined",
        "failed",
        "cancelled",
        "revoked",
        "purged",
    ]
    | None = None,
    approved: bool | None = None,
    file_type: Literal[
        "text", "pdf", "docx", "xlsx", "pptx", "txt", "md", "csv", "html", "png", "jpg", "jpeg"
    ]
    | None = None,
    effectivity: Literal["active", "future", "expired", "unknown"] | None = None,
) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        return catalog(
            db,
            page=page,
            page_size=page_size,
            q=q.strip(),
            status=status,
            approved=approved,
            file_type=file_type,
            effectivity=effectivity,
        )


@app.get("/api/v1/admin/knowledge/documents/{document_id}")
def document_detail(
    document_id: UUID,
    request: Request,
    page: int = Query(default=1, ge=1, le=1000000),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        doc = one(db, "SELECT id,title,revoked_at FROM documents WHERE id=:id", id=document_id)
        if not doc:
            raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy tài liệu.", 404)
        versions = many(
            db,
            "SELECT id,number,parse_status,approved_for_public,effective_from,effective_to,created_at FROM document_versions WHERE document_id=:id ORDER BY number DESC LIMIT :limit OFFSET :offset",
            id=document_id,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        total = one(db, "SELECT count(*) AS n FROM document_versions WHERE document_id=:id", id=document_id)
    count = int(total["n"]) if total else 0
    return {
        **doc,
        "versions": versions,
        "total": count,
        "page": page,
        "next_cursor": str(page + 1) if page * page_size < count else None,
    }


@app.post("/api/v1/admin/knowledge/texts", status_code=201)
def add_text(payload: KnowledgeText, request: Request) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        return create_text(db, admin.tenant_id, admin.account_id, payload)


@app.post("/api/v1/admin/knowledge/documents/{document_id}/versions", status_code=201)
def new_text_version(document_id: UUID, payload: KnowledgeText, request: Request) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        return create_text(db, admin.tenant_id, admin.account_id, payload, document_id=str(document_id))


@app.post("/api/v1/admin/knowledge/versions/{version_id}/approve-public")
def approve(version_id: UUID, payload: Approval, request: Request) -> dict[str, bool]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        row = one(
            db,
            "UPDATE document_versions v SET approved_for_public=true,approved_by=:actor,approved_at=now() FROM documents d WHERE v.id=:id AND (d.tenant_id,d.id)=(v.tenant_id,v.document_id) AND v.parse_status='ready' AND v.scan_status IN ('clean','not_required') AND COALESCE(v.metadata_json->>'classification','public')='public' AND d.revoked_at IS NULL AND d.purged_at IS NULL RETURNING v.id,v.extraction_revision",
            id=version_id,
            actor=admin.account_id,
        )
        if not row:
            raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy phiên bản tài liệu.", 404)
        audit(
            db,
            admin.tenant_id,
            admin.account_id,
            "knowledge.public_approved",
            str(version_id),
            {"revision": row["extraction_revision"]},
        )
    return {"approved_for_public": True}


@app.post("/api/v1/admin/knowledge/documents/{document_id}/revoke")
def revoke(document_id: UUID, payload: Reason, request: Request) -> dict[str, bool]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        row = one(db, "UPDATE documents SET revoked_at=now() WHERE id=:id RETURNING id", id=document_id)
        if not row:
            raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy tài liệu.", 404)
        run(db, "UPDATE tenants SET security_epoch=security_epoch+1")
        audit(
            db,
            admin.tenant_id,
            admin.account_id,
            "knowledge.revoked",
            str(document_id),
            {"reason": payload.reason},
        )
    return {"revoked": True}


@app.post("/api/v1/admin/releases/validate")
def validate_release(request: Request, if_match: str | None = Header(default=None)) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        assistant(db, lock=True)
        d = require_revision(db, if_match)
        versions = check_versions(db, d["config_json"], public=True)
        epoch = one(db, "SELECT security_epoch FROM tenants")
        validation_id = new_id()
        run(
            db,
            "INSERT INTO release_validations(id,tenant_id,assistant_id,draft_hash,runtime_fingerprint,security_epoch) VALUES(:id,:t,:a,:hash,:runtime,:epoch)",
            id=validation_id,
            t=admin.tenant_id,
            a=d["assistant_id"],
            hash=fingerprint(d["config_json"]),
            runtime=settings().runtime_fingerprint,
            epoch=epoch["security_epoch"] if epoch else 0,
        )
    return {
        "validation_id": validation_id,
        "passed": True,
        "scope": "M1 minimum preflight — chưa thay thế đánh giá chất lượng AI/UAT",
        "checks": [
            "Đúng tenant",
            "Tài liệu sẵn sàng và đã xác nhận công khai",
            "Hiệu lực và thu hồi",
            "Bản nháp và cấu hình chạy hiện hành",
        ],
        "document_count": len(versions),
    }


@app.post("/api/v1/admin/releases", status_code=201)
def publish(
    payload: Publish, request: Request, if_match: str | None = Header(default=None)
) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        assistant(db, lock=True)
        d = require_revision(db, if_match)
        epoch = one(db, "SELECT security_epoch FROM tenants")
        validation = one(
            db,
            "SELECT * FROM release_validations WHERE id=:id AND created_at>now()-interval '30 minutes'",
            id=payload.validation_id,
        )
        if (
            not validation
            or validation["draft_hash"] != fingerprint(d["config_json"])
            or validation["runtime_fingerprint"] != settings().runtime_fingerprint
            or not epoch
            or validation["security_epoch"] != epoch["security_epoch"]
        ):
            raise AppError("VERSION_CONFLICT", "Cần chạy lại kiểm tra trên bản nháp và quyền hiện tại.", 409)
        return publish_snapshot(db, admin.tenant_id, admin.account_id, d["config_json"], payload.reason)


@app.get("/api/v1/admin/releases")
def releases(request: Request) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        return {
            "items": many(
                db,
                "SELECT id,sequence,content_hash,reason,created_at FROM content_releases ORDER BY sequence DESC LIMIT 100",
            )
        }


@app.post("/api/v1/admin/releases/{release_id}/rollback")
def rollback(release_id: UUID, payload: Reason, request: Request) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        assistant(db, lock=True)
        old = one(db, "SELECT snapshot,runtime_fingerprint FROM content_releases WHERE id=:id", id=release_id)
        if not old:
            raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy phiên bản.", 404)
        if old["runtime_fingerprint"] != settings().runtime_fingerprint:
            raise AppError(
                "VERSION_CONFLICT", "Phiên bản cần được kiểm tra lại với môi trường hiện tại.", 409
            )
        return publish_snapshot(
            db, admin.tenant_id, admin.account_id, old["snapshot"], "Khôi phục: " + payload.reason
        )


@app.post("/api/v1/admin/assistant/pause")
def pause(request: Request) -> dict[str, bool]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        a = assistant(db, lock=True)
        run(db, "UPDATE assistants SET paused=NOT paused")
        run(db, "UPDATE tenants SET security_epoch=security_epoch+1")
        audit(db, admin.tenant_id, admin.account_id, "assistant.pause_changed", str(a["id"]))
    return {"paused": not a["paused"]}


@app.get("/api/v1/admin/dashboard")
def dashboard(request: Request) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        return {
            "documents": one(db, "SELECT count(*) AS n FROM documents"),
            "turns": one(db, "SELECT count(*) AS n FROM chat_turns"),
            "feedback": many(db, "SELECT rating,count(*) AS n FROM feedback GROUP BY rating"),
            "paused": assistant(db)["paused"],
        }


@app.get("/api/v1/admin/audit")
def audit_log(request: Request) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        return {
            "items": many(
                db,
                "SELECT event_type,resource_id,detail,created_at FROM audit_events ORDER BY created_at DESC LIMIT 100",
            )
        }


@app.get("/api/v1/admin/capabilities")
def capabilities(request: Request) -> dict[str, Any]:
    admin_context(request)
    ids = [
        "knowledge_search",
        "web_search",
        "actions",
        "document_analysis",
        "code_interpreter",
        "image_generation",
        "voice_input",
        "voice_output",
        "custom_extensions",
    ]
    return {
        "items": [
            {
                "id": c,
                "implementation": "implemented" if c == "knowledge_search" else "not_implemented",
                "availability": "enabled" if c == "knowledge_search" else "not_granted",
            }
            for c in ids
        ]
    }


@app.get("/api/v1/public/assistants/{public_key}")
def public_assistant(public_key: str) -> dict[str, Any]:
    with transaction() as db:
        ref = one(db, "SELECT * FROM resolve_assistant(:key)", key=public_key)
    if not ref:
        raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy trợ lý.", 404)
    with transaction(str(ref["tenant_id"])) as db:
        a = assistant(db)
        tenant = one(db, "SELECT display_name FROM tenants")
        release = one(db, "SELECT snapshot FROM content_releases WHERE id=:id", id=a["active_release_id"])
    config = release["snapshot"] if release else AssistantConfig().model_dump(mode="json")
    return {
        "name": config["name"],
        "welcome_message": config["welcome_message"],
        "conversation_starters": config["conversation_starters"],
        "branding": config["branding"],
        "tenant_name": tenant["display_name"] if tenant else "",
        "published": bool(release),
        "paused": a["paused"],
        "testing": settings().ai_provider == "mock",
        "citizen_login_configured": False,
    }


def new_chat_session(
    tenant_id: str,
    a: dict[str, Any],
    mode: str,
    snapshot: dict[str, Any] | None = None,
    admin_session_id: str | None = None,
) -> dict[str, Any]:
    token, session_id = secrets.token_urlsafe(40), new_id()
    with transaction(tenant_id) as db:
        run(
            db,
            "INSERT INTO chat_sessions(id,tenant_id,assistant_id,token_hash,mode,draft_snapshot,expires_at,admin_session_id) VALUES(:id,:t,:a,:token,:mode,CAST(:snapshot AS jsonb),now()+interval '2 hours',:owner)",
            id=session_id,
            t=tenant_id,
            a=a["id"],
            token=digest(token),
            mode=mode,
            snapshot=canonical(snapshot) if snapshot else None,
            owner=admin_session_id,
        )
    return {"session_id": session_id, "session_token": token, "mode": mode}


@app.post("/api/v1/public/assistants/{public_key}/sessions", response_model=SessionView, status_code=201)
def public_session(public_key: str, request: Request) -> dict[str, Any]:
    rate_limit("session:" + (request.client.host if request.client else "unknown"), 30)
    with transaction() as db:
        ref = one(db, "SELECT * FROM resolve_assistant(:key)", key=public_key)
    if not ref:
        raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy trợ lý.", 404)
    with transaction(str(ref["tenant_id"])) as db:
        a = assistant(db)
        if a["paused"] or not a["active_release_id"]:
            raise AppError("TENANT_PAUSED", "Trợ lý chưa xuất bản hoặc đang tạm dừng.", 409)
    return new_chat_session(str(ref["tenant_id"]), a, "public")


@app.post("/api/v1/admin/assistant/preview/sessions", response_model=SessionView, status_code=201)
def preview_session(request: Request) -> dict[str, Any]:
    admin = admin_context(request)
    with transaction(admin.tenant_id) as db:
        a, d = assistant(db), draft(db)
    return new_chat_session(admin.tenant_id, a, "preview", d["config_json"], admin.session_id)


@app.post("/api/v1/chat/sessions/{session_id}/turns", status_code=202)
def create_turn(session_id: UUID, payload: TurnInput, request: Request) -> dict[str, Any]:
    ctx = bearer_context(request)
    if str(session_id) != ctx["session_id"]:
        raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy phiên trò chuyện.", 404)
    rate_limit("turn:" + ctx["tenant_id"], 120)
    with transaction(ctx["tenant_id"]) as db:
        session = one(db, "SELECT * FROM chat_sessions WHERE id=:id FOR UPDATE", id=session_id)
        assert session
        old = one(
            db,
            "SELECT * FROM chat_turns WHERE session_id=:s AND client_request_id=:id",
            s=session_id,
            id=payload.client_request_id,
        )
        body_hash = fingerprint(payload.model_dump(mode="json"))
        if old:
            if old["payload_hash"] != body_hash:
                raise AppError("VERSION_CONFLICT", "Mã yêu cầu đã được dùng với nội dung khác.", 409)
            turn_id = str(old["id"])
        else:
            if one(
                db,
                "SELECT id FROM chat_turns WHERE session_id=:s AND state IN ('queued','generating')",
                s=session_id,
            ):
                raise AppError("VERSION_CONFLICT", "Phiên đang xử lý một câu hỏi. Vui lòng chờ.", 409)
            a = assistant(db)
            if a["paused"]:
                raise AppError("TENANT_PAUSED", "Trợ lý đang tạm dừng.", 409)
            release = one(
                db, "SELECT id,snapshot FROM content_releases WHERE id=:id", id=a["active_release_id"]
            )
            config = (
                session["draft_snapshot"]
                if session["mode"] == "preview"
                else (release["snapshot"] if release else None)
            )
            if not config:
                raise AppError("KNOWLEDGE_NOT_READY", "Trợ lý chưa có phiên bản xuất bản.", 409)
            turn_id = new_id()
            run(
                db,
                "INSERT INTO chat_turns(id,tenant_id,session_id,client_request_id,payload_hash,message,release_id,config_snapshot,runtime_fingerprint) VALUES(:id,:t,:s,:request,:hash,:message,:r,CAST(:config AS jsonb),:runtime)",
                id=turn_id,
                t=ctx["tenant_id"],
                s=session_id,
                request=payload.client_request_id,
                hash=body_hash,
                message=payload.message,
                r=release["id"] if release and session["mode"] == "public" else None,
                config=canonical(config),
                runtime=settings().runtime_fingerprint,
            )
            run(
                db,
                "INSERT INTO outbox_events(id,tenant_id,turn_id) VALUES(:id,:t,:turn)",
                id=new_id(),
                t=ctx["tenant_id"],
                turn=turn_id,
            )
            event(db, ctx["tenant_id"], turn_id, "turn.created", {"state": "queued"})
    return {
        "turn_id": turn_id,
        "state": "queued",
        "events_path": f"/api/v1/chat/turns/{turn_id}/events",
        "request_id": request.state.request_id,
    }


@app.get("/api/v1/chat/turns/{turn_id}", response_model=TurnView)
def get_turn(turn_id: UUID, request: Request) -> dict[str, Any]:
    ctx = bearer_context(request)
    with transaction(ctx["tenant_id"]) as db:
        return turn_view(db, owned_turn(db, str(turn_id), ctx["session_id"]))


@app.post("/api/v1/chat/turns/{turn_id}/cancel")
def cancel(turn_id: UUID, request: Request) -> dict[str, str]:
    ctx = bearer_context(request)
    with transaction(ctx["tenant_id"]) as db:
        row = owned_turn(db, str(turn_id), ctx["session_id"], lock=True)
        if row["state"] in {"queued", "generating"}:
            run(db, "UPDATE chat_turns SET state='cancelled',lease_until=NULL WHERE id=:id", id=turn_id)
            event(db, ctx["tenant_id"], str(turn_id), "turn.cancelled", {"state": "cancelled"})
            return {"state": "cancelled"}
    return {"state": row["state"]}


@app.post("/api/v1/chat/turns/{turn_id}/feedback")
def feedback(turn_id: UUID, payload: FeedbackInput, request: Request) -> dict[str, bool]:
    ctx = bearer_context(request)
    with transaction(ctx["tenant_id"]) as db:
        row = owned_turn(db, str(turn_id), ctx["session_id"])
        if row["state"] != "completed":
            raise AppError("VERSION_CONFLICT", "Chỉ đánh giá lượt đã hoàn tất.", 409)
        run(
            db,
            "INSERT INTO feedback(id,tenant_id,turn_id,rating,comment) VALUES(:id,:t,:turn,:rating,:comment) ON CONFLICT(tenant_id,turn_id) DO UPDATE SET rating=EXCLUDED.rating,comment=EXCLUDED.comment",
            id=new_id(),
            t=ctx["tenant_id"],
            turn=turn_id,
            rating=payload.rating,
            comment=payload.comment,
        )
    return {"saved": True}


@app.get("/api/v1/sources/{citation_id}")
def source(citation_id: UUID, request: Request) -> dict[str, Any]:
    ctx = bearer_context(request)
    with transaction(ctx["tenant_id"]) as db:
        row = one(
            db,
            """SELECT d.title,k.body,k.ordinal AS section,k.locator FROM citations c
            JOIN chat_turns t ON (t.tenant_id,t.id)=(c.tenant_id,c.turn_id)
            JOIN chat_sessions s ON (s.tenant_id,s.id)=(t.tenant_id,t.session_id)
            JOIN document_versions v ON (v.tenant_id,v.id)=(c.tenant_id,c.version_id)
            JOIN documents d ON (d.tenant_id,d.id)=(v.tenant_id,v.document_id)
            JOIN knowledge_chunks k ON (k.tenant_id,k.id)=(c.tenant_id,c.chunk_id)
            WHERE c.id=:id AND t.session_id=:session AND d.revoked_at IS NULL
            AND (s.mode='preview' OR v.approved_for_public)
            AND (v.effective_from IS NULL OR v.effective_from<=CURRENT_DATE)
            AND (v.effective_to IS NULL OR v.effective_to>=CURRENT_DATE)""",
            id=citation_id,
            session=ctx["session_id"],
        )
        if not row:
            raise AppError("SOURCE_REVOKED", "Nguồn không còn khả dụng hoặc không thuộc phiên này.", 404)
    return {**row, "source_type": "knowledge", "label": "Tài liệu của phường"}


@app.get("/api/v1/chat/turns/{turn_id}/events")
def events(
    turn_id: UUID, request: Request, last_event_id: str | None = Header(default=None)
) -> StreamingResponse:
    ctx = bearer_context(request)
    with transaction(ctx["tenant_id"]) as db:
        owned_turn(db, str(turn_id), ctx["session_id"])
        after = 0
        if last_event_id:
            try:
                event_uuid = UUID(last_event_id)
            except ValueError as exc:
                raise AppError("VALIDATION_ERROR", "Mã nối lại stream không hợp lệ.", 422) from exc
            last = one(
                db,
                "SELECT sequence FROM turn_events WHERE id=:id AND turn_id=:turn",
                id=event_uuid,
                turn=turn_id,
            )
            if not last:
                raise AppError("VALIDATION_ERROR", "Mã nối lại stream không hợp lệ.", 422)
            after = last["sequence"]

    async def stream() -> AsyncIterator[str]:
        sequence = after
        for _ in range(480):
            if await request.is_disconnected():
                return
            # Reauthenticate and release every DB connection before yielding bytes.
            refreshed = bearer_context(request)
            with transaction(refreshed["tenant_id"]) as db:
                row = owned_turn(db, str(turn_id), refreshed["session_id"])
                batch = many(
                    db,
                    "SELECT id,sequence,kind,payload,created_at FROM turn_events WHERE turn_id=:id AND sequence>:seq ORDER BY sequence",
                    id=turn_id,
                    seq=sequence,
                )
                safe_view = turn_view(db, row) if row["state"] == "completed" else None
            for item in batch:
                # Reconstruct answer events from current authorized terminal data after revocation.
                payload = item["payload"]
                if safe_view is not None:
                    if item["kind"] == "turn.completed":
                        payload = safe_view
                    elif item["kind"] == "turn.evidence_ready":
                        payload = {"citations": safe_view["citations"]}
                    elif item["kind"] == "answer.delta":
                        continue
                sequence = item["sequence"]
                packet = {
                    "event_id": str(item["id"]),
                    "turn_id": str(turn_id),
                    "sequence": sequence,
                    "timestamp": item["created_at"].isoformat(),
                    "payload": payload,
                }
                yield f"id: {item['id']}\nevent: {item['kind']}\ndata: {canonical(packet)}\n\n"
            if row["state"] in {"completed", "failed", "cancelled"}:
                return
            yield ": heartbeat\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})
