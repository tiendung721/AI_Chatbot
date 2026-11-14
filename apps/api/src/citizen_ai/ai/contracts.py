from dataclasses import dataclass, field
from typing import Any, Protocol

from ..common import AppError
from ..schemas import AnswerPacket


@dataclass
class GenerationRequest:
    question: str
    instructions: str
    evidence: list[dict[str, Any]]


@dataclass
class GenerationResult:
    answer: AnswerPacket
    input_tokens: int = 0
    output_tokens: int = 0
    technical_usage: dict[str, Any] = field(default_factory=dict)


class ModelAdapter(Protocol):
    def generate(self, request: GenerationRequest) -> GenerationResult: ...


def validate_answer(packet: AnswerPacket, evidence: list[dict[str, Any]]) -> None:
    allowed = {e["evidence_id"] for e in evidence}
    if packet.status == "answered" and not packet.blocks:
        raise AppError("INVALID_AI_ANSWER", "Câu trả lời chưa đạt kiểm tra nguồn.", 502)
    for block in packet.blocks:
        if (packet.status == "answered" and not block.evidence_ids) or not set(block.evidence_ids).issubset(
            allowed
        ):
            raise AppError("INVALID_AI_ANSWER", "Câu trả lời chưa đạt kiểm tra nguồn.", 502)
