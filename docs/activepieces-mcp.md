# Activepieces MCP Gateway — Implementation Plan

Status: implementation phase started; cloud account and live MCP connection are not yet provisioned.

## Decision

Use Activepieces Cloud as a project-scoped MCP gateway and workflow runner. Keep the Collective Intelligence Engine as the authority for model identity, scope authorization, evidence, audit records, and human approval. Notion remains the control plane and documented memory.

Official MCP behavior: Activepieces exposes an MCP server URL from Settings → MCP Server; clients authenticate through OAuth. MCP operations are scoped to the authenticated project. Custom MCP tools can be created with the MCP Tool trigger and a Reply to MCP Client action. The HTTP piece can call a fixed Engine endpoint from inside a flow.

## Trust boundary (mandatory)

1. Default deny. A new model is Pending/Denied until the ecosystem owner approves it.
2. Do not use one shared Activepieces project or one shared Engine bearer token for multiple models.
3. Provision one Activepieces project and one MCP endpoint per approved model identity (or another design only after the gateway can cryptographically prove the caller identity).
4. Bind that project's outbound Engine credential to exactly one approved Engine model_id. Store the raw credential only as an Activepieces connection/secret; store only its SHA-256 digest in the Engine runtime secret configuration.
5. The Engine must derive model_id and scopes from the validated credential. Never trust a model_id, role, scope, or approval flag supplied in MCP tool arguments.
6. Grant least-privilege scopes per model. Authentication is not authorization.
7. Do not expose arbitrary HTTP URL/method/body tools to model clients. Expose only narrow, purpose-built MCP Tool workflows with fixed Engine routes and validated input schemas.
8. Keep Activepieces Flow Management, Flow Building, Tables, and other unneeded MCP tool categories disabled for model clients. Enable only the custom MCP tools needed for the pilot.
9. Human approval remains mandatory for external side effects, publication, payments, account changes, or destructive operations.
10. Record every accepted/rejected call with request ID, authenticated model_id, project/gateway identity, scopes, timestamp, outcome, and correlation/run ID. Never log bearer tokens or secrets.

If Activepieces cannot provide a distinct project-bound identity and isolated credential per model, stop before exposing the MCP endpoint; do not fall back to a shared credential.

## Initial pilot

Pilot only one owner-approved model identity. Start with a read-only identity check, then add analysis submission after the Engine endpoints and persistent audit storage exist.

### Workflow A — engine_identity_check

- MCP Tool trigger: engine_identity_check (no caller-supplied identity or scope fields).
- HTTP action: fixed GET https://<ENGINE_PUBLIC_BASE_URL>/v1/agents/identity.
- Authentication: the dedicated bearer connection assigned to this Activepieces project.
- Reply to MCP Client: return only the Engine response (model_id, granted scopes) and a correlation ID.
- Acceptance: an approved project's token returns its bound model identity; missing, invalid, revoked, or unapproved credentials are rejected. A second model's token must not work in this project.

### Workflow B — submit_analysis (blocked until Engine API exists)

- MCP Tool trigger accepts only run_id and a structured analysis payload.
- Validate required fields and size limits in the flow.
- HTTP action calls only the fixed POST /v1/runs/{run_id}/analyses Engine route.
- Use the project's dedicated credential; do not accept credentials in tool arguments.
- Reply with accepted/rejected status and the Engine-generated analysis ID.
- Engine enforces the analysis:submit scope and writes the audit event.

## Engine prerequisites

Current backend has GET /v1/agents/identity and an environment-configured token allowlist. require_scope exists but is not yet attached to business endpoints. The registry is empty and the Codespaces runtime/tests have not been confirmed.

Before Workflow B:
- Implement persistent run/analysis/evidence records and request validation.
- Add scope-protected endpoints for create/read run, submit analysis, and submit evidence.
- Add durable append-only audit events and credential revocation.
- Add idempotency keys, payload size limits, timeouts, and safe error responses.
- Add tests for unknown model denial, wrong-project token denial, missing scope (403), duplicate request, invalid payload, and audit coverage.
- Keep execution/side-effect endpoints unavailable until human-approval gates exist.

## Cloud/mobile setup sequence

1. Owner creates an Activepieces Cloud account from Safari on iPhone.
2. Create a dedicated project for the first approved model; do not connect business apps yet.
3. In that project, open Settings → MCP Server, enable only the required custom MCP tool category, and copy the project MCP URL.
4. Create engine_identity_check using MCP Tool trigger → HTTP GET to the fixed Engine identity route → Reply to MCP Client.
5. Create a dedicated Engine token for that project outside chat; configure only its digest in Engine runtime secrets and keep the raw token in the Activepieces connection secret.
6. Connect a compatible MCP client to that project's MCP URL using the OAuth browser flow.
7. Run positive and negative identity tests before enabling any write workflow.
8. Record project ID (not secrets), MCP URL location, approved model_id, granted scopes, test evidence, and revocation procedure in the Connector Registry.

## Not yet completed

- Activepieces account/project creation.
- Public HTTPS deployment URL for the Engine.
- Project-scoped MCP server activation.
- Dedicated credential provisioning.
- MCP client OAuth connection.
- Identity smoke test.
- Engine write endpoints, persistent audit log, and end-to-end tests.

## Official references

- https://www.activepieces.com/docs/mcp/overview
- https://www.activepieces.com/pieces/mcp
- https://www.activepieces.com/pieces/http
- https://www.activepieces.com/mcp/http
