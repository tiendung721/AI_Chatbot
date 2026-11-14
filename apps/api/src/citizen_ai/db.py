from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from .config import settings


@lru_cache
def engine() -> Engine:
    return create_engine(settings().database_url.get_secret_value(), pool_pre_ping=True, hide_parameters=True)


@contextmanager
def transaction(tenant_id: str | None = None, *, privileged: bool = False) -> Iterator[Session]:
    db_engine = engine()
    if privileged:
        url = settings().migration_database_url.get_secret_value()
        if not url:
            raise RuntimeError("MIGRATION_DATABASE_URL chỉ được cấp cho migration/CLI vận hành.")
        db_engine = create_engine(url, hide_parameters=True)
    try:
        with Session(db_engine) as session, session.begin():
            if privileged and tenant_id is not None:
                # Tenant-scoped CLI work uses the runtime role too; a migration owner
                # would otherwise bypass FORCE RLS and could select another tenant.
                session.execute(text("SET LOCAL ROLE citizen_runtime"))
            if tenant_id is not None:
                session.execute(
                    text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": str(tenant_id)}
                )
            yield session
    finally:
        if privileged:
            db_engine.dispose()


def one(db: Session, sql: str, **params: Any) -> dict[str, Any] | None:
    row = db.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


def many(db: Session, sql: str, **params: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text(sql), params).mappings()]


def run(db: Session, sql: str, **params: Any) -> None:
    db.execute(text(sql), params)
