import secrets
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Request
from redis import Redis

from .common import AppError, digest
from .config import settings
from .db import one, run, transaction

passwords = PasswordHasher()
DUMMY_HASH = passwords.hash(secrets.token_urlsafe(32))
COOKIE_NAME = "citizen_admin"


@lru_cache
def redis_client() -> Redis:
    return Redis.from_url(
        settings().redis_url.get_secret_value(),
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )


def rate_limit(key: str, limit: int, seconds: int = 60) -> None:
    script = (
        "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n"
    )
    count = redis_client().eval(script, 1, "citizen:rate:" + digest(key), seconds)
    if int(count) > limit:
        raise AppError("RATE_LIMITED", "Bạn thao tác quá nhanh. Vui lòng thử lại sau.", 429, True)


def verify_password(stored: str, supplied: str) -> bool:
    try:
        return passwords.verify(stored, supplied)
    except (VerificationError, InvalidHashError):
        return False


@dataclass(frozen=True)
class Admin:
    tenant_id: str
    account_id: str
    session_id: str
    csrf_hash: str
    must_change_password: bool


def admin_context(request: Request, *, allow_password_change: bool = False) -> Admin:
    token = request.cookies.get(COOKIE_NAME, "")
    with transaction() as db:
        row = one(db, "SELECT * FROM resolve_admin(:hash)", hash=digest(token)) if token else None
    if not row:
        raise AppError("AUTH_REQUIRED", "Vui lòng đăng nhập lại.", 401)
    admin = Admin(
        tenant_id=str(row["tenant_id"]),
        account_id=str(row["account_id"]),
        session_id=str(row["session_id"]),
        csrf_hash=row["csrf_hash"],
        must_change_password=bool(row["must_change_password"]),
    )
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        require_origin(request)
        if not secrets.compare_digest(digest(request.headers.get("X-CSRF-Token", "")), admin.csrf_hash):
            raise AppError("FORBIDDEN", "Phiên xác nhận không hợp lệ. Hãy tải lại trang.", 403)
    if admin.must_change_password and not allow_password_change:
        raise AppError("PASSWORD_CHANGE_REQUIRED", "Vui lòng đổi mật khẩu được cấp lần đầu.", 403)
    with transaction(admin.tenant_id) as db:
        run(db, "UPDATE admin_sessions SET last_seen_at=now() WHERE id=:id", id=admin.session_id)
    return admin


def require_origin(request: Request) -> None:
    if request.headers.get("origin") != settings().app_public_url.rstrip("/"):
        raise AppError("FORBIDDEN", "Nguồn yêu cầu không được phép.", 403)


def bearer_context(request: Request) -> dict[str, Any]:
    raw = request.headers.get("authorization", "")
    if not raw.startswith("Bearer ") or len(raw) > 512:
        raise AppError("AUTH_REQUIRED", "Phiên trò chuyện không hợp lệ.", 401)
    with transaction() as db:
        row = one(db, "SELECT * FROM resolve_chat(:hash)", hash=digest(raw[7:]))
    if not row:
        raise AppError("SESSION_EXPIRED", "Phiên trò chuyện đã hết hạn. Vui lòng mở phiên mới.", 401)
    return {k: str(v) for k, v in row.items()}
