"""M0/M1 PostgreSQL schema, immutable releases, tenant RLS and narrow identity directory."""

from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).parent / "0001_schema.sql").read_text(encoding="utf-8")
    # Static, reviewed DDL only. Omitting DBAPI parameters preserves PostgreSQL format('%I')
    # and allows dollar-quoted multi-statement functions in this Alembic transaction.
    with op.get_bind().connection.driver_connection.cursor() as cursor:
        cursor.execute(sql, prepare=False)


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade is disabled. Restore or use a reviewed forward migration.")
