CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE tenants (
 id uuid PRIMARY KEY, slug text NOT NULL UNIQUE, display_name text NOT NULL,
 security_epoch integer NOT NULL DEFAULT 0, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE accounts (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenants(id), email text NOT NULL UNIQUE,
 password_hash text NOT NULL, active boolean NOT NULL DEFAULT true,
 must_change_password boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE (tenant_id,id)
);
CREATE TABLE tenant_admin_memberships (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenants(id), account_id uuid NOT NULL,
 active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY (tenant_id,account_id) REFERENCES accounts(tenant_id,id)
);
CREATE UNIQUE INDEX one_active_admin ON tenant_admin_memberships(tenant_id) WHERE active;
CREATE TABLE admin_sessions (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenants(id), account_id uuid NOT NULL,
 token_hash text NOT NULL UNIQUE, csrf_hash text NOT NULL, expires_at timestamptz NOT NULL,
 last_seen_at timestamptz NOT NULL DEFAULT now(), revoked_at timestamptz,
 FOREIGN KEY (tenant_id,account_id) REFERENCES accounts(tenant_id,id)
);
CREATE TABLE assistants (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenants(id), public_key text NOT NULL UNIQUE,
 active_release_id uuid, paused boolean NOT NULL DEFAULT false, UNIQUE(tenant_id,id)
);
CREATE TABLE assistant_drafts (
 tenant_id uuid NOT NULL, assistant_id uuid PRIMARY KEY, revision integer NOT NULL DEFAULT 1,
 config_json jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY (tenant_id,assistant_id) REFERENCES assistants(tenant_id,id)
);
CREATE TABLE documents (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenants(id), title text NOT NULL,
 revoked_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(tenant_id,id)
);
CREATE TABLE document_versions (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, document_id uuid NOT NULL, number integer NOT NULL,
 body text NOT NULL, sha256 text NOT NULL, parse_status text NOT NULL CHECK(parse_status IN ('ready','failed')),
 approved_for_public boolean NOT NULL DEFAULT false, effective_from date, effective_to date,
 created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(tenant_id,id), UNIQUE(tenant_id,document_id,number),
 FOREIGN KEY(tenant_id,document_id) REFERENCES documents(tenant_id,id),
 CHECK(effective_from IS NULL OR effective_to IS NULL OR effective_to >= effective_from)
);
CREATE TABLE knowledge_chunks (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, version_id uuid NOT NULL, ordinal integer NOT NULL,
 body text NOT NULL, normalized_text text NOT NULL,
 search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple',normalized_text)) STORED,
 UNIQUE(tenant_id,id), UNIQUE(tenant_id,version_id,ordinal),
 FOREIGN KEY(tenant_id,version_id) REFERENCES document_versions(tenant_id,id)
);
CREATE INDEX chunks_search ON knowledge_chunks USING gin(search_vector);
CREATE TABLE release_validations (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, assistant_id uuid NOT NULL, draft_hash text NOT NULL,
 runtime_fingerprint text NOT NULL, security_epoch integer NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(tenant_id,assistant_id) REFERENCES assistants(tenant_id,id)
);
CREATE TABLE content_releases (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, assistant_id uuid NOT NULL, sequence integer NOT NULL,
 snapshot jsonb NOT NULL, content_hash text NOT NULL, runtime_fingerprint text NOT NULL,
 created_by uuid NOT NULL, reason text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,id), UNIQUE(tenant_id,assistant_id,sequence),
 FOREIGN KEY(tenant_id,assistant_id) REFERENCES assistants(tenant_id,id),
 FOREIGN KEY(tenant_id,created_by) REFERENCES accounts(tenant_id,id)
);
ALTER TABLE assistants ADD CONSTRAINT active_release_tenant_fk
 FOREIGN KEY(tenant_id,active_release_id) REFERENCES content_releases(tenant_id,id);
CREATE TABLE release_documents (
 tenant_id uuid NOT NULL, release_id uuid NOT NULL, document_version_id uuid NOT NULL,
 PRIMARY KEY(tenant_id,release_id,document_version_id),
 FOREIGN KEY(tenant_id,release_id) REFERENCES content_releases(tenant_id,id),
 FOREIGN KEY(tenant_id,document_version_id) REFERENCES document_versions(tenant_id,id)
);
CREATE TABLE chat_sessions (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, assistant_id uuid NOT NULL, token_hash text NOT NULL UNIQUE,
 mode text NOT NULL CHECK(mode IN ('public','preview')), draft_snapshot jsonb,
 expires_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(tenant_id,id),
 FOREIGN KEY(tenant_id,assistant_id) REFERENCES assistants(tenant_id,id)
);
CREATE TABLE chat_turns (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, session_id uuid NOT NULL, client_request_id uuid NOT NULL,
 payload_hash text NOT NULL, message text NOT NULL, state text NOT NULL DEFAULT 'queued'
 CHECK(state IN ('queued','generating','completed','failed','cancelled')),
 release_id uuid, config_snapshot jsonb NOT NULL, result_json jsonb, error_code text,
 lease_until timestamptz, claim_id uuid, attempts integer NOT NULL DEFAULT 0,
 runtime_fingerprint text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,id), UNIQUE(tenant_id,session_id,client_request_id),
 FOREIGN KEY(tenant_id,session_id) REFERENCES chat_sessions(tenant_id,id),
 FOREIGN KEY(tenant_id,release_id) REFERENCES content_releases(tenant_id,id)
);
CREATE UNIQUE INDEX one_live_turn_per_session ON chat_turns(tenant_id,session_id)
 WHERE state IN ('queued','generating');
