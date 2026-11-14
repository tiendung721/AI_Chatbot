from typing import Any

from celery import Celery

from .chat import process_turn
from .config import settings
from .db import many, run, transaction
from .ingestion.pipeline import process_ingestion
from .ingestion.purge import process_purge

celery = Celery("citizen_ai", broker=settings().redis_url.get_secret_value())
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    task_routes={"citizen.ingest": {"queue": "ingestion"}, "citizen.purge": {"queue": "ingestion"}},
    beat_schedule={"dispatch-outbox": {"task": "citizen.dispatch", "schedule": 2.0}},
)


@celery.task(name="citizen.turn", soft_time_limit=240, time_limit=270)
def execute_turn(tenant_id: str, turn_id: str) -> None:
    process_turn(tenant_id, turn_id)


@celery.task(name="citizen.ingest", soft_time_limit=330, time_limit=350)
def execute_ingestion(tenant_id: str, job_id: str) -> None:
    process_ingestion(tenant_id, job_id)


@celery.task(name="citizen.purge", soft_time_limit=330, time_limit=350)
def execute_purge(tenant_id: str, job_id: str) -> None:
    process_purge(tenant_id, job_id)


@celery.task(name="citizen.dispatch")
def dispatch_outbox() -> None:
    with transaction() as db:
        tenants = many(db, "SELECT tenant_id FROM worker_tenants()")
    for tenant in tenants:
        tenant_id = str(tenant["tenant_id"])
        pending: list[dict[str, Any]] = []
        with transaction(tenant_id) as db:
            pending = many(
                db,
                """SELECT o.id,o.turn_id FROM outbox_events o JOIN chat_turns t
                ON (t.tenant_id,t.id)=(o.tenant_id,o.turn_id)
                WHERE (t.state='queued' OR (t.state='generating' AND t.lease_until<now()))
                AND (o.last_dispatched_at IS NULL OR o.last_dispatched_at<now()-interval '30 seconds')
                ORDER BY o.created_at LIMIT 50 FOR UPDATE OF o SKIP LOCKED""",
            )
            for item in pending:
                run(
                    db,
                    "UPDATE outbox_events SET last_dispatched_at=now(),attempts=attempts+1 WHERE id=:id",
                    id=item["id"],
                )
        for item in pending:
            execute_turn.delay(tenant_id, str(item["turn_id"]))
        with transaction(tenant_id) as db:
            knowledge = many(
                db,
                """SELECT o.id,o.kind,o.target_id FROM knowledge_outbox o
                LEFT JOIN ingestion_jobs j ON o.kind='ingestion' AND (j.tenant_id,j.id)=(o.tenant_id,o.target_id)
                LEFT JOIN deletion_jobs p ON o.kind='purge' AND (p.tenant_id,p.id)=(o.tenant_id,o.target_id)
                WHERE (o.last_dispatched_at IS NULL OR o.last_dispatched_at<now()-interval '30 seconds')
                AND ((j.state='uploaded' OR (j.state IN ('scanning','extracting','indexing') AND j.lease_until<now()))
                OR (p.state='queued' OR (p.state='executing' AND p.lease_until<now())))
                ORDER BY o.created_at LIMIT 20 FOR UPDATE OF o SKIP LOCKED""",
            )
            for item in knowledge:
                run(
                    db,
                    "UPDATE knowledge_outbox SET last_dispatched_at=now(),attempts=attempts+1 WHERE id=:id",
                    id=item["id"],
                )
        for item in knowledge:
            task = execute_ingestion if item["kind"] == "ingestion" else execute_purge
            task.delay(tenant_id, str(item["target_id"]))
