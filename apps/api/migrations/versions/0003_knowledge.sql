ALTER TABLE documents ADD COLUMN purged_at timestamptz;
ALTER TABLE document_versions DROP CONSTRAINT document_versions_parse_status_check;
ALTER TABLE document_versions ADD CONSTRAINT version_state CHECK(parse_status IN ('uploaded','scanning','extracting','needs_review','indexing','ready','quarantined','failed','cancelled','purged'));
ALTER TABLE document_versions ADD COLUMN object_key text;
ALTER TABLE document_versions ADD COLUMN original_filename text;
ALTER TABLE document_versions ADD COLUMN mime_type text;
ALTER TABLE document_versions ADD COLUMN byte_size bigint CHECK(byte_size>=0);
ALTER TABLE document_versions ADD COLUMN scan_status text NOT NULL DEFAULT 'not_required' CHECK(scan_status IN ('not_required','pending','clean','infected','error'));
ALTER TABLE document_versions ADD COLUMN extraction_revision integer NOT NULL DEFAULT 0;
ALTER TABLE document_versions ADD COLUMN metadata_json jsonb NOT NULL DEFAULT '{}';
ALTER TABLE document_versions ADD COLUMN purged_at timestamptz;
CREATE TABLE document_sections (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, version_id uuid NOT NULL, ordinal integer NOT NULL,
 locator jsonb NOT NULL, body text NOT NULL, review_text text, selected boolean NOT NULL DEFAULT true,
 warnings jsonb NOT NULL DEFAULT '[]', hidden boolean NOT NULL DEFAULT false,
 UNIQUE(tenant_id,id), UNIQUE(tenant_id,version_id,ordinal),
 FOREIGN KEY(tenant_id,version_id) REFERENCES document_versions(tenant_id,id)
);
ALTER TABLE knowledge_chunks ADD COLUMN section_id uuid;
ALTER TABLE knowledge_chunks ADD COLUMN locator jsonb;
ALTER TABLE knowledge_chunks ADD CONSTRAINT chunk_section_tenant_fk FOREIGN KEY(tenant_id,section_id) REFERENCES document_sections(tenant_id,id) ON DELETE SET NULL (section_id);
CREATE TABLE extraction_reviews (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, version_id uuid NOT NULL, revision integer NOT NULL,
 actor_id uuid NOT NULL, review_json jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,version_id,revision),
 FOREIGN KEY(tenant_id,version_id) REFERENCES document_versions(tenant_id,id),
 FOREIGN KEY(tenant_id,actor_id) REFERENCES accounts(tenant_id,id)
);
CREATE TABLE ingestion_jobs (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, version_id uuid NOT NULL, created_by uuid NOT NULL,
 state text NOT NULL DEFAULT 'uploaded' CHECK(state IN ('uploaded','scanning','extracting','needs_review','indexing','ready','quarantined','failed','cancelled')),
 progress integer NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
 error_code text, attempts integer NOT NULL DEFAULT 0, claim_id uuid, lease_until timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,id), UNIQUE(tenant_id,version_id),
 FOREIGN KEY(tenant_id,version_id) REFERENCES document_versions(tenant_id,id),
 FOREIGN KEY(tenant_id,created_by) REFERENCES accounts(tenant_id,id)
);
CREATE TABLE deletion_jobs (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL, document_id uuid NOT NULL, created_by uuid NOT NULL,
 state text NOT NULL DEFAULT 'queued' CHECK(state IN ('queued','executing','completed','failed')),
 error_code text, claim_id uuid, lease_until timestamptz, attempts integer NOT NULL DEFAULT 0,
 created_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz,
 UNIQUE(tenant_id,id), UNIQUE(tenant_id,document_id),
 FOREIGN KEY(tenant_id,document_id) REFERENCES documents(tenant_id,id),
 FOREIGN KEY(tenant_id,created_by) REFERENCES accounts(tenant_id,id)
);
CREATE TABLE knowledge_outbox (
 id uuid PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenants(id), kind text NOT NULL CHECK(kind IN ('ingestion','purge')),
 target_id uuid NOT NULL, last_dispatched_at timestamptz, attempts integer NOT NULL DEFAULT 0,
 created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(tenant_id,kind,target_id)
);
CREATE TABLE embedding_profiles (
 id uuid PRIMARY KEY, fingerprint text NOT NULL UNIQUE, dimensions integer NOT NULL CHECK(dimensions BETWEEN 1 AND 4096),
 metric text NOT NULL DEFAULT 'cosine' CHECK(metric='cosine'), chunker_version text NOT NULL DEFAULT 'm2-chunker-v1',
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE chunk_embeddings (
 tenant_id uuid NOT NULL, chunk_id uuid NOT NULL, embedding_profile_id uuid NOT NULL REFERENCES embedding_profiles(id),
 embedding vector NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(tenant_id,chunk_id,embedding_profile_id),
 FOREIGN KEY(tenant_id,chunk_id) REFERENCES knowledge_chunks(tenant_id,id) ON DELETE CASCADE
);
CREATE FUNCTION validate_vector_profile() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF vector_dims(NEW.embedding) <> (SELECT dimensions FROM embedding_profiles WHERE id=NEW.embedding_profile_id) THEN
 RAISE EXCEPTION 'embedding_dimensions_mismatch'; END IF;
 RETURN NEW; END $$;
CREATE TRIGGER vector_profile_dimensions BEFORE INSERT OR UPDATE ON chunk_embeddings FOR EACH ROW EXECUTE FUNCTION validate_vector_profile();
ALTER TABLE citations ALTER COLUMN chunk_id DROP NOT NULL;
ALTER TABLE citations DROP CONSTRAINT citations_tenant_id_chunk_id_fkey;
ALTER TABLE citations ADD CONSTRAINT citation_chunk_tenant_fk FOREIGN KEY(tenant_id,chunk_id) REFERENCES knowledge_chunks(tenant_id,id) ON DELETE SET NULL (chunk_id);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['document_sections','extraction_reviews','ingestion_jobs','deletion_jobs','knowledge_outbox','chunk_embeddings'] LOOP
 EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY tenant_scope ON %I USING (tenant_id = NULLIF(current_setting(''app.tenant_id'',true),'''')::uuid) WITH CHECK (tenant_id = NULLIF(current_setting(''app.tenant_id'',true),'''')::uuid)',t);
 EXECUTE format('GRANT SELECT,INSERT,UPDATE,DELETE ON %I TO citizen_runtime',t);
 END LOOP;
END $$;
GRANT SELECT ON embedding_profiles TO citizen_runtime;
REVOKE ALL ON FUNCTION validate_vector_profile() FROM PUBLIC;
-- These are extension functions, not application directory functions. Needed for exact cosine queries and dimension checks.
GRANT EXECUTE ON FUNCTION vector_dims(vector),cosine_distance(vector,vector),vector_in(cstring,oid,integer),vector_out(vector) TO citizen_runtime;
CREATE INDEX ingestion_work ON ingestion_jobs(tenant_id,state,updated_at);
CREATE INDEX deletion_work ON deletion_jobs(tenant_id,state,created_at);
