-- 36OS canonical relational schema (PostgreSQL-compatible; SQLite adaptations are straightforward)
-- Git JSON files remain reviewable seed/source records; runtime state belongs in a database.
BEGIN;

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL,
  description TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS objectives (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
  title TEXT NOT NULL, description TEXT, objective_type TEXT NOT NULL,
  status TEXT NOT NULL, priority TEXT, success_criteria JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS decisions (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
  title TEXT NOT NULL, decision TEXT NOT NULL, status TEXT NOT NULL,
  rationale TEXT, source_ref TEXT, confidence TEXT,
  decided_at TIMESTAMPTZ, supersedes_id TEXT REFERENCES decisions(id),
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
  title TEXT NOT NULL, started_at TIMESTAMPTZ, ended_at TIMESTAMPTZ,
  record_type TEXT NOT NULL, completeness TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id),
  sequence_no INTEGER NOT NULL, speaker TEXT NOT NULL, body TEXT NOT NULL,
  created_at TIMESTAMPTZ, source_message_ref TEXT,
  UNIQUE(conversation_id, sequence_no)
);
CREATE TABLE IF NOT EXISTS conversation_summaries (
  id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id),
  summary TEXT NOT NULL, topic TEXT, source_refs JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS agents (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
  name TEXT NOT NULL, role TEXT NOT NULL, status TEXT NOT NULL,
  model_id TEXT, metadata JSONB NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS integrations (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
  name TEXT NOT NULL, role TEXT NOT NULL, status TEXT NOT NULL,
  endpoint_ref TEXT, metadata JSONB NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
  evidence_type TEXT NOT NULL, uri TEXT, content_hash TEXT,
  summary TEXT, trust_level TEXT, captured_at TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS decision_evidence (
  decision_id TEXT NOT NULL REFERENCES decisions(id),
  evidence_id TEXT NOT NULL REFERENCES evidence(id),
  PRIMARY KEY(decision_id, evidence_id)
);
CREATE TABLE IF NOT EXISTS objective_decisions (
  objective_id TEXT NOT NULL REFERENCES objectives(id),
  decision_id TEXT NOT NULL REFERENCES decisions(id),
  relation TEXT NOT NULL DEFAULT 'supports',
  PRIMARY KEY(objective_id, decision_id)
);
CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
  actor_id TEXT NOT NULL, actor_type TEXT NOT NULL,
  action TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT,
  request_id TEXT, correlation_id TEXT, outcome TEXT NOT NULL,
  payload_hash TEXT, occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  metadata JSONB NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS change_proposals (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
  resource_type TEXT NOT NULL, resource_id TEXT,
  proposed_by TEXT NOT NULL, rationale TEXT NOT NULL,
  patch JSONB NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
  approved_by TEXT, approved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  checksum TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_objectives_project_status ON objectives(project_id,status);
CREATE INDEX IF NOT EXISTS idx_decisions_project_status ON decisions(project_id,status);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_seq ON messages(conversation_id,sequence_no);
CREATE INDEX IF NOT EXISTS idx_audit_project_time ON audit_events(project_id,occurred_at);
CREATE INDEX IF NOT EXISTS idx_evidence_project_time ON evidence(project_id,captured_at);

-- Append-only audit: updates/deletes are intentionally prohibited for ordinary app roles.
CREATE OR REPLACE FUNCTION prevent_audit_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit_events is append-only';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS audit_events_no_update ON audit_events;
CREATE TRIGGER audit_events_no_update BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();

INSERT INTO projects(id,name,status,description)
VALUES ('36OS','36OS — Collective Intelligence Operating System','architecture_and_bootstrap',
        'Human-governed multi-agent collective intelligence ecosystem')
ON CONFLICT (id) DO NOTHING;

COMMIT;
