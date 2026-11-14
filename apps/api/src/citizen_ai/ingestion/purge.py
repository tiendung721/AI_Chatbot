import logging

from ..chat import turn_view
from ..common import canonical, new_id
from ..db import many, one, run, transaction
from ..storage import delete_private


def process_purge(tenant_id: str, job_id: str) -> None:
    claim = new_id()
    document_id = None
    try:
        with transaction(tenant_id) as db:
            ref = one(db, "SELECT document_id FROM deletion_jobs WHERE id=:id", id=job_id)
            if not ref:
                return
            document_id = str(ref["document_id"])
            one(db, "SELECT id FROM documents WHERE id=:id FOR UPDATE", id=document_id)
            job = one(db, "SELECT * FROM deletion_jobs WHERE id=:id FOR UPDATE", id=job_id)
            if (
                not job
                or job["state"] == "completed"
                or one(
                    db, "SELECT 1 AS busy FROM deletion_jobs WHERE id=:id AND lease_until>now()", id=job_id
                )
            ):
                return
            run(
                db,
                "UPDATE deletion_jobs SET state='executing',claim_id=:claim,lease_until=now()+interval '6 minutes',attempts=attempts+1,error_code=NULL WHERE id=:id",
                claim=claim,
                id=job_id,
            )
            keys = many(
                db,
                "SELECT object_key FROM document_versions WHERE document_id=:id AND object_key IS NOT NULL",
                id=document_id,
            )
        for item in keys:
            delete_private(item["object_key"])
        with transaction(tenant_id) as db:
            one(db, "SELECT id FROM documents WHERE id=:id FOR UPDATE", id=document_id)
            job = one(db, "SELECT * FROM deletion_jobs WHERE id=:id FOR UPDATE", id=job_id)
            if not job or str(job["claim_id"]) != claim:
                return
            versions = [
                str(v["id"])
                for v in many(db, "SELECT id FROM document_versions WHERE document_id=:id", id=document_id)
            ]
            affected = many(
                db,
                "SELECT DISTINCT t.* FROM chat_turns t JOIN citations c ON (c.tenant_id,c.turn_id)=(t.tenant_id,t.id) WHERE c.version_id=ANY(CAST(:versions AS uuid[]))",
                versions=versions,
            )
            safe_answer = {
                "status": "insufficient_evidence",
                "blocks": [],
                "follow_up_question": "Nguồn đã được xóa theo yêu cầu. Vui lòng đặt câu hỏi mới.",
                "needs_login": False,
            }
            for turn in affected:
                run(
                    db,
                    "UPDATE chat_turns SET result_json=CAST(:answer AS jsonb) WHERE id=:id",
                    answer=canonical(safe_answer),
                    id=turn["id"],
                )
                run(db, "DELETE FROM turn_events WHERE turn_id=:id AND kind='answer.delta'", id=turn["id"])
            run(
                db,
                "DELETE FROM knowledge_chunks WHERE version_id=ANY(CAST(:versions AS uuid[]))",
                versions=versions,
            )
            run(
                db,
                "DELETE FROM document_sections WHERE version_id=ANY(CAST(:versions AS uuid[]))",
                versions=versions,
            )
            run(
                db,
                "DELETE FROM extraction_reviews WHERE version_id=ANY(CAST(:versions AS uuid[]))",
                versions=versions,
            )
            run(
                db,
                "UPDATE upload_receipts SET result_json=result_json || CAST(:patch AS jsonb) WHERE result_json->>'document_id'=:doc",
                doc=document_id,
                patch=canonical({"filename": "", "state": "purged"}),
            )
            run(
                db,
                "UPDATE document_versions SET body='',object_key=NULL,original_filename=NULL,metadata_json='{}',approved_for_public=false,approved_at=NULL,approved_by=NULL,parse_status='purged',purged_at=now(),updated_at=now(),sha256=:empty WHERE document_id=:id",
                id=document_id,
                empty="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            )
            run(
                db,
                "UPDATE documents SET title='Tài liệu đã xóa',purged_at=now() WHERE id=:id",
                id=document_id,
            )
            run(
                db,
                "UPDATE ingestion_jobs SET state='cancelled',error_code='SOURCE_PURGED',lease_until=NULL,claim_id=NULL,updated_at=now() WHERE version_id=ANY(CAST(:versions AS uuid[]))",
                versions=versions,
            )
            for turn in affected:
                updated = one(db, "SELECT * FROM chat_turns WHERE id=:id", id=turn["id"])
                assert updated
                view = turn_view(db, updated)
                run(
                    db,
                    "UPDATE turn_events SET payload=CAST(:value AS jsonb) WHERE turn_id=:id AND kind='turn.completed'",
                    id=turn["id"],
                    value=canonical(view),
                )
                run(
                    db,
                    "UPDATE turn_events SET payload=CAST(:value AS jsonb) WHERE turn_id=:id AND kind='turn.evidence_ready'",
                    id=turn["id"],
                    value=canonical({"citations": view["citations"]}),
                )
            run(
                db,
                "UPDATE deletion_jobs SET state='completed',completed_at=now(),lease_until=NULL WHERE id=:id",
                id=job_id,
            )
    except Exception as exc:
        logging.getLogger("citizen_ai").warning("purge_failed job_id=%s type=%s", job_id, type(exc).__name__)
        with transaction(tenant_id) as db:
            run(
                db,
                "UPDATE deletion_jobs SET state='failed',error_code='PURGE_FAILED',lease_until=NULL WHERE id=:id AND claim_id=:claim AND state<>'completed'",
                id=job_id,
                claim=claim,
            )
