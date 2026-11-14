"""Bounded operator cleanup; dry-run by default and isolated to one tenant."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from ..common import canonical, new_id
from ..config import settings
from ..db import one, run, transaction
from ..storage import storage_client


def sweep_orphans(
    tenant_id: str,
    *,
    apply: bool = False,
    grace_hours: int = 24,
    maximum: int = 1000,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Only original object keys in a canonical tenant prefix are eligible."""
    tenant_id = str(UUID(tenant_id))
    if grace_hours < 24 or not 1 <= maximum <= 10000:
        raise ValueError("Orphan cleanup requires >=24 hours grace and 1–10000 objects")
    cutoff = (as_of or datetime.now(UTC)) - timedelta(hours=grace_hours)
    client, bucket = storage_client(), settings().s3_bucket
    prefix = f"tenant/{tenant_id}/documents/"
    examined = 0
    candidates: list[str] = []
    deleted: list[str] = []
    # Upload uses this lock through object creation and DB commit. The sweep does
    # not guess liveness from a list snapshot or an expired worker lease.
    with transaction(tenant_id) as db:
        run(db, "SELECT pg_advisory_xact_lock(hashtextextended(:scope,0))", scope="storage:" + tenant_id)
        for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                if examined >= maximum:
                    break
                examined += 1
                key = item["Key"]
                parts = key.split("/")
                if len(parts) != 5 or not parts[4].startswith("original.") or item["LastModified"] > cutoff:
                    continue
                try:
                    UUID(parts[3])
                except ValueError:
                    continue
                if one(db, "SELECT id FROM document_versions WHERE object_key=:key", key=key):
                    continue
                candidates.append(key)
                if apply:
                    head = client.head_object(Bucket=bucket, Key=key)
                    if (
                        head["ETag"] != item["ETag"]
                        or head["ContentLength"] != item["Size"]
                        or head["LastModified"] > cutoff
                    ):
                        continue
                    client.delete_object(Bucket=bucket, Key=key)
                    deleted.append(key)
            if examined >= maximum:
                break
        run(
            db,
            "INSERT INTO audit_events(id,tenant_id,event_type,resource_id,detail) VALUES(:id,:t,'ops.orphan_sweep',:t,CAST(:detail AS jsonb))",
            id=new_id(),
            t=tenant_id,
            detail=canonical(
                {"apply": apply, "examined": examined, "candidates": len(candidates), "deleted": len(deleted)}
            ),
        )
    return {
        "dry_run": not apply,
        "examined": examined,
        "candidates": candidates,
        "deleted": deleted,
        "limit_reached": examined >= maximum,
    }
