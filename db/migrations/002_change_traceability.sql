-- 36OS migration 002: runtime change records and traceability.
-- Apply after 001_initial_schema.sql on PostgreSQL.
BEGIN;
CREATE TABLE IF NOT EXISTS change_records (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  summary TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  goal_ids JSONB NOT NULL DEFAULT '[]',
  decision_ids JSONB NOT NULL DEFAULT '[]',
  touched_files JSONB NOT NULL DEFAULT '[]',
  risk TEXT NOT NULL,
  approval_status TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}';
CREATE INDEX IF NOT EXISTS idx_change_records_project_time
  ON change_records(project_id, created_at);
COMMIT;

-- Keep the versioned change-record ledger append-only as well.
CREATE OR REPLACE FUNCTION prevent_change_record_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'change_records is append-only';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS change_records_no_update ON change_records;
CREATE TRIGGER change_records_no_update BEFORE UPDATE OR DELETE ON change_records
FOR EACH ROW EXECUTE FUNCTION prevent_change_record_mutation();
