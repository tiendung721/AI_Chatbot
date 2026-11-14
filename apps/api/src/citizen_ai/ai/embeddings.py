"""Developer-only embedding profile operations. No implicit paid indexing."""

import hashlib
import math
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from ..common import AppError, canonical
from ..config import settings
from ..db import many, one, run, transaction


def validate_vectors(vectors: list[list[float]], count: int, dimensions: int) -> list[list[float]]:
    if len(vectors) != count or any(
        len(v) != dimensions or any(not math.isfinite(x) for x in v) or not any(v) for v in vectors
    ):
        raise AppError("EMBEDDING_PROFILE_MISMATCH", "Vector không khớp profile đang cấu hình.", 503)
    return vectors


def embed(texts: list[str], *, client: Any = None) -> list[list[float]]:
    cfg = settings()
    if not texts or len(texts) > 16 or any(not t.strip() or len(t) > 4000 for t in texts):
        raise AppError("EMBEDDING_INPUT_LIMIT", "Vượt giới hạn batch embedding.", 422)
    if cfg.embedding_provider == "mock":
        if cfg.app_env not in {"local", "test"}:
            raise AppError("CAPABILITY_NOT_GRANTED", "Mock embedding chỉ dành cho kiểm thử local.", 503)
        vectors = []
        for text in texts:
            seed = hashlib.sha256(text.encode()).digest()
            vectors.append([(seed[i % len(seed)] - 127.5) / 127.5 for i in range(cfg.embedding_dimensions)])
        return validate_vectors(vectors, len(texts), cfg.embedding_dimensions)
    if cfg.embedding_provider != "openai":
        raise AppError("CAPABILITY_NOT_GRANTED", "Embedding chưa được Developer cấu hình.", 503)
    sdk = client or OpenAI(
        api_key=cfg.openai_api_key.get_secret_value(), timeout=cfg.ai_request_timeout_seconds, max_retries=0
    )
    try:
        result = sdk.embeddings.create(
            model=cfg.openai_embedding_model,
            input=texts,
            dimensions=cfg.embedding_dimensions,
            encoding_format="float",
        )
        items = sorted(result.data, key=lambda x: x.index)
        if [i.index for i in items] != list(range(len(texts))):
            raise ValueError("invalid embedding indexes")
        return validate_vectors([i.embedding for i in items], len(texts), cfg.embedding_dimensions)
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            "EMBEDDING_UNAVAILABLE", "Dịch vụ tạo vector tạm thời chưa sẵn sàng.", 503, True
        ) from exc


def require_profile(db: Session) -> dict[str, Any]:
    cfg = settings()
    row = one(
        db,
        "SELECT id,fingerprint,dimensions FROM embedding_profiles WHERE id=CAST(:id AS uuid)",
        id=cfg.embedding_profile_id,
    )
    if (
        not row
        or row["fingerprint"] != cfg.embedding_fingerprint
        or row["dimensions"] != cfg.embedding_dimensions
    ):
        raise AppError(
            "EMBEDDING_PROFILE_MISMATCH", "Profile vector cần được Developer tạo hoặc reindex lại.", 503
        )
    return row


def create_profile() -> None:
    cfg = settings()
    if cfg.embedding_provider == "disabled":
        raise ValueError("Developer cần cấu hình embedding trước khi tạo profile.")
    with transaction(privileged=True) as db:
        run(
            db,
            "INSERT INTO embedding_profiles(id,fingerprint,dimensions) VALUES(CAST(:id AS uuid),:fp,:dims) ON CONFLICT DO NOTHING",
            id=cfg.embedding_profile_id,
            fp=cfg.embedding_fingerprint,
            dims=cfg.embedding_dimensions,
        )
        require_profile(db)


def reindex(tenant_id: str) -> int:
    cfg = settings()
    total = 0
    while True:
        with transaction(tenant_id) as db:
            require_profile(db)
            rows = many(
                db,
                """SELECT c.id,c.body,v.document_id FROM knowledge_chunks c
                JOIN document_versions v ON (v.tenant_id,v.id)=(c.tenant_id,c.version_id)
                JOIN documents d ON (d.tenant_id,d.id)=(v.tenant_id,v.document_id)
                WHERE v.parse_status='ready' AND v.approved_for_public AND v.scan_status IN ('clean','not_required')
                AND d.revoked_at IS NULL AND d.purged_at IS NULL
                AND NOT EXISTS(SELECT 1 FROM chunk_embeddings e WHERE e.chunk_id=c.id AND e.embedding_profile_id=CAST(:profile AS uuid))
                ORDER BY c.id LIMIT 16""",
                profile=cfg.embedding_profile_id,
            )
        if not rows:
            return total
        vectors = embed([r["body"] for r in rows])
        with transaction(tenant_id) as db:
            require_profile(db)
            for row, vector in zip(rows, vectors, strict=True):
                doc = one(
                    db,
                    "SELECT revoked_at,purged_at FROM documents WHERE id=:id FOR SHARE",
                    id=row["document_id"],
                )
                if not doc or doc["revoked_at"] or doc["purged_at"]:
                    continue
                run(
                    db,
                    "INSERT INTO chunk_embeddings(tenant_id,chunk_id,embedding_profile_id,embedding) SELECT :t,id,CAST(:profile AS uuid),CAST(:vector AS vector) FROM knowledge_chunks WHERE id=:id ON CONFLICT DO NOTHING",
                    t=tenant_id,
                    id=row["id"],
                    profile=cfg.embedding_profile_id,
                    vector=canonical(vector),
                )
                total += 1
