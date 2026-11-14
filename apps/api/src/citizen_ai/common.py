import hashlib
import hmac
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .config import settings


@dataclass
class AppError(Exception):
    code: str
    message: str
    status: int = 400
    retryable: bool = False


def new_id() -> str:
    return str(uuid4())


def digest(value: str) -> str:
    return hmac.new(
        settings().session_secret.get_secret_value().encode(), value.encode(), "sha256"
    ).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return " ".join(
        re.sub(r"[^\w\s]", " ", "".join(c for c in decomposed if not unicodedata.combining(c))).split()
    )


def search_query(question: str) -> str:
    stop = set(
        "toi muon biet can la gi thi va cua cho xin hay co khong nhu the nao ve o duoc mot cac nay".split()
    )
    words = [w for w in normalize(question).split() if w not in stop and re.fullmatch(r"[a-z0-9]+", w)]
    return " | ".join(dict.fromkeys(words[:40]))


def chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    paragraphs = re.split(r"\n\s*\n", text.strip())
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        for start in range(0, len(paragraph), max_chars):
            piece = paragraph[start : start + max_chars]
            if current and len(current) + len(piece) + 2 > max_chars:
                chunks.append(current)
                current = ""
            current = f"{current}\n\n{piece}".strip()
    if current:
        chunks.append(current)
    return chunks
