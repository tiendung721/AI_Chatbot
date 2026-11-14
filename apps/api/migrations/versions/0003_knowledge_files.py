"""Private file ingestion, review, purge and isolated vector profiles."""

from pathlib import Path

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).parent / "0003_knowledge.sql").read_text(encoding="utf-8")
    with op.get_bind().connection.driver_connection.cursor() as cursor:
        cursor.execute(sql, prepare=False)


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade disabled; use a reviewed forward migration.")
