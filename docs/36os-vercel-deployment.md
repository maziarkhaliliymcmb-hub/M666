# 36OS Vercel Deployment

## Service boundary

This project deploys the 36OS Knowledge & Governance API as an independent FastAPI service.
CIE is a separate runtime and must consume canonical knowledge through the authenticated 36OS API.
Only 36OS receives the canonical Neon PostgreSQL connection string. Do not add the 36OS
DATABASE_URL to the CIE project.

## Runtime

- Framework: FastAPI
- ASGI entrypoint: `app/main.py`
- Dependencies: `requirements.txt`
- PostgreSQL driver: psycopg 3; standard `postgresql://` and `postgres://` URLs are normalized
  to the SQLAlchemy `postgresql+psycopg://` dialect.
- The health endpoint executes `SELECT 1`; `database: connected` indicates a live database round-trip.
- Application startup creates missing tables, installs append-only ledger guards, and seeds absent
  canonical goals, decisions, and change records. Existing runtime records are not overwritten.

## Vercel project

- Project: `36os-database`
- Git repository: `maziarkhaliliymcmb-hub/36OS-database`
- Production branch: `main`
- Required environment variable: `DATABASE_URL` in Development, Preview, and Production.
- Keep the value in Vercel's environment-variable store. Never copy it into Git, logs, issues, or chat.
- Preview deployment is the first release gate. Do not promote to Production until health and
  knowledge API checks pass.

## Security and integration

- The trusted-model registry is deny-by-default when `TRUSTED_MODEL_TOKEN_HASHES` and
  `TRUSTED_MODEL_SCOPES` are absent.
- Provision a distinct CIE service identity and least-privilege scopes before connecting CIE.
- CIE must not receive direct database credentials.
- Do not expose database credentials in client-side variables.
- Audit and change ledgers are append-only at the database trigger layer; production database roles
  must also be restricted from UPDATE/DELETE on those ledgers.
