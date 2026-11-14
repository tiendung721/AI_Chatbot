import os
import secrets
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

from citizen_ai.ai.adapters import MockAdapter
from citizen_ai.chat import process_turn
from citizen_ai.cli import provision_admin, provision_tenant
from citizen_ai.common import canonical, new_id
from citizen_ai.config import settings
from citizen_ai.content import create_text, publish_snapshot
from citizen_ai.db import many, one, run, transaction
from citizen_ai.main import app, check_runtime
from citizen_ai.schemas import AssistantConfig, KnowledgeText

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1", reason="Set RUN_DB_TESTS=1 with real PostgreSQL/Redis"
    ),
]


@dataclass
class Ward:
    tenant_id: str
    public_key: str
    account_id: str
    client: TestClient
    csrf: str
    config: dict[str, Any]
    document_id: str

    def post(self, path: str, body: dict | None = None, **headers: str) -> Any:
        return self.client.post("/api/v1" + path, json=body, headers={"X-CSRF-Token": self.csrf, **headers})

    def save(self, config: dict[str, Any]) -> int:
        revision = self.client.get("/api/v1/admin/assistant").json()["revision"]
        result = self.client.patch(
            "/api/v1/admin/assistant/draft",
            json=config,
            headers={"X-CSRF-Token": self.csrf, "If-Match": f'"{revision}"'},
        )
        assert result.status_code == 200, result.text
        return result.json()["revision"]

    def publish(self, config: dict[str, Any]) -> str:
        revision = self.save(config)
        preflight = self.post("/admin/releases/validate", **{"If-Match": f'"{revision}"'})
        assert preflight.status_code == 200, preflight.text
        release = self.post(
            "/admin/releases",
            {"validation_id": preflight.json()["validation_id"], "reason": "Integration fixture publish"},
            **{"If-Match": f'"{revision}"'},
        )
        assert release.status_code == 201, release.text
        return release.json()["id"]

    def session(self, preview: bool = False) -> dict[str, str]:
        response = (
            self.post("/admin/assistant/preview/sessions")
            if preview
            else self.client.post(f"/api/v1/public/assistants/{self.public_key}/sessions")
        )
        assert response.status_code == 201, response.text
        return response.json()

    def ask(self, question: str, *, preview: bool = False) -> tuple[dict, dict]:
        session = self.session(preview)
        headers = {"Authorization": "Bearer " + session["session_token"]}
        created = self.client.post(
            f"/api/v1/chat/sessions/{session['session_id']}/turns",
            json={"client_request_id": new_id(), "message": question},
            headers=headers,
        )
        assert created.status_code == 202, created.text
        process_turn(self.tenant_id, created.json()["turn_id"])
        result = self.client.get(f"/api/v1/chat/turns/{created.json()['turn_id']}", headers=headers)
        assert result.status_code == 200, result.text
        return result.json(), session


@pytest.fixture(scope="module")
def wards() -> list[Ward]:
    result = []
    for letter, marker in [("a", "LAM-A-482"), ("b", "BONG-SEN-B-915")]:
        slug = "integration-" + letter + "-" + secrets.token_hex(4)
        tenant_id, public_key = provision_tenant(slug, "PHƯỜNG KIỂM THỬ " + letter)
        password = secrets.token_urlsafe(20)
        account_id = provision_admin(tenant_id, slug + "@example.invalid", password)
        client = TestClient(
            app, base_url=settings().app_public_url, headers={"Origin": settings().app_public_url}
        )
        login = client.post(
            "/api/v1/auth/admin/login", json={"email": slug + "@example.invalid", "password": password}
        )
        assert login.status_code == 200, login.text
        csrf = login.json()["csrf_token"]
        changed = client.post(
            "/api/v1/auth/admin/change-password",
            json={"current_password": password, "new_password": secrets.token_urlsafe(22)},
            headers={"X-CSRF-Token": csrf},
        )
        assert changed.status_code == 200, changed.text
        with transaction(tenant_id, privileged=True) as db:
            doc = create_text(
                db,
                tenant_id,
                account_id,
                KnowledgeText(
                    title="Thủ tục minh họa", body="DỮ LIỆU GIẢ. Thủ tục minh họa có mã thử nghiệm " + marker
                ),
            )
            run(
                db, "UPDATE document_versions SET approved_for_public=true WHERE id=:id", id=doc["version_id"]
            )
            config = AssistantConfig(knowledge_version_ids=[doc["version_id"]]).model_dump(mode="json")
            publish_snapshot(db, tenant_id, account_id, config, "Integration fixture")
        result.append(Ward(tenant_id, public_key, account_id, client, csrf, config, doc["document_id"]))
    yield result
    for ward in result:
        ward.client.close()


