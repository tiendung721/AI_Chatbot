from typing import Any

from sqlalchemy.orm import Session

from .common import AppError, canonical, search_query
from .config import settings
from .db import many, one

ELIGIBLE = """SELECT c.id AS chunk_id,c.tenant_id,c.version_id,c.ordinal,c.body,c.locator,c.search_vector,d.title
    FROM knowledge_chunks c
    JOIN document_versions v ON (v.tenant_id,v.id)=(c.tenant_id,c.version_id)
    JOIN documents d ON (d.tenant_id,d.id)=(v.tenant_id,v.document_id)
    WHERE v.id=ANY(CAST(:ids AS uuid[])) AND v.parse_status='ready' AND v.scan_status IN ('clean','not_required')
    AND d.revoked_at IS NULL AND d.purged_at IS NULL AND (:public=false OR (v.approved_for_public AND COALESCE(v.metadata_json->>'classification','public')='public'))
    AND (v.effective_from IS NULL OR v.effective_from<=CURRENT_DATE)
    AND (v.effective_to IS NULL OR v.effective_to>=CURRENT_DATE)"""


def search_rows(
    db: Session,
    question: str,
    ids: list[str],
    *,
    public: bool,
    vector: list[float] | None = None,
    profile_id: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"ids": ids, "q": search_query(question), "public": public}
    if vector is None:
        return many(
            db,
            "WITH eligible AS MATERIALIZED ("
            + ELIGIBLE
            + ") SELECT * FROM eligible WHERE search_vector @@ to_tsquery('simple',:q) ORDER BY ts_rank_cd(search_vector,to_tsquery('simple',:q)) DESC,chunk_id LIMIT 8",
            **params,
        )
    params.update(vector=canonical(vector), profile=profile_id)
    return many(
        db,
        """WITH eligible AS MATERIALIZED ("""
        + ELIGIBLE
        + """),
        lexical AS (SELECT chunk_id,row_number() OVER(ORDER BY ts_rank_cd(search_vector,to_tsquery('simple',:q)) DESC,chunk_id) AS rank
            FROM eligible WHERE search_vector @@ to_tsquery('simple',:q) ORDER BY rank LIMIT 20),
        vectors AS MATERIALIZED (SELECT a.chunk_id,e.embedding FROM eligible a JOIN chunk_embeddings e
            ON (e.tenant_id,e.chunk_id)=(a.tenant_id,a.chunk_id) JOIN embedding_profiles p ON p.id=e.embedding_profile_id
            WHERE e.embedding_profile_id=CAST(:profile AS uuid) AND p.dimensions=vector_dims(CAST(:vector AS vector))),
        semantic AS (SELECT chunk_id,row_number() OVER(ORDER BY cosine_distance(embedding,CAST(:vector AS vector)),chunk_id) AS rank
            FROM vectors ORDER BY rank LIMIT 20),
        scores AS (SELECT chunk_id,sum(score) AS score FROM (
            SELECT chunk_id,1.0/(60+rank) AS score FROM lexical UNION ALL SELECT chunk_id,1.0/(60+rank) FROM semantic
        ) s GROUP BY chunk_id)
        SELECT a.* FROM eligible a JOIN scores s USING(chunk_id) ORDER BY s.score DESC,a.chunk_id LIMIT 8""",
        **params,
    )


def retrieve(db: Session, question: str, config: dict[str, Any], *, public: bool) -> list[dict[str, Any]]:
    ids = config.get("knowledge_version_ids", [])
    if not ids or not config["capabilities"]["knowledge_search"]:
        return []
    vector = None
    cfg = settings()
    external = cfg.ai_provider == "openai" or cfg.embedding_provider == "openai"
    if external and one(
        db,
        "SELECT id FROM document_versions WHERE id=ANY(CAST(:ids AS uuid[])) AND (NOT approved_for_public OR COALESCE(metadata_json->>'classification','public')<>'public') LIMIT 1",
        ids=ids,
    ):
        raise AppError(
            "DATA_POLICY_BLOCKED",
            "Nguồn chưa được xác nhận công khai, không được gửi tới dịch vụ AI bên ngoài.",
            409,
        )
    if cfg.embedding_provider != "disabled":
        from .ai.embeddings import embed, require_profile

        require_profile(db)
        vector = embed([question])[0]
    rows = search_rows(
        db,
        question,
        ids,
        public=public or external,
        vector=vector,
        profile_id=cfg.embedding_profile_id or None,
    )
    return [
        {
            "evidence_id": f"E{i}",
            "chunk_id": str(r["chunk_id"]),
            "version_id": str(r["version_id"]),
            "title": r["title"],
            "text": r["body"],
            "locator": r["locator"] or {"kind": "text_section", "section": r["ordinal"]},
        }
        for i, r in enumerate(rows, 1)
    ]
