# Adaptive Autonomy Policy v1

Status: approved architectural direction; implementation is staged and not yet operational.

## Decision

The Collective Intelligence Engine adopts **Level B — Adaptive Autonomy**.

The system may continue approved operations without the owner's live presence, evaluate its own outputs, discover tools, design improvements, and test candidate capabilities in isolated environments. It may deploy only changes that fall within an explicit, pre-approved low-risk policy.

Human ownership and authority remain non-delegable.

## Invariants

1. Default deny: unknown models, tools, actions, and scopes are denied.
2. Least privilege: each approved model and service receives only the scopes required for its task.
3. Separation of duties: the component proposing a change cannot approve its own privilege increase or production release.
4. Human approval is required for new external data access, new production integrations, scope expansion, budget increases, payments, publication, account changes, destructive actions, and security-policy changes.
5. No agent or workflow may disable owner controls, erase audit records, extract or reveal credentials, or approve itself.
6. Secrets are stored only in managed secret stores. Logs contain identifiers and outcomes, never bearer tokens or secret values.
7. Every state-changing operation must be attributable, authorized, idempotent where practical, and auditable.
8. Every autonomous deployment must have tests, a bounded rollout, health checks, and a rollback path.

## Autonomy bands

### Autonomous within existing grants
- Run scheduled jobs and read-only health checks.
- Analyze approved project data and evaluate outputs.
- Record evidence, decisions, errors, and lessons.
- Discover and document candidate tools and APIs.
- Create sandbox experiments and draft workflow/code changes.
- Open GitHub issues and pull requests within the approved repository policy.
- Retry transient failures within configured limits and route unresolved jobs to a dead-letter queue.

### Approval required
- Connect a new external service to production data.
- Grant or expand scopes, credentials, model identities, or project access.
- Publish or deploy changes outside an explicitly pre-approved low-risk release policy.
- Increase spending, quotas, or resource ceilings.
- Perform external side effects, account changes, payments, or destructive operations.
- Change security, retention, backup, or owner-control policies.

### Prohibited
- Self-approval or self-granting privileges.
- Bypassing authentication, authorization, or human approval.
- Disabling or deleting audit trails.
- Exfiltrating secrets or private data.
- Changing ownership or removing the owner's stop/revoke authority.

## Absence mode

When the owner is unavailable:
- Continue only pre-authorized, bounded jobs.
- Queue approval-required actions without attempting workarounds.
- Preserve partial results and retry metadata.
- Continue health monitoring, backups, audit logging, and safe recovery.
- Notify the owner through an approved channel when available; never assume notification delivery.
- If policy, credentials, or audit storage cannot be verified, fail closed for privileged actions.

## Evolution loop

Observe -> Evaluate -> Identify opportunity -> Research -> Propose -> Sandbox -> Test -> Policy check -> (approval if required) -> bounded release -> monitor -> rollback or retain.

The system may prepare a proposal autonomously. A proposal is not an approval, and a successful sandbox test is not authorization for production access.

## Initial implementation gates

1. Complete scope enforcement on every protected endpoint.
2. Add durable append-only audit events and revocation.
3. Add persistent job state, idempotency, bounded retries, and dead-letter handling.
4. Add CI tests for authentication, authorization, audit coverage, and failure behavior.
5. Deploy to a cloud runtime and verify health, backup, and recovery.
6. Only then enable the first read-only Activepieces MCP identity-check workflow.
7. Keep analysis submission and all external write actions disabled until their specific scopes, schemas, audit coverage, and approval gates are tested.

## Current implementation truth

The repository currently contains a FastAPI bootstrap, environment-configured trusted-model token hashes/scopes, a read-only identity endpoint, and unit tests for authentication and scope helper behavior. The registry is empty by default. Scope enforcement is not yet attached to business endpoints; persistent audit, revocation, database, scheduler, worker, cloud deployment, and Activepieces live connection are not yet verified. Do not describe the engine as autonomous or production-ready until those gates pass.