@pytest.fixture
def ward(wards: list[Ward]) -> Ward:
    a = wards[0]
    a.publish(a.config)
    return a


def test_runtime_role_rls_default_deny_and_connection_pool(wards: list[Ward]) -> None:
    check_runtime()
    with transaction() as db:
        assert many(db, "SELECT * FROM documents") == []
        role = one(db, "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user")
        assert role == {"rolsuper": False, "rolbypassrls": False}
    with transaction(wards[0].tenant_id) as db:
        assert all(
            str(r["tenant_id"]) == wards[0].tenant_id for r in many(db, "SELECT tenant_id FROM documents")
        )
        assert one(db, "SELECT * FROM documents WHERE id=:id", id=wards[1].document_id) is None
    with transaction(wards[1].tenant_id) as db:
        assert all(
            str(r["tenant_id"]) == wards[1].tenant_id for r in many(db, "SELECT tenant_id FROM documents")
        )
    with transaction() as db:
        assert many(db, "SELECT * FROM documents") == []
    with pytest.raises(DBAPIError), transaction(wards[0].tenant_id) as db:
        run(
            db,
            "INSERT INTO documents(id,tenant_id,title) VALUES(:id,:t,'blocked')",
            id=new_id(),
            t=wards[1].tenant_id,
        )


def test_cross_tenant_document_api_and_composite_fk(wards: list[Ward]) -> None:
    a, b = wards
    assert a.client.get("/api/v1/admin/knowledge/documents/" + b.document_id).status_code == 404
    with pytest.raises(DBAPIError), transaction(a.tenant_id) as db:
        release = one(db, "SELECT id FROM content_releases LIMIT 1")
        assert release
        run(
            db,
            "INSERT INTO release_documents(tenant_id,release_id,document_version_id) VALUES(:t,:r,:v)",
            t=a.tenant_id,
            r=release["id"],
            v=b.config["knowledge_version_ids"][0],
        )


def test_admin_schema_model_injection_and_csrf(ward: Ward) -> None:
    current = ward.client.get("/api/v1/admin/assistant").json()
    for field in ["model", "provider", "api_key", "tenant_id", "runtime_profile"]:
        response = ward.client.patch(
            "/api/v1/admin/assistant/draft",
            json={**ward.config, field: "secret-must-not-echo"},
            headers={"X-CSRF-Token": ward.csrf, "If-Match": f'"{current["revision"]}"'},
        )
        assert response.status_code == 422
        assert "secret-must-not-echo" not in response.text
    assert ward.client.patch("/api/v1/admin/assistant/draft", json=ward.config).status_code == 403
    assert ward.post("/admin/assistant/pause", **{"Origin": "https://attacker.invalid"}).status_code == 403


def test_foreign_version_cannot_enter_draft(ward: Ward, wards: list[Ward]) -> None:
    current = ward.client.get("/api/v1/admin/assistant").json()
    foreign = {**ward.config, "knowledge_version_ids": wards[1].config["knowledge_version_ids"]}
    r = ward.client.patch(
        "/api/v1/admin/assistant/draft",
        json=foreign,
        headers={"X-CSRF-Token": ward.csrf, "If-Match": f'"{current["revision"]}"'},
    )
    assert r.status_code == 403


def test_rag_and_sources_are_isolated(ward: Ward, wards: list[Ward]) -> None:
    a_result, a_session = ward.ask("Thủ tục minh họa")
    b_result, _ = wards[1].ask("Thủ tục minh họa")
    assert a_result["state"] == b_result["state"] == "completed"
    assert "LAM-A-482" in canonical(a_result) and "BONG-SEN-B-915" not in canonical(a_result)
    assert "BONG-SEN-B-915" in canonical(b_result) and "LAM-A-482" not in canonical(b_result)
    assert a_result["citations"]
    source = ward.client.get(
        a_result["citations"][0]["source_path"],
        headers={"Authorization": "Bearer " + a_session["session_token"]},
    )
    assert source.status_code == 200 and "LAM-A-482" in source.json()["body"]
    other_session = ward.session()
    denied = ward.client.get(
        a_result["citations"][0]["source_path"],
        headers={"Authorization": "Bearer " + other_session["session_token"]},
    )
    assert denied.status_code == 404


