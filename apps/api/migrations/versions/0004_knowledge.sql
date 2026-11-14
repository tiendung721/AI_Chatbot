ALTER TABLE document_versions ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();
UPDATE document_versions SET updated_at=created_at;
ALTER TABLE document_versions ADD COLUMN supersedes_version_id uuid;
ALTER TABLE document_versions ADD CONSTRAINT supersedes_tenant_fk FOREIGN KEY(tenant_id,supersedes_version_id) REFERENCES document_versions(tenant_id,id);
ALTER TABLE document_versions ADD COLUMN approved_by uuid;
ALTER TABLE document_versions ADD COLUMN approved_at timestamptz;
ALTER TABLE document_versions ADD CONSTRAINT approval_actor_tenant_fk FOREIGN KEY(tenant_id,approved_by) REFERENCES accounts(tenant_id,id);
CREATE INDEX knowledge_version_page ON document_versions(tenant_id,updated_at DESC,id DESC);
CREATE INDEX knowledge_metadata_tags ON document_versions USING gin(metadata_json);
CREATE TABLE upload_batches (
 tenant_id uuid NOT NULL REFERENCES tenants(id), request_id uuid NOT NULL,
 actor_id uuid NOT NULL, payload_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(tenant_id,request_id),
 FOREIGN KEY(tenant_id,actor_id) REFERENCES accounts(tenant_id,id)
);
CREATE TABLE upload_receipts (
 tenant_id uuid NOT NULL, operation_id uuid NOT NULL, batch_id uuid NOT NULL, payload_hash text NOT NULL,
 result_json jsonb, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(tenant_id,operation_id),
 FOREIGN KEY(tenant_id,batch_id) REFERENCES upload_batches(tenant_id,request_id)
);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['upload_batches','upload_receipts'] LOOP
 EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
 EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
 EXECUTE format('CREATE POLICY tenant_scope ON %I USING (tenant_id = NULLIF(current_setting(''app.tenant_id'',true),'''')::uuid) WITH CHECK (tenant_id = NULLIF(current_setting(''app.tenant_id'',true),'''')::uuid)',t);
 EXECUTE format('GRANT SELECT,INSERT,UPDATE,DELETE ON %I TO citizen_runtime',t);
 END LOOP;
END $$;
