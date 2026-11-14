import os
import time

import httpx
import pytest
from sqlalchemy.exc import DBAPIError

from citizen_ai.ai import embeddings
from citizen_ai.common import AppError, canonical, new_id
from citizen_ai.config import settings
from citizen_ai.db import many, one, run, transaction
from citizen_ai.ingestion.pipeline import process_ingestion
from citizen_ai.ingestion.purge import process_purge
from citizen_ai.ingestion.scanner import scan_bytes
from citizen_ai.retrieval import search_rows
from citizen_ai.storage import initialize_storage, storage_client

from .test_m1 import Ward
from .test_m1 import wards as wards

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1", reason="Real PostgreSQL/Redis/MinIO/ClamAV/parser required"
    ),
]


def upload(
    ward: Ward, filename: str, data: bytes, mime: str = "text/plain", document_id: str | None = None
) -> dict:
    response = ward.client.post(
        "/api/v1/admin/knowledge/uploads",
        files=[("files", (filename, data, mime))],
        data={"document_id": document_id} if document_id else {},
        headers={"X-CSRF-Token": ward.csrf},
    )
    assert response.status_code == 202, response.text
    return response.json()["items"][0]


def read_version(ward: Ward, item: dict) -> dict:
    response = ward.client.get("/api/v1/admin/knowledge/versions/" + item["version_id"])
    assert response.status_code == 200, response.text
    return response.json()


def test_real_clamav_clean_and_eicar() -> None:
    scan_bytes(b"Clean test fixture.")
    # Official EICAR antivirus test string; memory only, never write to host disk.
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}" + b"$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    with pytest.raises(AppError, match="FILE_QUARANTINED"):
        scan_bytes(eicar)


def test_upload_scan_extract_approve_source_version_and_purge(wards: list[Ward]) -> None:
    a, b = wards
    initialize_storage()
    item = upload(a, "lotus.txt", "DỮ LIỆU GIẢ. Sen xanh có mã SEN-XANH-M2-482.".encode())
    assert item["state"] == "uploaded", item
    assert (
        a.post(
            f"/admin/knowledge/versions/{item['version_id']}/approve-public", {"confirm_public": True}
        ).status_code
        == 404
    )
    process_ingestion(a.tenant_id, item["job_id"])
    process_ingestion(a.tenant_id, item["job_id"])
    version = read_version(a, item)
    assert version["parse_status"] == "ready" and version["scan_status"] == "clean", version
    assert b.client.get(f"/api/v1/admin/knowledge/jobs/{item['job_id']}").status_code == 404
    assert b.client.get(f"/api/v1/admin/knowledge/versions/{item['version_id']}").status_code == 404
    assert b.client.get(f"/api/v1/admin/knowledge/versions/{item['version_id']}/original").status_code == 404
    with transaction(a.tenant_id) as db:
        row = one(db, "SELECT object_key FROM document_versions WHERE id=:v", v=item["version_id"])
        assert row
        key = row["object_key"]
        assert (
            one(db, "SELECT count(*) AS n FROM knowledge_chunks WHERE version_id=:v", v=item["version_id"])[
                "n"
            ]
            == 1
        )
    assert storage_client().get_object(Bucket=settings().s3_bucket, Key=key)["ContentLength"] > 0
    anonymous = httpx.get(
        settings().s3_endpoint + "/" + settings().s3_bucket + "/" + key, timeout=10, trust_env=False
    )
    assert anonymous.status_code == 403
    assert a.client.get(f"/api/v1/admin/knowledge/versions/{item['version_id']}/original").content.endswith(
        b"SEN-XANH-M2-482."
    )
    assert (
        a.post(
            f"/admin/knowledge/versions/{item['version_id']}/approve-public", {"confirm_public": True}
        ).status_code
        == 200
    )
    config = {**a.config, "knowledge_version_ids": [item["version_id"]]}
    a.publish(config)
    result, session = a.ask("Sen xanh")
    assert result["answer"]["status"] == "answered", result
    assert result["citations"][0]["locator"]["kind"] == "text_section"
    citation = result["citations"][0]["source_path"]
    profile = new_id()
    with transaction(privileged=True) as db:
        run(
            db,
            "INSERT INTO embedding_profiles(id,fingerprint,dimensions) VALUES(:id,:fp,2)",
            id=profile,
            fp=profile,
        )
    with transaction(a.tenant_id) as db:
        run(
            db,
            "INSERT INTO chunk_embeddings(tenant_id,chunk_id,embedding_profile_id,embedding) SELECT tenant_id,id,:p,CAST('[1,0]' AS vector) FROM knowledge_chunks WHERE version_id=:v",
            p=profile,
            v=item["version_id"],
        )
    headers = {"Authorization": "Bearer " + session["session_token"]}
    assert a.client.get(citation, headers=headers).status_code == 200
    next_version = upload(
        a, "lotus-next.txt", b"Changed fixture SEN-XANH-M2-NEW.", document_id=item["document_id"]
    )
    process_ingestion(a.tenant_id, next_version["job_id"])
    assert read_version(a, next_version)["number"] == 2
    assert read_version(a, item)["sections"][0]["body"].endswith("SEN-XANH-M2-482.")
    deletion = a.post(
        f"/admin/knowledge/documents/{item['document_id']}/delete-request",
        {"reason": "Integration fixture removal"},
    )
    assert deletion.status_code == 202, deletion.text
    assert a.client.get(citation, headers=headers).status_code == 404
    process_purge(a.tenant_id, deletion.json()["job_id"])
    process_purge(a.tenant_id, deletion.json()["job_id"])
    state = a.client.get("/api/v1/admin/knowledge/deletions/" + deletion.json()["job_id"]).json()
    assert state["state"] == "completed", state
    with transaction(a.tenant_id) as db:
        assert not many(db, "SELECT * FROM chunk_embeddings WHERE embedding_profile_id=:p", p=profile)
        assert not many(db, "SELECT * FROM knowledge_chunks WHERE version_id=:v", v=item["version_id"])
        assert not many(db, "SELECT * FROM document_sections WHERE version_id=:v", v=item["version_id"])
        assert one(db, "SELECT body,object_key FROM document_versions WHERE id=:v", v=item["version_id"]) == {
            "body": "",
            "object_key": None,
        }
        turn = one(db, "SELECT result_json FROM chat_turns WHERE id=:id", id=result["turn_id"])
        assert "SEN-XANH-M2-482" not in canonical(turn)
        assert not many(
            db, "SELECT * FROM turn_events WHERE turn_id=:id AND kind='answer.delta'", id=result["turn_id"]
        )
    assert (
        httpx.get(
            settings().s3_endpoint + "/" + settings().s3_bucket + "/" + key, timeout=10, trust_env=False
        ).status_code
        == 403
    )
    with pytest.raises(storage_client().exceptions.NoSuchKey):
        storage_client().get_object(Bucket=settings().s3_bucket, Key=key)
    process_ingestion(a.tenant_id, item["job_id"])
    assert read_version(a, item)["parse_status"] == "purged"
    a.publish(a.config)


