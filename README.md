# Collective Intelligence Engine

A human-governed, evidence-based multi-agent decision system. Notion is the control plane and documented memory; this repository contains the executable engine.

## Development environment

This repository is configured for GitHub Codespaces using Python 3.12 and a Dev Container.

1. Open the repository on GitHub.
2. Select **Code → Codespaces → Create codespace on main**.
3. Wait for the Dev Container to finish building and installing `requirements.txt`.
4. In the Codespaces terminal, run:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Open forwarded port 8000. Check `/health` for `{"status":"ok"}` and `/docs` for interactive API documentation.

## Local development

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run tests with `pytest`.

## Current scope

This is the bootstrap foundation only. Database integration, orchestration, agent adapters, evaluation, authentication, and production deployment are not implemented yet. Provide secrets through environment variables or a secret manager; never commit credentials.


## Trusted-model access policy (v0.2)

Only models explicitly approved by the ecosystem owner may authenticate. New or unknown models are denied by default. Authentication and permissions are separate: an approved model receives only the scopes explicitly assigned to it. The initial registry is empty, so all model requests are denied until an administrator provisions credentials.

### Configure an approved model

Generate a high-entropy bearer token outside source control, then store only its SHA-256 digest in the runtime secret configuration. Example:

```bash
export MODEL_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export MODEL_TOKEN_HASH="$(python -c 'import hashlib,os; print(hashlib.sha256(os.environ["MODEL_TOKEN"].encode()).hexdigest())')"
export TRUSTED_MODEL_TOKEN_HASHES="{\"provider:model-version\":\"$MODEL_TOKEN_HASH\"}"
export TRUSTED_MODEL_SCOPES='{"provider:model-version":["analysis:submit","evidence:read"]}'
```

Keep `MODEL_TOKEN` in the approved model's secure secret store and deliver it through a secure channel. Never commit the token or hash configuration to Git. Rotate credentials when a model is revoked or a secret may have been exposed.

### Verify model identity

Send the bearer token to `GET /v1/agents/identity`. A valid approved model receives its model ID and granted scopes. Missing/invalid credentials or an unapproved model receive HTTP 401. Scope checks return HTTP 403 when an approved model requests an operation outside its grants.

### Current implementation boundary

This is an initial environment-configured allowlist, not yet a full admin console or persistent registry. It does not automatically connect external model providers, grant access to Notion/GitHub, or execute tools on a model's behalf. Provider adapters, scope enforcement on each business endpoint, audit logging, credential revocation workflows, and runtime tests remain follow-up work. The Codespaces runtime has not yet been confirmed, so tests have been added but not executed in this change.


## 36OS Database-First Development (mandatory)

The canonical project records under `data/36os/` govern implementation. Before changing code, data, architecture, documentation, configuration, integrations, permissions, or deployment, contributors must inspect the relevant goals, decisions, schemas, and policies.

Every change must include a JSON Change Record under `data/36os/change-records/` with:
- stable change ID;
- actor and date;
- concise rationale and summary;
- linked goal and decision IDs;
- exact list of changed paths;
- risk classification and approval state;
- commit/PR reference where available.

The `database-governance` GitHub Actions workflow rejects pull requests or pushes that modify files without a matching Change Record, or reference unknown goals/decisions. Enable branch protection on `main` and require both governance and test checks; otherwise a direct push can land before a failing check is reported.

Runtime knowledge is stored in the configured database (`DATABASE_URL`); canonical JSON records remain version-controlled seed/reference data. All mutating API requests are audited. Audit events are append-only at the application layer and must also be protected by database permissions/triggers in production.

### Runtime database

- Set `DATABASE_URL` to a persistent PostgreSQL URL in the deployment secret store.
- For local development, the app defaults to `sqlite:///./36os.db`.
- On startup, the app creates missing tables and seeds absent goals/decisions from canonical JSON; existing runtime records are not overwritten.
- Knowledge API endpoints require an approved model token and the corresponding `knowledge:read`, `knowledge:write`, or `audit:read` scope.
- Never commit database credentials, bearer tokens, or production data exports.

Run tests: `pytest`.
