"""36OS runtime persistence: SQLAlchemy models, sessions, seed loader and audit store."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def normalize_database_url(value: str) -> str:
    """Use the installed psycopg 3 driver for standard PostgreSQL URLs."""
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://"):]
    return value


DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL", "sqlite:///./36os.db"))
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Goal(Base):
    __tablename__ = "objectives"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    objective_type: Mapped[str] = mapped_column(String(100), default="general")
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    priority: Mapped[str | None] = mapped_column(String(40))
    success_criteria: Mapped[list] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    source_ref: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(String(30))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("decisions.id"))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class ChangeRecord(Base):
    __tablename__ = "change_records"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(200), nullable=False)
    goal_ids: Mapped[list] = mapped_column(JSON, default=list)
    decision_ids: Mapped[list] = mapped_column(JSON, default=list)
    touched_files: Mapped[list] = mapped_column(JSON, default=list)
    risk: Mapped[str] = mapped_column(String(30), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(50), nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(200), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(200))
    request_id: Mapped[str | None] = mapped_column(String(200))
    correlation_id: Mapped[str | None] = mapped_column(String(200))
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_hash: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


def _install_append_only_guards() -> None:
    """Protect audit and change ledgers at the database layer."""
    if engine.dialect.name == "postgresql":
        function_sql = """
        CREATE OR REPLACE FUNCTION prevent_36os_ledger_mutation() RETURNS trigger AS $
        BEGIN
          RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $ LANGUAGE plpgsql
        """
        with engine.begin() as connection:
            connection.exec_driver_sql(function_sql)
            for table in ("audit_events", "change_records"):
                trigger = f"{table}_append_only_guard"
                connection.exec_driver_sql(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
                connection.exec_driver_sql(
                    f"CREATE TRIGGER {trigger} BEFORE UPDATE OR DELETE ON {table} "
                    "FOR EACH ROW EXECUTE FUNCTION prevent_36os_ledger_mutation()"
                )
    elif engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            for table in ("audit_events", "change_records"):
                for operation in ("UPDATE", "DELETE"):
                    trigger = f"{table}_{operation.lower()}_append_only_guard"
                    connection.exec_driver_sql(
                        f"CREATE TRIGGER IF NOT EXISTS {trigger} BEFORE {operation} ON {table} "
                        f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END"
                    )


def init_database() -> None:
    Base.metadata.create_all(engine)
    _install_append_only_guards()
    seed_canonical_records()


def _read_json(relative_path: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


def seed_canonical_records() -> None:
    """Insert missing canonical records only; never overwrite runtime state."""
    with SessionLocal() as session:
        if session.get(Project, "36OS") is None:
            project = _read_json("data/36os/project.json")
            session.add(Project(id="36OS", name=project["name"], status=project["status"],
                                description=project.get("purpose")))
        goals = _read_json("data/36os/goals.json").get("goals", [])
        decisions = _read_json("data/36os/decisions.json").get("decisions", [])
        for item in goals:
            if session.get(Goal, item["id"]) is None:
                session.add(Goal(
                    id=item["id"], project_id="36OS", title=item["title"],
                    description=item.get("description"), objective_type=item.get("type", "general"),
                    status=item.get("status", "planned"), priority=item.get("priority"),
                    success_criteria=item.get("success_criteria", []),
                    metadata_json={k:v for k,v in item.items() if k not in {
                        "id","title","description","type","status","priority","success_criteria"}}
                ))
        for item in decisions:
            if session.get(Decision, item["id"]) is None:
                session.add(Decision(
                    id=item["id"], project_id="36OS", title=item["title"],
                    decision=item["decision"], status=item["status"],
                    rationale=item.get("rationale"), source_ref=item.get("source"),
                    confidence=item.get("confidence"),
                    metadata_json={k:v for k,v in item.items() if k not in {
                        "id","title","decision","status","rationale","source","confidence","date"}}
                ))
        change_dir = PROJECT_ROOT / "data/36os/change-records"
        if change_dir.exists():
            for path in sorted(change_dir.glob("*.json")):
                item = json.loads(path.read_text(encoding="utf-8"))
                if session.get(ChangeRecord, item["change_id"]) is None:
                    actor = item.get("actor", {})
                    notes = item.get("notes", {})
                    if not isinstance(notes, dict):
                        notes = {"notes": notes}
                    session.add(ChangeRecord(
                        id=item["change_id"], project_id="36OS", summary=item["summary"],
                        actor_id=actor.get("id", "unknown"), goal_ids=item.get("goal_ids", []),
                        decision_ids=item.get("decision_ids", []), touched_files=item.get("touched_files", []),
                        risk=item.get("risk", "unknown"),
                        approval_status=item.get("approval_status", "pending"),
                        metadata_json={"source_file": str(path.relative_to(PROJECT_ROOT)), **notes}
                    ))
        session.commit()


def write_audit_event(*, actor_id: str, actor_type: str, action: str,
                      resource_type: str, resource_id: str | None,
                      request_id: str | None, correlation_id: str | None,
                      outcome: str, payload_hash: str | None,
                      metadata: dict | None = None) -> None:
    try:
        with SessionLocal() as session:
            session.add(AuditEvent(
                project_id="36OS", actor_id=actor_id, actor_type=actor_type,
                action=action, resource_type=resource_type, resource_id=resource_id,
                request_id=request_id, correlation_id=correlation_id,
                outcome=outcome, payload_hash=payload_hash, metadata_json=metadata or {}
            ))
            session.commit()
    except Exception:
        # Never hide an API response because audit storage is unavailable.
        # Production deployments must alert and fail closed for privileged writes.
        if os.getenv("AUDIT_FAIL_CLOSED", "false").lower() == "true":
            raise


def list_goals(session):
    return list(session.scalars(select(Goal).order_by(Goal.id)))


def list_decisions(session):
    return list(session.scalars(select(Decision).order_by(Decision.id)))
