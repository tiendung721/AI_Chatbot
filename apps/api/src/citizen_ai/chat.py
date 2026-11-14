import logging
from typing import Any

from sqlalchemy.orm import Session

from .common import AppError, canonical, new_id
from .config import settings
from .db import many, one, run, transaction


def event(db: Session, tenant_id: str, turn_id: str, kind: str, payload: dict[str, Any]) -> None:
    sequence = one(
        db, "SELECT COALESCE(max(sequence),0)+1 AS n FROM turn_events WHERE turn_id=:id", id=turn_id
    )
    run(
        db,
        "INSERT INTO turn_events(id,tenant_id,turn_id,sequence,kind,payload) VALUES(:id,:t,:turn,:n,:kind,CAST(:payload AS jsonb))",
        id=new_id(),
        t=tenant_id,
        turn=turn_id,
        n=sequence["n"] if sequence else 1,
        kind=kind,
        payload=canonical(payload),
    )


def owned_turn(db: Session, turn_id: str, session_id: str, *, lock: bool = False) -> dict[str, Any]:
    row = one(
        db,
        "SELECT * FROM chat_turns WHERE id=:id AND session_id=:session" + (" FOR UPDATE" if lock else ""),
        id=turn_id,
        session=session_id,
    )
    if not row:
        raise AppError("RESOURCE_NOT_FOUND", "Không tìm thấy lượt trò chuyện.", 404)
    return row


def turn_view(db: Session, row: dict[str, Any]) -> dict[str, Any]:
    citations = many(
        db,
        """SELECT c.id,c.evidence_id,d.title,k.ordinal AS section,k.locator FROM citations c
        JOIN document_versions v ON (v.tenant_id,v.id)=(c.tenant_id,c.version_id)
        JOIN documents d ON (d.tenant_id,d.id)=(v.tenant_id,v.document_id)
        JOIN knowledge_chunks k ON (k.tenant_id,k.id)=(c.tenant_id,c.chunk_id)
        WHERE c.turn_id=:id AND d.revoked_at IS NULL AND (v.effective_from IS NULL OR v.effective_from<=CURRENT_DATE)
        AND (v.effective_to IS NULL OR v.effective_to>=CURRENT_DATE) ORDER BY c.evidence_id""",
        id=row["id"],
    )
    answer = row["result_json"]
    # Old terminal results remain stored for audit, but are not served as usable answers after revocation.
    if answer:
        required = {e for b in answer["blocks"] for e in b["evidence_ids"]}
        if not required.issubset({c["evidence_id"] for c in citations}):
            answer = {
                "status": "insufficient_evidence",
                "blocks": [],
                "follow_up_question": "Nguồn đã bị thu hồi hoặc hết hiệu lực. Vui lòng đặt câu hỏi mới.",
                "needs_login": False,
            }
            citations = []
    return {
        "turn_id": row["id"],
        "state": row["state"],
        "answer": answer,
        "citations": [{**c, "source_path": f"/api/v1/sources/{c['id']}"} for c in citations],
        "error_code": row["error_code"],
        "testing": settings().ai_provider == "mock",
    }


