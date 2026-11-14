from datetime import date
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Branding(StrictModel):
    primary_color: str = Field(default="#145B86", pattern=r"^#[0-9a-fA-F]{6}$")


class Capabilities(StrictModel):
    knowledge_search: bool = True
    web_search: Literal[False] = False
    actions: Literal[False] = False
    document_analysis: Literal[False] = False
    code_interpreter: Literal[False] = False
    image_generation: Literal[False] = False
    voice_input: Literal[False] = False
    voice_output: Literal[False] = False
    custom_extensions: Literal[False] = False


class AssistantConfig(StrictModel):
    name: str = Field(default="Trợ lý thông tin phường", min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    instructions: str = Field(
        default="Trả lời lịch sự bằng tiếng Việt, dựa trên nguồn được cung cấp.", max_length=12000
    )
    welcome_message: str = Field(default="Xin chào, bạn cần hỗ trợ nội dung gì?", max_length=500)
    conversation_starters: list[str] = Field(default_factory=list, max_length=6)
    knowledge_version_ids: list[UUID] = Field(default_factory=list, max_length=200)
    capabilities: Capabilities = Field(default_factory=Capabilities)
    branding: Branding = Field(default_factory=Branding)

    @model_validator(mode="after")
    def bounded_starters(self) -> "AssistantConfig":
        if any(not s or len(s) > 160 for s in self.conversation_starters):
            raise ValueError("Câu gợi ý cần có 1–160 ký tự.")
        if len(set(self.knowledge_version_ids)) != len(self.knowledge_version_ids):
            raise ValueError("Không chọn trùng phiên bản tài liệu.")
        return self


class Login(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class PasswordChange(StrictModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(min_length=14, max_length=256)


class KnowledgeText(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=100000)
    effective_from: date | None = None
    effective_to: date | None = None

    @model_validator(mode="after")
    def valid_dates(self) -> "KnowledgeText":
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("Ngày hết hiệu lực không được trước ngày bắt đầu.")
        return self


class Approval(StrictModel):
    confirm_public: Literal[True]


class Publish(StrictModel):
    validation_id: UUID
    reason: str = Field(min_length=3, max_length=500)


class Reason(StrictModel):
    reason: str = Field(min_length=3, max_length=500)


class TurnInput(StrictModel):
    client_request_id: UUID
    message: str = Field(min_length=1, max_length=4000)
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=0)


class FeedbackInput(StrictModel):
    rating: Literal["helpful", "unhelpful"]
    comment: str = Field(default="", max_length=1000)


class AnswerBlock(StrictModel):
    text: str = Field(min_length=1, max_length=6000)
    evidence_ids: list[str] = Field(max_length=8)


class AnswerPacket(StrictModel):
    status: Literal[
        "answered",
        "needs_clarification",
        "insufficient_evidence",
        "conflicting_sources",
        "needs_login",
        "temporarily_unavailable",
    ]
    blocks: list[AnswerBlock] = Field(max_length=12)
    follow_up_question: str | None
    needs_login: bool


class AdminAssistantView(StrictModel):
    tenant_name: str
    public_key: str
    revision: int
    config: AssistantConfig
    active_release_id: UUID | None
    testing: bool


class CitationView(StrictModel):
    id: UUID
    evidence_id: str
    title: str
    section: int
    locator: dict[str, Any] | None = None
    source_path: str


class TurnView(StrictModel):
    turn_id: UUID
    state: Literal["queued", "generating", "completed", "failed", "cancelled"]
    answer: AnswerPacket | None
    citations: list[CitationView]
    error_code: str | None
    testing: bool


class SessionView(StrictModel):
    session_id: UUID
    session_token: str
    mode: Literal["public", "preview"]