def test_draft_preview_not_public_and_unapproved_publish_blocked(ward: Ward) -> None:
    created = ward.post(
        "/admin/knowledge/texts",
        {"title": "Tinh vân thử nghiệm", "body": "Tinh vân ZETA-DRAFT-704 là dữ liệu giả chưa xuất bản."},
    ).json()
    revision = ward.save({**ward.config, "knowledge_version_ids": [created["version_id"]]})
    blocked = ward.post("/admin/releases/validate", **{"If-Match": f'"{revision}"'})
    assert blocked.status_code == 409
    preview, _ = ward.ask("Tinh vân", preview=True)
    public, _ = ward.ask("Tinh vân")
    assert "ZETA-DRAFT-704" in canonical(preview)
    assert public["answer"]["status"] == "insufficient_evidence"


def test_optimistic_revision_and_stale_validation(ward: Ward) -> None:
    revision = ward.client.get("/api/v1/admin/assistant").json()["revision"]
    checked = ward.post("/admin/releases/validate", **{"If-Match": f'"{revision}"'}).json()
    next_revision = ward.save({**ward.config, "welcome_message": "Thay đổi chưa công bố"})
    stale = ward.client.patch(
        "/api/v1/admin/assistant/draft",
        json=ward.config,
        headers={"X-CSRF-Token": ward.csrf, "If-Match": f'"{revision}"'},
    )
    assert stale.status_code == 412
    assert (
        ward.post(
            "/admin/releases",
            {"validation_id": checked["validation_id"], "reason": "Stale validation"},
            **{"If-Match": f'"{next_revision}"'},
        ).status_code
        == 409
    )


def test_releases_are_immutable_and_rollback_does_not_change_runtime(ward: Ward) -> None:
    old = ward.publish(ward.config)
    ward.publish({**ward.config, "welcome_message": "Phiên bản mới"})
    runtime = settings().runtime_fingerprint
    assert ward.post(f"/admin/releases/{old}/rollback", {"reason": "Khôi phục kiểm thử"}).status_code == 200
    assert settings().runtime_fingerprint == runtime
    with pytest.raises(DBAPIError), transaction(ward.tenant_id) as db:
        run(db, "UPDATE content_releases SET reason='tampered' WHERE id=:id", id=old)


def test_idempotency_conflict_and_single_live_turn(ward: Ward) -> None:
    session = ward.session()
    headers = {"Authorization": "Bearer " + session["session_token"]}
    path = f"/api/v1/chat/sessions/{session['session_id']}/turns"
    payload = {"client_request_id": new_id(), "message": "Thủ tục minh họa"}
    first = ward.client.post(path, json=payload, headers=headers)
    second = ward.client.post(path, json=payload, headers=headers)
    assert first.status_code == second.status_code == 202
    assert first.json()["turn_id"] == second.json()["turn_id"]
    assert (
        ward.client.post(path, json={**payload, "message": "Nội dung khác"}, headers=headers).status_code
        == 409
    )
    assert (
        ward.client.post(path, json={**payload, "client_request_id": new_id()}, headers=headers).status_code
        == 409
    )
    process_turn(ward.tenant_id, first.json()["turn_id"])
    process_turn(ward.tenant_id, first.json()["turn_id"])
    with transaction(ward.tenant_id) as db:
        assert (
            one(db, "SELECT count(*) AS n FROM usage_events WHERE turn_id=:id", id=first.json()["turn_id"])[
                "n"
            ]
            == 1
        )


def test_sse_replay_feedback_and_ownership(ward: Ward) -> None:
    result, session = ward.ask("Thủ tục minh họa")
    headers = {"Authorization": "Bearer " + session["session_token"]}
    path = f"/api/v1/chat/turns/{result['turn_id']}"
    stream = ward.client.get(path + "/events", headers=headers)
    assert stream.status_code == 200 and "event: turn.completed" in stream.text
    first_event = next(line[4:] for line in stream.text.splitlines() if line.startswith("id: "))
    replay = ward.client.get(path + "/events", headers={**headers, "Last-Event-ID": first_event})
    assert "event: turn.created" not in replay.text and "turn.completed" in replay.text
    assert (
        ward.client.post(path + "/feedback", json={"rating": "helpful"}, headers=headers).status_code == 200
    )
    other = ward.session()
    assert (
        ward.client.get(path, headers={"Authorization": "Bearer " + other["session_token"]}).status_code
        == 404
    )
    assert (
        ward.client.get(
            path + "/events", headers={"Authorization": "Bearer " + other["session_token"]}
        ).status_code
        == 404
    )