def process_turn(tenant_id: str, turn_id: str) -> None:
    from .ai.adapters import model_adapter
    from .ai.contracts import GenerationRequest, validate_answer
    from .retrieval import retrieve

    claim = new_id()
    try:
        with transaction(tenant_id) as db:
            row = one(
                db,
                "SELECT t.*,s.mode,s.expires_at,s.token_hash AS session_token_hash,s.admin_session_id,a.paused FROM chat_turns t JOIN chat_sessions s ON (s.tenant_id,s.id)=(t.tenant_id,t.session_id) JOIN assistants a ON (a.tenant_id,a.id)=(s.tenant_id,s.assistant_id) WHERE t.id=:id FOR UPDATE OF t",
                id=turn_id,
            )
            if not row or row["state"] in {"completed", "failed", "cancelled"}:
                return
            live = one(db, "SELECT 1 AS live FROM chat_turns WHERE id=:id AND lease_until>now()", id=turn_id)
            if row["state"] == "generating" and live:
                return
            if row["paused"]:
                raise AppError("TENANT_PAUSED", "Trợ lý đang tạm dừng.", 409)
            valid_session = one(
                db,
                "SELECT 1 AS ok FROM resolve_chat(:hash)",
                hash=row["session_token_hash"],
            )
            if not valid_session or row["attempts"] >= 3:
                raise AppError("AI_UNAVAILABLE", "Lượt hỏi chưa thể hoàn tất. Vui lòng tạo lượt mới.", 503)
            # claim_id is a fencing token: an expired worker may never commit over a new worker's lease.
            run(
                db,
                "UPDATE chat_turns SET state='generating',lease_until=now()+interval '5 minutes',attempts=attempts+1,claim_id=:claim WHERE id=:id",
                id=turn_id,
                claim=claim,
            )
            event(db, tenant_id, turn_id, "turn.status", {"status": "searching"})
            evidence = retrieve(db, row["message"], row["config_snapshot"], public=row["mode"] == "public")
            event(db, tenant_id, turn_id, "turn.status", {"status": "generating"})
        # Deliberately no DB transaction/connection is held during the model call.
        result = model_adapter().generate(
            GenerationRequest(row["message"], row["config_snapshot"]["instructions"], evidence)
        )
        validate_answer(result.answer, evidence)
        with transaction(tenant_id) as db:
            current = one(db, "SELECT * FROM chat_turns WHERE id=:id FOR UPDATE", id=turn_id)
            if not current or current["state"] != "generating" or str(current["claim_id"]) != claim:
                return
            paused = one(db, "SELECT paused FROM assistants FOR SHARE")
            if paused and paused["paused"]:
                raise AppError("TENANT_PAUSED", "Trợ lý đang tạm dừng.", 409)
            if row["mode"] == "preview":
                one(db, "SELECT id FROM admin_sessions WHERE id=:id FOR SHARE", id=row["admin_session_id"])
            if not one(db, "SELECT 1 AS ok FROM resolve_chat(:hash)", hash=row["session_token_hash"]):
                raise AppError("SESSION_EXPIRED", "Phiên đã hết hạn hoặc bị thu hồi.", 401)
            # Lock source rows until final commit so revocation cannot race answer publication.
            if evidence:
                available = many(
                    db,
                    "SELECT v.id FROM document_versions v JOIN documents d ON (d.tenant_id,d.id)=(v.tenant_id,v.document_id) WHERE v.id=ANY(CAST(:ids AS uuid[])) AND d.revoked_at IS NULL AND (:public=false OR v.approved_for_public) AND (v.effective_from IS NULL OR v.effective_from<=CURRENT_DATE) AND (v.effective_to IS NULL OR v.effective_to>=CURRENT_DATE) FOR SHARE OF d,v",
                    ids=list({e["version_id"] for e in evidence}),
                    public=row["mode"] == "public",
                )
                if {str(v["id"]) for v in available} != {e["version_id"] for e in evidence}:
                    raise AppError(
                        "SOURCE_REVOKED", "Nguồn vừa thay đổi. Vui lòng hỏi lại để dùng nguồn hiện hành.", 409
                    )
            referenced = {eid for b in result.answer.blocks for eid in b.evidence_ids}
            for e in evidence:
                if e["evidence_id"] in referenced:
                    run(
                        db,
                        "INSERT INTO citations(id,tenant_id,turn_id,version_id,chunk_id,evidence_id) VALUES(:id,:t,:turn,:v,:chunk,:e)",
                        id=new_id(),
                        t=tenant_id,
                        turn=turn_id,
                        v=e["version_id"],
                        chunk=e["chunk_id"],
                        e=e["evidence_id"],
                    )
            run(
                db,
                "UPDATE chat_turns SET state='completed',result_json=CAST(:answer AS jsonb),lease_until=NULL WHERE id=:id",
                answer=canonical(result.answer.model_dump()),
                id=turn_id,
            )
            run(
                db,
                "INSERT INTO usage_events(id,tenant_id,turn_id,input_tokens,output_tokens,runtime_fingerprint) VALUES(:id,:t,:turn,:input,:output,:runtime)",
                id=new_id(),
                t=tenant_id,
                turn=turn_id,
                input=result.input_tokens,
                output=result.output_tokens,
                runtime=settings().runtime_fingerprint,
            )
            updated = one(db, "SELECT * FROM chat_turns WHERE id=:id", id=turn_id)
            assert updated
            view = turn_view(db, updated)
            event(db, tenant_id, turn_id, "turn.evidence_ready", {"citations": view["citations"]})
            for block in result.answer.blocks:
                event(db, tenant_id, turn_id, "answer.delta", {"text": block.text})
            event(db, tenant_id, turn_id, "turn.completed", view)
    except Exception as exc:
        code = exc.code if isinstance(exc, AppError) else "AI_UNAVAILABLE"
        logging.getLogger("citizen_ai").warning(
            "turn_failed turn_id=%s code=%s type=%s", turn_id, code, type(exc).__name__
        )
        with transaction(tenant_id) as db:
            row = one(db, "SELECT * FROM chat_turns WHERE id=:id FOR UPDATE", id=turn_id)
            if (
                row
                and row["state"] in {"queued", "generating"}
                and (row.get("claim_id") is None or str(row["claim_id"]) == claim)
            ):
                run(
                    db,
                    "UPDATE chat_turns SET state='failed',error_code=:code,lease_until=NULL WHERE id=:id",
                    code=code,
                    id=turn_id,
                )
                event(
                    db,
                    tenant_id,
                    turn_id,
                    "turn.failed",
                    {"code": code, "message": "Lượt trả lời chưa hoàn tất. Vui lòng thử lại an toàn."},
                )
