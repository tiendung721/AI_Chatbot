from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from citizen_ai.ai.adapters import MockAdapter, OpenAIAdapter
from citizen_ai.ai.contracts import GenerationRequest, validate_answer
from citizen_ai.common import AppError, chunk_text, normalize, search_query
from citizen_ai.config import Settings, settings
from citizen_ai.schemas import AnswerBlock, AnswerPacket, AssistantConfig, KnowledgeText


@pytest.mark.parametrize(
    "field",
    [
        "model",
        "provider",
        "api_key",
        "base_url",
        "temperature",
        "reasoning_effort",
        "runtime_profile",
        "embedding_model",
        "tenant_id",
    ],
)
def test_admin_rejects_technical_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        AssistantConfig.model_validate({field: "forbidden"})


def test_nested_unknown_fields_and_ungranted_capability() -> None:
    with pytest.raises(ValidationError):
        AssistantConfig.model_validate({"branding": {"javascript": "alert(1)"}})
    with pytest.raises(ValidationError):
        AssistantConfig.model_validate({"capabilities": {"web_search": True}})


def test_source_validator_rejects_fabricated_or_missing_evidence() -> None:
    for ids in ([], ["E999"]):
        packet = AnswerPacket(
            status="answered",
            blocks=[AnswerBlock(text="Invented", evidence_ids=ids)],
            follow_up_question=None,
            needs_login=False,
        )
        with pytest.raises(AppError, match="INVALID_AI_ANSWER"):
            validate_answer(packet, [{"evidence_id": "E1"}])


def test_mock_is_extractive_and_explicitly_handles_no_source() -> None:
    request = GenerationRequest(
        "question", "instructions", [{"evidence_id": "E1", "text": "Dữ liệu giả có thật trong fixture"}]
    )
    result = MockAdapter().generate(request)
    assert result.answer.blocks[0].text == request.evidence[0]["text"]
    assert MockAdapter().generate(GenerationRequest("q", "", [])).answer.status == "insufficient_evidence"


def test_vietnamese_search_and_long_text_coverage() -> None:
    assert normalize("Đường ĐỘC LẬP") == "duong doc lap"
    assert search_query("Tôi muốn biết thủ tục minh họa") == "thu | tuc | minh | hoa"
    source = "a" * 7200 + "\n\n" + "Thông tin cuối cùng không được bỏ sót."
    chunks = chunk_text(source)
    assert all(len(c) <= 3000 for c in chunks)
    assert "".join(chunks).replace("\n", "") == source.replace("\n", "")


def test_metadata_dates_and_branding_are_validated() -> None:
    with pytest.raises(ValidationError):
        KnowledgeText(title="Test", body="Data", effective_from="2026-11-10", effective_to="2026-01-01")
    with pytest.raises(ValidationError):
        AssistantConfig(branding={"primary_color": "url(javascript:alert(1))"})


@pytest.mark.parametrize(
    "overrides",
    [
        {"app_env": "production"},
        {"session_secret": "changeme"},
        {"database_url": "sqlite:///db"},
        {"ai_provider": "openai", "openai_api_key": "", "openai_chat_model": ""},
    ],
)
def test_startup_fails_closed(overrides: dict[str, str]) -> None:
    values = {
        "database_url": "postgresql+psycopg://runtime@localhost/test",
        "session_secret": "x" * 40,
        **overrides,
    }
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_openai_adapter_contract_uses_server_settings_and_no_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "test-configured-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-live")
    settings.cache_clear()
    captured: dict = {}
    packet = AnswerPacket(
        status="answered",
        blocks=[AnswerBlock(text="Fixture", evidence_ids=["E1"])],
        follow_up_question=None,
        needs_login=False,
    )

    def parse(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(
            status="completed", output_parsed=packet, usage=SimpleNamespace(input_tokens=15, output_tokens=8)
        )

    monkeypatch.setattr(
        "citizen_ai.ai.adapters.OpenAI",
        lambda **kwargs: SimpleNamespace(responses=SimpleNamespace(parse=parse), close=lambda: None),
    )
    try:
        result = OpenAIAdapter().generate(
            GenerationRequest("q", "i", [{"evidence_id": "E1", "text": "Fixture"}])
        )
        assert captured["model"] == "test-configured-model"
        assert captured["store"] is False
        assert "temperature" not in captured and "reasoning" not in captured and "tools" not in captured
        assert result.input_tokens == 15 and result.output_tokens == 8
    finally:
        settings.cache_clear()
