"""P1 acceptance on real PostgreSQL, storage, scanner and parser."""

import os
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.exc import DBAPIError

from citizen_ai.common import AppError, new_id
from citizen_ai.config import settings
from citizen_ai.db import many, one, run, transaction
from citizen_ai.ingestion.cleanup import sweep_orphans
from citizen_ai.ingestion.pipeline import process_ingestion
from citizen_ai.ingestion.purge import process_purge
from citizen_ai.storage import get_private, put_private

from .test_m1 import Ward
from .test_m1 import wards as wards
from .test_m2 import read_version, upload

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.getenv("RUN_DB_TESTS") != "1", reason="Real services required"),
]


def test_batch_retry_concurrency_and_payload_conflict(wards: list[Ward]) -> None:
    a, b = wards
    request_id = new_id()

    def send(ward: Ward, body: bytes = b"P1 idempotency fixture."):
        return ward.client.post(
            "/api/v1/admin/knowledge/uploads",
            files=[("files", ("retry.txt", body, "text/plain"))],
            data={"client_request_id": request_id},
            headers={"X-CSRF-Token": ward.csrf},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: send(a), range(2)))
    assert all(r.status_code == 202 for r in results), [r.text for r in results]
    first = results[0].json()["items"][0]
    assert first == results[1].json()["items"][0]
    assert send(a).json()["items"][0] == first
    assert send(a, b"Changed payload.").status_code == 409
    partial_id = new_id()

    def partial():
        return a.client.post(
            "/api/v1/admin/knowledge/uploads",
            data={"client_request_id": partial_id},
            files=[
                ("files", ("valid.txt", b"Valid partial batch.", "text/plain")),
                ("files", ("unsupported.exe", b"not executable fixture", "application/octet-stream")),
                ("files", ("empty.txt", b"", "text/plain")),
            ],
            headers={"X-CSRF-Token": a.csrf},
        )

    batch, retry = partial(), partial()
    assert batch.status_code == retry.status_code == 202
    assert batch.json()["items"] == retry.json()["items"]
    assert [x["state"] for x in batch.json()["items"]] == ["uploaded", "rejected", "rejected"]
    foreign = send(b).json()["items"][0]
    assert foreign["version_id"] != first["version_id"]
    with transaction(a.tenant_id) as db:
        assert (
            one(db, "SELECT count(*) AS n FROM upload_receipts WHERE batch_id=:id", id=request_id)["n"] == 1
        )
        assert not one(db, "SELECT id FROM document_versions WHERE id=:id", id=foreign["version_id"])
    with pytest.raises(DBAPIError), transaction(a.tenant_id) as db:
        run(
            db,
            "INSERT INTO upload_receipts(tenant_id,operation_id,batch_id,payload_hash) VALUES(:t,:id,:b,'invalid')",
            t=b.tenant_id,
            id=new_id(),
            b=request_id,
        )