def test_metadata_strict_fields_revision_effectivity_and_published_immutable(wards: list[Ward]) -> None:
    a, b = wards
    item = upload(a, "metadata.txt", b"Metadata fixture SEN-XANH-DATE-482.")
    process_ingestion(a.tenant_id, item["job_id"])
    path = f"/api/v1/admin/knowledge/versions/{item['version_id']}/metadata"
    version = read_version(a, item)
    assert version["effective_from"] is None and version["effective_to"] is None
    payload = {
        "revision": version["extraction_revision"],
        "document_number": "FIXTURE-482",
        "issuer": "TEST UNIT",
        "effective_from": None,
        "effective_to": None,
    }
    headers = {"X-CSRF-Token": a.csrf}
    assert (
        a.client.patch(path, json={**payload, "embedding_profile_id": new_id()}, headers=headers).status_code
        == 422
    )
    assert b.client.patch(path, json=payload, headers={"X-CSRF-Token": b.csrf}).status_code == 404
    assert (
        a.client.patch(
            path,
            json={**payload, "effective_from": "2030-01-02", "effective_to": "2029-01-01"},
            headers=headers,
        ).status_code
        == 422
    )
    assert a.client.patch(path, json=payload, headers=headers).status_code == 200
    assert a.client.patch(path, json=payload, headers=headers).status_code == 409
    assert (
        a.post(
            f"/admin/knowledge/versions/{item['version_id']}/approve-public", {"confirm_public": True}
        ).status_code
        == 200
    )
    a.publish({**a.config, "knowledge_version_ids": [item["version_id"]]})
    version = read_version(a, item)
    assert version["published"]
    assert (
        a.client.patch(
            path, json={**payload, "revision": version["extraction_revision"]}, headers=headers
        ).status_code
        == 409
    )
    a.publish(a.config)