CREATE TABLE turn_events (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, turn_id uuid NOT NULL, sequence integer NOT NULL,
 kind text NOT NULL, payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,turn_id,sequence), FOREIGN KEY(tenant_id,turn_id) REFERENCES chat_turns(tenant_id,id)
);
CREATE TABLE citations (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, turn_id uuid NOT NULL, version_id uuid NOT NULL,
 chunk_id uuid NOT NULL, evidence_id text NOT NULL, UNIQUE(tenant_id,id),
 FOREIGN KEY(tenant_id,turn_id) REFERENCES chat_turns(tenant_id,id),
 FOREIGN KEY(tenant_id,version_id) REFERENCES document_versions(tenant_id,id),
 FOREIGN KEY(tenant_id,chunk_id) REFERENCES knowledge_chunks(tenant_id,id)
);
CREATE TABLE feedback (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, turn_id uuid NOT NULL, rating text NOT NULL
 CHECK(rating IN ('helpful','unhelpful')), comment text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,turn_id), FOREIGN KEY(tenant_id,turn_id) REFERENCES chat_turns(tenant_id,id)
);
CREATE TABLE outbox_events (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenants(id), turn_id uuid NOT NULL,
 last_dispatched_at timestamptz, attempts integer NOT NULL DEFAULT 0,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(tenant_id,turn_id) REFERENCES chat_turns(tenant_id,id)
);
CREATE TABLE audit_events (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenants(id), actor_id uuid,
 event_type text NOT NULL, resource_id uuid, detail jsonb NOT NULL DEFAULT '{}',
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE usage_events (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, turn_id uuid NOT NULL UNIQUE,
 input_tokens integer NOT NULL, output_tokens integer NOT NULL, cost_status text NOT NULL DEFAULT 'unpriced',
 runtime_fingerprint text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(tenant_id,turn_id) REFERENCES chat_turns(tenant_id,id)
);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['accounts','tenant_admin_memberships','admin_sessions','assistants','assistant_drafts',
 'documents','document_versions','knowledge_chunks','release_validations','content_releases','release_documents',
 'chat_sessions','chat_turns','turn_events','citations','feedback','outbox_events','audit_events','usage_events'] LOOP
 EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY tenant_scope ON %I USING (tenant_id = NULLIF(current_setting(''app.tenant_id'',true),'''')::uuid) WITH CHECK (tenant_id = NULLIF(current_setting(''app.tenant_id'',true),'''')::uuid)',t);
 END LOOP;
END $$;
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_scope ON tenants USING(id=NULLIF(current_setting('app.tenant_id',true),'')::uuid)
 WITH CHECK(id=NULLIF(current_setting('app.tenant_id',true),'')::uuid);
CREATE FUNCTION reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 RAISE EXCEPTION 'immutable_record'; END $$;
CREATE TRIGGER release_immutable BEFORE UPDATE OR DELETE ON content_releases FOR EACH ROW EXECUTE FUNCTION reject_mutation();
CREATE TRIGGER membership_immutable BEFORE UPDATE OR DELETE ON release_documents FOR EACH ROW EXECUTE FUNCTION reject_mutation();
CREATE TRIGGER audit_append_only BEFORE UPDATE OR DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION reject_mutation();

-- Exact-match identity resolution only. No caller-supplied SQL/tenant context, no content is returned.
CREATE FUNCTION resolve_login(p_email text) RETURNS TABLE(tenant_id uuid,account_id uuid,password_hash text)
 LANGUAGE sql SECURITY DEFINER SET search_path=public,pg_temp AS $$
 SELECT a.tenant_id,a.id,a.password_hash FROM accounts a JOIN tenant_admin_memberships m
 ON m.tenant_id=a.tenant_id AND m.account_id=a.id WHERE a.email=p_email AND a.active AND m.active;
$$;
CREATE FUNCTION resolve_admin(p_hash text) RETURNS TABLE(tenant_id uuid,account_id uuid,session_id uuid,csrf_hash text,must_change_password boolean)
 LANGUAGE sql SECURITY DEFINER SET search_path=public,pg_temp AS $$
 SELECT s.tenant_id,s.account_id,s.id,s.csrf_hash,a.must_change_password FROM admin_sessions s
 JOIN accounts a ON (a.tenant_id,a.id)=(s.tenant_id,s.account_id)
 JOIN tenant_admin_memberships m ON (m.tenant_id,m.account_id)=(a.tenant_id,a.id)
 WHERE s.token_hash=p_hash AND s.revoked_at IS NULL AND s.expires_at>now()
 AND s.last_seen_at>now()-interval '30 minutes' AND a.active AND m.active;
$$;
CREATE FUNCTION resolve_assistant(p_key text) RETURNS TABLE(tenant_id uuid,assistant_id uuid)
 LANGUAGE sql SECURITY DEFINER SET search_path=public,pg_temp AS $$
 SELECT a.tenant_id,a.id FROM assistants a WHERE a.public_key=p_key;
$$;
CREATE FUNCTION resolve_chat(p_hash text) RETURNS TABLE(tenant_id uuid,session_id uuid)
 LANGUAGE sql SECURITY DEFINER SET search_path=public,pg_temp AS $$
 SELECT s.tenant_id,s.id FROM chat_sessions s WHERE s.token_hash=p_hash AND s.expires_at>now();
$$;
CREATE FUNCTION worker_tenants() RETURNS TABLE(tenant_id uuid)
 LANGUAGE sql SECURITY DEFINER SET search_path=public,pg_temp AS $$ SELECT id FROM tenants; $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO citizen_runtime;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO citizen_runtime;
REVOKE ALL ON alembic_version FROM citizen_runtime;
REVOKE UPDATE,DELETE ON content_releases,release_documents,audit_events FROM citizen_runtime;
GRANT EXECUTE ON FUNCTION resolve_login(text),resolve_admin(text),resolve_assistant(text),resolve_chat(text),worker_tenants() TO citizen_runtime;