def test_catalog_paginates_more_than_200_filters_and_isolates(wards: list[Ward]) -> None:
    a, b = wards
    doc_id = new_id()
    with transaction(a.tenant_id) as db:
        run(
            db,
            "INSERT INTO documents(id,tenant_id,title) VALUES(:id,:t,'P1-CATALOG-UNIQUE')",
            id=doc_id,
            t=a.tenant_id,
        )
        run(
            db,
            "INSERT INTO document_versions(id,tenant_id,document_id,number,body,sha256,parse_status,metadata_json) SELECT gen_random_uuid(),:t,:doc,n,'Fixture',repeat('a',64),'ready','{\"document_number\":\"P1-205\",\"topic_tags\":[\"pagination\"]}'::jsonb FROM generate_series(1,205) n",
            t=a.tenant_id,
            doc=doc_id,
        )
    seen = set()
    for page in range(1, 12):
        response = a.client.get(
            f"/api/v1/admin/knowledge/documents?q=P1-CATALOG-UNIQUE&page={page}&page_size=20&status=ready&approved=false&file_type=text&effectivity=unknown"
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["total"] == 205
        ids = {r["version_id"] for r in result["items"]}
        assert not seen.intersection(ids)
        seen.update(ids)
    assert len(seen) == 205
    detail = a.client.get(f"/api/v1/admin/knowledge/documents/{doc_id}").json()
    assert detail["total"] == 205 and len(detail["versions"]) == 20 and detail["next_cursor"] == "2"
    last = a.client.get(f"/api/v1/admin/knowledge/documents/{doc_id}?page=11").json()
    assert len(last["versions"]) == 5 and last["next_cursor"] is None
    assert all("body" not in row for row in detail["versions"])
    assert a.client.get("/api/v1/admin/knowledge/documents?q=P1-205").json()["total"] == 205
    assert a.client.get("/api/v1/admin/knowledge/documents?q=pagination").json()["total"] == 205
    assert (
        a.client.get("/api/v1/admin/knowledge/documents?q=P1-CATALOG-UNIQUE&page_size=101").status_code == 422
    )
    assert b.client.get("/api/v1/admin/knowledge/documents?q=P1-CATALOG-UNIQUE").json()["total"] == 0


def test_metadata_review_diff_and_public_classification(
    wards: list[Ward], monkeypatch: pytest.MonkeyPatch
) -> None:
    from citizen_ai import retrieval

    a, b = wards
    old = upload(a, "p1-version.txt", b"First published fact P1-OLD.")
    process_ingestion(a.tenant_id, old["job_id"])
    current = upload(a, "p1-version.txt", b"Second reviewed fact P1-NEW.", document_id=old["document_id"])
    process_ingestion(a.tenant_id, current["job_id"])
    version = read_version(a, current)
    path = f"/api/v1/admin/knowledge/versions/{current['version_id']}"
    payload = {
        "revision": version["extraction_revision"],
        "source_url": "https://congbao.chinhphu.vn/",
        "issuer": "",
        "document_number": "P1-METADATA",
        "jurisdiction": "national",
        "topic_tags": ["Hộ tịch", "Hộ tịch"],
        "supersedes_version_id": old["version_id"],
        "classification": "internal",
        "allow_public_download": False,
    }
    headers = {"X-CSRF-Token": a.csrf}
    assert (
        a.client.patch(
            path + "/metadata", json={**payload, "source_url": "javascript:alert(1)"}, headers=headers
        ).status_code
        == 422
    )
    assert (
        a.client.patch(
            path + "/metadata",
            json={**payload, "supersedes_version_id": b.config["knowledge_version_ids"][0]},
            headers=headers,
        ).status_code
        == 422
    )
    assert a.client.patch(path + "/metadata", json=payload, headers=headers).status_code == 200
    version = read_version(a, current)
    assert version["metadata_json"]["issuer"] is None
    assert version["metadata_json"]["topic_tags"] == ["Hộ tịch"]
    with monkeypatch.context() as patch:
        patch.setattr(retrieval, "settings", lambda: settings().model_copy(update={"ai_provider": "openai"}))
        with transaction(a.tenant_id) as db, pytest.raises(AppError, match="DATA_POLICY_BLOCKED"):
            retrieval.retrieve(
                db,
                "Internal fixture must never leave",
                {**a.config, "knowledge_version_ids": [current["version_id"]]},
                public=False,
            )
    assert not a.post(
        f"/admin/knowledge/versions/{current['version_id']}/approve-public", {"confirm_public": True}
    ).is_success
    payload.update(revision=version["extraction_revision"], classification="public")
    assert a.client.patch(path + "/metadata", json=payload, headers=headers).status_code == 200
    version = read_version(a, current)
    review = {
        "revision": version["extraction_revision"],
        "selected_section_ids": [s["id"] for s in version["sections"]],
        "edits": [{"section_id": version["sections"][0]["id"], "text": "Reviewed correction P1-CORRECT."}],
        "acknowledge_warnings": True,
    }
    assert a.client.post(path + "/review", json=review, headers=headers).status_code == 200
    assert a.client.post(path + "/review", json=review, headers=headers).status_code == 409
    result = a.client.get(path + "/diff", params={"against": old["version_id"]})
    assert result.status_code == 200, result.text
    assert "+Reviewed correction P1-CORRECT." in result.json()["diff"]
    assert "-First published fact P1-OLD." in result.json()["diff"]
    assert b.client.get(path + "/diff", params={"against": old["version_id"]}).status_code == 404
    current_revision = read_version(a, current)["extraction_revision"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        concurrent = list(
            pool.map(
                lambda _: a.client.post(
                    path + "/review", json={**review, "revision": current_revision}, headers=headers
                ),
                range(2),
            )
        )
    assert sorted(r.status_code for r in concurrent) == [200, 409]
    assert (
        a.post(
            f"/admin/knowledge/versions/{current['version_id']}/approve-public", {"confirm_public": True}
        ).status_code
        == 200
    )
    a.publish({**a.config, "knowledge_version_ids": [current["version_id"]]})
    version = read_version(a, current)
    assert version["approved_at"] is not None
    assert (
        a.client.post(
            path + "/review", json={**review, "revision": version["extraction_revision"]}, headers=headers
        ).status_code
        == 409
    )
    assert (
        a.client.patch(
            path + "/metadata", json={**payload, "revision": version["extraction_revision"]}, headers=headers
        ).status_code
        == 409
    )
    a.publish(a.config)


def test_orphan_sweep_grace_dry_run_and_tenant_boundary(wards: list[Ward]) -> None:
    a, b = wards
    key_a = f"tenant/{a.tenant_id}/documents/{new_id()}/original.txt"
    key_b = f"tenant/{b.tenant_id}/documents/{new_id()}/original.txt"
    put_private(key_a, b"Orphan fixture A", "text/plain")
    put_private(key_b, b"Orphan fixture B", "text/plain")
    linked = upload(a, "protected.txt", b"Active upload must survive cleanup.")
    with transaction(a.tenant_id) as db:
        protected = one(db, "SELECT object_key FROM document_versions WHERE id=:id", id=linked["version_id"])[
            "object_key"
        ]
    assert key_a not in sweep_orphans(a.tenant_id)["candidates"]
    future = datetime.now(UTC) + timedelta(hours=25)
    preview = sweep_orphans(a.tenant_id, as_of=future, maximum=10000)
    assert key_a in preview["candidates"] and protected not in preview["candidates"]
    assert get_private(key_a) == b"Orphan fixture A"
    result = sweep_orphans(a.tenant_id, apply=True, as_of=future, maximum=10000)
    assert key_a in result["deleted"] and key_b not in result["deleted"]
    assert get_private(protected) and get_private(key_b)
    assert not sweep_orphans(a.tenant_id, apply=True, as_of=future)["deleted"]
    with pytest.raises(ValueError):
        sweep_orphans(a.tenant_id, grace_hours=0)


def test_stale_parse_cannot_resurrect_after_concurrent_revoke_and_purge(
    wards: list[Ward], monkeypatch: pytest.MonkeyPatch
) -> None:
    from citizen_ai.ingestion import pipeline

    a = wards[0]
    waiting, release = threading.Event(), threading.Event()
    original = pipeline.httpx.Client

    class BarrierClient(original):
        def post(self, *args, **kwargs):
            response = super().post(*args, **kwargs)
            if threading.current_thread().name == "p1-stale":
                waiting.set()
                assert release.wait(30)
            return response

    with monkeypatch.context() as patch:
        patch.setattr(pipeline, "enqueue", lambda *args: None)
        item = upload(a, "stale.txt", b"Old worker must not resurrect this fixture.")
    monkeypatch.setattr(pipeline.httpx, "Client", BarrierClient)
    worker = threading.Thread(target=process_ingestion, args=(a.tenant_id, item["job_id"]), name="p1-stale")
    worker.start()
    try:
        assert waiting.wait(30)
        deletion = a.post(
            f"/admin/knowledge/documents/{item['document_id']}/delete-request",
            {"reason": "Concurrent fixture revocation"},
        )
        assert deletion.status_code == 202
        process_purge(a.tenant_id, deletion.json()["job_id"])
    finally:
        release.set()
        worker.join(30)
    assert not worker.is_alive()
    assert read_version(a, item)["parse_status"] == "purged"
    with transaction(a.tenant_id) as db:
        assert not many(db, "SELECT id FROM document_sections WHERE version_id=:v", v=item["version_id"])
        receipt = one(
            db,
            "SELECT result_json FROM upload_receipts WHERE result_json->>'version_id'=:v",
            v=item["version_id"],
        )
        assert receipt["result_json"]["state"] == "purged"
        assert receipt["result_json"]["filename"] == ""


def kill_at_barrier(code: str) -> None:
    with tempfile.TemporaryDirectory() as directory:
        marker = Path(directory) / "barrier"
        process = subprocess.Popen(
            [sys.executable, "-c", code],
            env={**os.environ, "P1_BARRIER": str(marker)},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 90
            while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.1)
            assert marker.exists(), "Worker did not reach crash barrier"
            process.kill()
            process.wait(timeout=10)
            assert process.returncode != 0
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)


def test_hard_kill_parse_and_purge_then_recover(wards: list[Ward], monkeypatch: pytest.MonkeyPatch) -> None:
    from citizen_ai.ingestion import pipeline, router

    a = wards[0]
    # This fixture must be owned by the process we kill, not a background
    # dispatcher racing the crash barrier. Queue dispatch is covered separately.
    with monkeypatch.context() as patch:
        patch.setattr(pipeline, "enqueue", lambda *args: None)
        item = upload(a, "crash.txt", b"Real parser crash fixture P1-CRASH.")
    kill_at_barrier(f"""
import os,time
from pathlib import Path
from citizen_ai.ingestion import pipeline
class BarrierClient(pipeline.httpx.Client):
    def post(self,*args,**kwargs):
        result=super().post(*args,**kwargs)
        Path(os.environ["P1_BARRIER"]).touch()
        time.sleep(120)
        return result
pipeline.httpx.Client=BarrierClient
pipeline.process_ingestion({a.tenant_id!r},{item["job_id"]!r})
""")
    with transaction(a.tenant_id) as db:
        assert (
            one(db, "SELECT state FROM ingestion_jobs WHERE id=:id", id=item["job_id"])["state"]
            == "extracting"
        )
        run(
            db,
            "UPDATE ingestion_jobs SET lease_until=now()-interval '1 second' WHERE id=:id",
            id=item["job_id"],
        )
    process_ingestion(a.tenant_id, item["job_id"])
    assert read_version(a, item)["parse_status"] == "ready"
    with monkeypatch.context() as patch:
        patch.setattr(router, "enqueue", lambda *args: None)
        deletion = a.post(
            f"/admin/knowledge/documents/{item['document_id']}/delete-request",
            {"reason": "P1 crash fixture purge"},
        ).json()
    kill_at_barrier(f"""
import os,time
from pathlib import Path
from citizen_ai.ingestion import purge
original=purge.delete_private
def barrier(key):
    original(key)
    Path(os.environ["P1_BARRIER"]).touch()
    time.sleep(120)
purge.delete_private=barrier
purge.process_purge({a.tenant_id!r},{deletion["job_id"]!r})
""")
    with transaction(a.tenant_id) as db:
        run(
            db,
            "UPDATE deletion_jobs SET lease_until=now()-interval '1 second' WHERE id=:id",
            id=deletion["job_id"],
        )
    process_purge(a.tenant_id, deletion["job_id"])
    process_ingestion(a.tenant_id, item["job_id"])
    assert read_version(a, item)["parse_status"] == "purged"
    with transaction(a.tenant_id) as db:
        assert not many(db, "SELECT id FROM knowledge_chunks WHERE version_id=:id", id=item["version_id"])