def test_xlsx_review_revision_ownership_and_no_hidden_leak(wards: list[Ward]) -> None:
    from tests.fixture_files import file_fixture

    a, b = wards
    item = upload(
        a,
        "table.xlsx",
        file_fixture(".xlsx"),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    process_ingestion(a.tenant_id, item["job_id"])
    version = read_version(a, item)
    assert version["parse_status"] == "needs_review", version
    assert any(s["hidden"] and not s["selected"] for s in version["sections"])
    selected = [s["id"] for s in version["sections"] if not s["hidden"]]
    payload = {
        "revision": version["extraction_revision"],
        "selected_section_ids": selected,
        "edits": [],
        "acknowledge_warnings": True,
    }
    path = f"/admin/knowledge/versions/{item['version_id']}/review"
    assert b.post(path, payload).status_code == 404
    assert a.post(path, {**payload, "selected_section_ids": [new_id()]}).status_code == 422
    assert a.post(path, {**payload, "acknowledge_warnings": False}).status_code == 422
    assert a.post(path, payload).status_code == 200
    assert a.post(path, payload).status_code == 409
    with transaction(a.tenant_id) as db:
        chunks = many(
            db, "SELECT body,locator FROM knowledge_chunks WHERE version_id=:v", v=item["version_id"]
        )
        assert chunks and all(c["locator"]["sheet"] == "Công khai" for c in chunks)
        assert "HIDDEN-SECRET-915" not in canonical(chunks)


def test_quarantine_retry_and_scanner_failure(wards: list[Ward], monkeypatch: pytest.MonkeyPatch) -> None:
    from citizen_ai.ingestion import pipeline

    a = wards[0]
    item = upload(
        a, "eicar.txt", b"X5O!P%@AP[4\\PZX54(P^)7CC)7}" + b"$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    )
    process_ingestion(a.tenant_id, item["job_id"])
    version = read_version(a, item)
    assert version["parse_status"] == "quarantined" and version["scan_status"] == "infected", version
    assert a.post(f"/admin/knowledge/jobs/{item['job_id']}/retry").status_code == 409
    assert a.client.get(f"/api/v1/admin/knowledge/versions/{item['version_id']}/original").status_code == 404
    clean = upload(a, "retry.txt", b"Retry file fixture.")

    def offline(*args):
        raise AppError("SCANNER_UNAVAILABLE", "Fixture offline", 503)

    with monkeypatch.context() as patch:
        patch.setattr(pipeline, "scan_bytes", offline)
        process_ingestion(a.tenant_id, clean["job_id"])
    assert read_version(a, clean)["scan_status"] == "error"
    assert a.post(f"/admin/knowledge/jobs/{clean['job_id']}/retry").status_code == 200
    process_ingestion(a.tenant_id, clean["job_id"])
    assert read_version(a, clean)["parse_status"] == "ready"


def test_actual_pgvector_profiles_rls_and_filtered_hybrid(
    wards: list[Ward], monkeypatch: pytest.MonkeyPatch
) -> None:
    a, b = wards
    profile, other = new_id(), new_id()
    cfg = settings().model_copy(
        update={
            "embedding_provider": "mock",
            "embedding_profile_id": profile,
            "embedding_dimensions": 3,
            "openai_embedding_model": "fixture-" + profile,
        }
    )
    monkeypatch.setattr(embeddings, "settings", lambda: cfg)
    embeddings.create_profile()
    with transaction(privileged=True) as db:
        run(
            db,
            "INSERT INTO embedding_profiles(id,fingerprint,dimensions) VALUES(:id,:fp,2)",
            id=other,
            fp=other,
        )
    assert embeddings.reindex(a.tenant_id) > 0
    assert embeddings.reindex(a.tenant_id) == 0
    with transaction(a.tenant_id) as db:
        with pytest.raises(AppError, match="EMBEDDING_PROFILE_MISMATCH"):
            monkeypatch.setattr(
                embeddings, "settings", lambda: cfg.model_copy(update={"embedding_dimensions": 2})
            )
            embeddings.require_profile(db)
        monkeypatch.setattr(embeddings, "settings", lambda: cfg)
        chunks = many(
            db,
            "SELECT id,version_id FROM knowledge_chunks WHERE version_id=:v",
            v=a.config["knowledge_version_ids"][0],
        )
        assert chunks
        rows = search_rows(
            db,
            "Thủ tục",
            a.config["knowledge_version_ids"] + b.config["knowledge_version_ids"],
            public=True,
            vector=[1.0, 0.0, 0.0],
            profile_id=profile,
        )
        assert rows and all(str(r["version_id"]) in a.config["knowledge_version_ids"] for r in rows)
        run(
            db,
            "UPDATE document_versions SET effective_to=CURRENT_DATE-1 WHERE id=:id",
            id=a.config["knowledge_version_ids"][0],
        )
        assert (
            search_rows(
                db,
                "Thủ tục",
                a.config["knowledge_version_ids"],
                public=True,
                vector=[1.0, 0.0, 0.0],
                profile_id=profile,
            )
            == []
        )
        run(
            db,
            "UPDATE document_versions SET effective_to=NULL WHERE id=:id",
            id=a.config["knowledge_version_ids"][0],
        )
    with pytest.raises(DBAPIError), transaction(a.tenant_id) as db:
        run(
            db,
            "INSERT INTO chunk_embeddings(tenant_id,chunk_id,embedding_profile_id,embedding) VALUES(:t,:c,:p,CAST('[1,0,0]' AS vector))",
            t=a.tenant_id,
            c=chunks[0]["id"],
            p=other,
        )
    with pytest.raises(DBAPIError), transaction(a.tenant_id) as db:
        run(db, "UPDATE embedding_profiles SET dimensions=9 WHERE id=:id", id=profile)
    with transaction(b.tenant_id) as db:
        assert not many(db, "SELECT * FROM chunk_embeddings WHERE embedding_profile_id=:id", id=profile)


def test_dispatcher_and_dedicated_worker_process_real_job(wards: list[Ward]) -> None:
    from citizen_ai.workers import dispatch_outbox

    a = wards[0]
    item = upload(a, "worker.txt", b"Real queue fixture WORKER-482.")
    dispatch_outbox()
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        result = a.client.get("/api/v1/admin/knowledge/jobs/" + item["job_id"]).json()
        if result["state"] in {"ready", "failed", "quarantined", "needs_review"}:
            break
        time.sleep(0.5)
    assert result["state"] == "ready", result