def test_revocation_during_generation_and_rollback_blocked(
    ward: Ward, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = ward.post(
        "/admin/knowledge/texts", {"title": "Cánh diều", "body": "Cánh diều REVOKED-FIXTURE"}
    ).json()
    assert (
        ward.post(
            f"/admin/knowledge/versions/{text['version_id']}/approve-public", {"confirm_public": True}
        ).status_code
        == 200
    )
    release = ward.publish({**ward.config, "knowledge_version_ids": [text["version_id"]]})
    original = MockAdapter.generate

    def revoke_then_generate(self: MockAdapter, request: Any) -> Any:
        assert (
            ward.post(
                f"/admin/knowledge/documents/{text['document_id']}/revoke",
                {"reason": "Thu hồi khi đang trả lời"},
            ).status_code
            == 200
        )
        return original(self, request)

    monkeypatch.setattr(MockAdapter, "generate", revoke_then_generate)
    result, _ = ward.ask("Cánh diều")
    assert result["state"] == "failed" and result["error_code"] == "SOURCE_REVOKED"
    assert "REVOKED-FIXTURE" not in canonical(result)
    assert (
        ward.post(
            f"/admin/releases/{release}/rollback", {"reason": "Không được phục hồi nguồn đã thu hồi"}
        ).status_code
        == 409
    )


def test_old_result_source_and_sse_are_redacted_after_revocation(ward: Ward) -> None:
    text = ward.post(
        "/admin/knowledge/texts", {"title": "Bạch dương", "body": "Bạch dương PURGE-OLD-ANSWER"}
    ).json()
    ward.post(f"/admin/knowledge/versions/{text['version_id']}/approve-public", {"confirm_public": True})
    ward.publish({**ward.config, "knowledge_version_ids": [text["version_id"]]})
    result, session = ward.ask("Bạch dương")
    assert "PURGE-OLD-ANSWER" in canonical(result)
    ward.post(f"/admin/knowledge/documents/{text['document_id']}/revoke", {"reason": "Thu hồi nguồn cũ"})
    headers = {"Authorization": "Bearer " + session["session_token"]}
    path = f"/api/v1/chat/turns/{result['turn_id']}"
    assert "PURGE-OLD-ANSWER" not in ward.client.get(path, headers=headers).text
    assert "PURGE-OLD-ANSWER" not in ward.client.get(path + "/events", headers=headers).text
    assert ward.client.get(result["citations"][0]["source_path"], headers=headers).status_code == 404


def test_no_technical_metadata_in_admin_public_and_errors(ward: Ward) -> None:
    paths = [
        "/admin/assistant",
        "/admin/dashboard",
        "/admin/releases",
        "/admin/audit",
        "/public/assistants/" + ward.public_key,
    ]
    forbidden = {
        "model",
        "provider",
        "api_key",
        "runtime_fingerprint",
        "password_hash",
        "token_hash",
        "database_url",
    }

    def keys(value: Any) -> set[str]:
        if isinstance(value, dict):
            return set(value) | set().union(*(keys(v) for v in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(v) for v in value))
        return set()

    for path in paths:
        response = ward.client.get("/api/v1" + path)
        assert response.status_code == 200
        assert not (keys(response.json()) & forbidden)


def test_preview_token_stops_working_after_admin_logout() -> None:
    tenant_id, public_key = provision_tenant(
        "integration-preview-" + secrets.token_hex(5), "PHƯỜNG KIỂM THỬ THU HỒI PHIÊN"
    )
    password = secrets.token_urlsafe(20)
    email = public_key + "@example.invalid"
    provision_admin(tenant_id, email, password)
    with TestClient(
        app, base_url=settings().app_public_url, headers={"Origin": settings().app_public_url}
    ) as client:
        login = client.post("/api/v1/auth/admin/login", json={"email": email, "password": password})
        csrf = login.json()["csrf_token"]
        headers = {"X-CSRF-Token": csrf}
        assert (
            client.post(
                "/api/v1/auth/admin/change-password",
                json={"current_password": password, "new_password": secrets.token_urlsafe(22)},
                headers=headers,
            ).status_code
            == 200
        )
        preview = client.post("/api/v1/admin/assistant/preview/sessions", headers=headers).json()
        bearer = {"Authorization": "Bearer " + preview["session_token"]}
        path = f"/api/v1/chat/sessions/{preview['session_id']}/turns"
        queued = client.post(
            path, json={"client_request_id": new_id(), "message": "Câu hỏi thử nghiệm"}, headers=bearer
        )
        assert queued.status_code == 202
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
        assert (
            client.post(
                path, json={"client_request_id": new_id(), "message": "Không còn quyền"}, headers=bearer
            ).status_code
            == 401
        )
        process_turn(tenant_id, queued.json()["turn_id"])
        with transaction(tenant_id) as db:
            row = one(
                db, "SELECT state,result_json FROM chat_turns WHERE id=:id", id=queued.json()["turn_id"]
            )
            assert row and row["state"] == "failed" and row["result_json"] is None
