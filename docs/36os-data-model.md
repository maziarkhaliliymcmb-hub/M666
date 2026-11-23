# 36OS Data Model and Update Contract

## Canonical records
- `data/36os/project.json`: project identity, boundaries and source-of-truth map.
- `goals.json`: measurable objectives and dependencies.
- `decisions.json`: decisions, proposals, deferred choices and unresolved questions.
- `conversations/`: structured conversation records; never label reconstructed summaries as verbatim transcripts.
- `agents.json`, `integrations.json`: machine-readable registries.
- `db/migrations/`: normalized runtime relational schema.
- `schemas/`: JSON Schema contracts for interoperable records.

## Stable identifiers
Use immutable IDs: `G-###` for goals, `D-###` for decisions, `AGENT-*` for agents, `INT-*` for integrations, `CONV-*` for conversations, `EV-*` for evidence, `AUD-*` for audit events.

## Decision lifecycle
`proposed -> accepted_direction -> approved_architecture -> implemented -> verified`.
Other valid states: `open_research`, `planned_not_verified`, `accepted_defer`, `rejected`, `superseded`.
A proposal is not an approval. A design decision is not evidence of a working integration.

## Update rules
1. Never silently overwrite a decision. Add a new decision and set `supersedes` when changing a prior decision.
2. Preserve source, date, status, confidence and unresolved items.
3. Every runtime mutation must create an append-only audit event.
4. Machine actors may propose changes; owner approval is required for privilege, security, external side-effect and production changes.
5. Store secrets only in managed secret stores. Git contains schemas and non-secret configuration, never tokens.
6. JSON files are version-controlled project knowledge; the relational database is runtime query/state storage. Do not treat Git as a transactional live database.

## Interoperability
- UTF-8 JSON is the canonical exchange format.
- JSON Schema validates records before ingestion.
- SQL migration defines normalized PostgreSQL-compatible storage.
- Future API should expose versioned endpoints such as `/v1/projects/{id}/goals`, `/v1/projects/{id}/decisions`, `/v1/conversations/{id}`, and `/v1/audit-events`.
- Use pagination, stable IDs, idempotency keys, UTC timestamps and explicit schema versions.

## Conversation capture integrity
The CIE conversation file is a structured reconstruction from the prior-context material available during this update. It is not a full raw transcript. Import raw message exports later as immutable message records, retaining original timestamps and source IDs.
