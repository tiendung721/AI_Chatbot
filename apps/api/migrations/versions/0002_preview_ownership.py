"""Bind private Preview sessions to a live administrator session."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE admin_sessions ADD CONSTRAINT admin_session_tenant_id_unique UNIQUE(tenant_id,id)"
    )
    op.execute("ALTER TABLE chat_sessions ADD COLUMN admin_session_id uuid")
    op.execute(
        "ALTER TABLE chat_sessions ADD CONSTRAINT preview_owner_tenant_fk FOREIGN KEY(tenant_id,admin_session_id) REFERENCES admin_sessions(tenant_id,id)"
    )
    op.execute("""CREATE OR REPLACE FUNCTION resolve_chat(p_hash text) RETURNS TABLE(tenant_id uuid,session_id uuid)
        LANGUAGE sql SECURITY DEFINER SET search_path=public,pg_temp AS $$
        SELECT s.tenant_id,s.id FROM chat_sessions s WHERE s.token_hash=p_hash AND s.expires_at>now()
        AND (s.mode='public' OR EXISTS(
            SELECT 1 FROM admin_sessions adm JOIN accounts a ON (a.tenant_id,a.id)=(adm.tenant_id,adm.account_id)
            JOIN tenant_admin_memberships m ON (m.tenant_id,m.account_id)=(a.tenant_id,a.id)
            WHERE adm.id=s.admin_session_id AND adm.tenant_id=s.tenant_id AND adm.revoked_at IS NULL
            AND adm.expires_at>now() AND adm.last_seen_at>now()-interval '30 minutes' AND a.active AND m.active
        )); $$""")


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade disabled; use a reviewed forward migration.")
