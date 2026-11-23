# 36OS Database-First Development and Universal Change Traceability

Status: owner-approved architectural rule (D-013); implementation is partially active.

## Mandatory development sequence
1. Read `project.json`, relevant goals, decisions, policies and schemas before changing a subsystem.
2. Identify the goal(s) and decision(s) that authorize or motivate the change. If none exists, propose and record a new goal/decision before implementation.
3. Define/update data and API contracts before integrating a new module or provider.
4. Implement the change and tests.
5. Add one or more Change Records under `data/36os/change-records/`, listing every changed path (except the record files themselves), actor, rationale, goal IDs, decision IDs, risk and approval state.
6. CI verifies record completeness and known references.
7. Merge only after governance and test checks pass.
8. Runtime mutating API requests are written to append-only audit_events with actor, request/correlation IDs, HTTP method/path and outcome. Request bodies are not copied into audit logs.

## Scope
This rule applies to code, database schemas and data, API contracts, architecture, docs, configuration, CI/CD, secrets policy, integrations, model/agent registries, permissions, infrastructure and deployment.

## Change record contract
See `schemas/change-record.schema.json`. IDs are immutable. Correct a past record with a new record; do not silently rewrite history.

## Runtime APIs
- `GET /v1/knowledge/goals` — `knowledge:read`
- `GET /v1/knowledge/decisions` — `knowledge:read`
- `POST /v1/knowledge/decisions` — `knowledge:write`; use a new ID and supersedes_id rather than overwriting a decision.
- `POST /v1/knowledge/goals/{id}/status` — `knowledge:write`; prior status is preserved in status_history.
- `POST /v1/change-records` — `changes:record`
- `GET /v1/audit-events` — `audit:read`

Every protected endpoint derives identity and scopes from its bearer token; caller-supplied actor IDs are not trusted.

## Runtime database
SQLAlchemy supports local SQLite and PostgreSQL via `DATABASE_URL`. Startup creates missing tables and seeds absent canonical records. Existing runtime records are not overwritten. Configure persistent PostgreSQL for cloud production; the local SQLite default is for development only.

## Limits and enforcement boundary
GitHub Actions validates changes in PRs and pushes. A failing workflow alone does not prevent a direct push to main. Repository administrators must enable branch protection/rulesets requiring `database-governance` and `test` checks and disallow direct pushes/bypass. This administrative setting has not been changed by this commit.

Audit middleware records mutating HTTP requests with actor, request/correlation IDs, HTTP method/path and outcome; request bodies are not copied into logs. The first implementation is best-effort and writes the audit event after the route completes, so it is not yet an atomic transaction with the business mutation. It does not observe manual edits made directly in a database console. Those changes require restricted database access and external database audit controls. For strict tamper resistance, apply the migration triggers and use a DB role without UPDATE/DELETE privileges on audit_events or change_records.
