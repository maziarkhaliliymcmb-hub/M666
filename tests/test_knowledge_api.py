import hashlib
import os
import time
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database import AuditEvent, SessionLocal, normalize_database_url
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test-36os.db"

from fastapi.testclient import TestClient
from app.main import app

TOKEN = "test-36os-token"
DIGEST = hashlib.sha256(TOKEN.encode()).hexdigest()

def test_postgresql_url_uses_psycopg3_driver():
    assert normalize_database_url("postgresql://user:pass@host/db") == "postgresql+psycopg://user:pass@host/db"
    assert normalize_database_url("postgres://user:pass@host/db") == "postgresql+psycopg://user:pass@host/db"


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["database"] == "connected"

def test_identity_requires_approved_model(monkeypatch):
    monkeypatch.setenv("TRUSTED_MODEL_TOKEN_HASHES", '{"test:model":"' + DIGEST + '"}')
    monkeypatch.setenv("TRUSTED_MODEL_SCOPES", '{"test:model":["knowledge:read"]}')
    with TestClient(app) as client:
        response = client.get("/v1/agents/identity", headers={"Authorization":f"Bearer {TOKEN}"})
        assert response.status_code == 200
        assert response.json()["model_id"] == "test:model"

def test_knowledge_endpoint_enforces_scope(monkeypatch):
    monkeypatch.setenv("TRUSTED_MODEL_TOKEN_HASHES", '{"test:model":"' + DIGEST + '"}')
    monkeypatch.setenv("TRUSTED_MODEL_SCOPES", '{"test:model":[]}')
    with TestClient(app) as client:
        response = client.get("/v1/knowledge/goals", headers={"Authorization":f"Bearer {TOKEN}"})
        assert response.status_code == 403

def test_knowledge_endpoint_returns_seeded_goals(monkeypatch):
    monkeypatch.setenv("TRUSTED_MODEL_TOKEN_HASHES", '{"test:model":"' + DIGEST + '"}')
    monkeypatch.setenv("TRUSTED_MODEL_SCOPES", '{"test:model":["knowledge:read"]}')
    with TestClient(app) as client:
        response = client.get("/v1/knowledge/goals", headers={"Authorization":f"Bearer {TOKEN}"})
        assert response.status_code == 200
        assert any(item["id"] == "G-011" for item in response.json()["goals"])

def test_mutating_knowledge_request_is_audited(monkeypatch):
    monkeypatch.setenv("TRUSTED_MODEL_TOKEN_HASHES", '{"test:model":"' + DIGEST + '"}')
    monkeypatch.setenv("TRUSTED_MODEL_SCOPES", '{"test:model":["knowledge:write","audit:read"]}')
    decision_id = "D-" + str(int(time.time() * 1000000))
    headers = {"Authorization":f"Bearer {TOKEN}"}
    with TestClient(app) as client:
        created = client.post("/v1/knowledge/decisions", headers=headers, json={
            "id":decision_id,"title":"Audit integration test",
            "decision":"This test decision verifies mutation audit recording.",
            "status":"proposed","source":"automated test","confidence":"high"
        })
        assert created.status_code == 201
        audit = client.get("/v1/audit-events", headers=headers)
        assert audit.status_code == 200
        assert any(event["action"] == "POST" and event["outcome"] == "success"
                   and event["metadata"]["path"] == "/v1/knowledge/decisions"
                   for event in audit.json()["events"])

def test_audit_ledger_is_append_only(monkeypatch):
    monkeypatch.setenv("TRUSTED_MODEL_TOKEN_HASHES", '{"test:model":"' + DIGEST + '"}')
    monkeypatch.setenv("TRUSTED_MODEL_SCOPES", '{"test:model":["knowledge:write","audit:read"]}')
    decision_id = "D-" + str(int(time.time() * 1000000))
    headers = {"Authorization":f"Bearer {TOKEN}"}
    with TestClient(app) as client:
        created = client.post("/v1/knowledge/decisions", headers=headers, json={
            "id":decision_id,"title":"Append-only audit test",
            "decision":"This decision produces an audit event for immutability testing.",
            "status":"proposed"
        })
        assert created.status_code == 201
    with SessionLocal() as session:
        event = session.scalar(select(AuditEvent).order_by(AuditEvent.occurred_at.desc()))
        assert event is not None
        event.outcome = "tampered"
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
