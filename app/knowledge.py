"""Versioned knowledge APIs for goals, decisions, change records and audit events."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import AuditEvent, ChangeRecord, Decision, Goal, SessionLocal, list_decisions, list_goals
from app.security.dependencies import get_trusted_model
from app.security.trusted_models import TrustedModel, require_scope

router = APIRouter(prefix="/v1", tags=["36os-knowledge"])


def get_session():
    with SessionLocal() as session:
        yield session


def require(model: TrustedModel, scope: str) -> None:
    require_scope(model, scope)


class DecisionInput(BaseModel):
    id: str = Field(pattern=r"^D-[0-9]{3,}$")
    title: str = Field(min_length=3, max_length=500)
    decision: str = Field(min_length=5)
    status: str
    rationale: str | None = None
    source: str | None = None
    confidence: str | None = None
    supersedes_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class GoalStatusInput(BaseModel):
    status: str = Field(min_length=2, max_length=80)
    rationale: str = Field(min_length=5)


class ChangeRecordInput(BaseModel):
    id: str = Field(min_length=5, max_length=120)
    summary: str = Field(min_length=10)
    goal_ids: list[str] = Field(min_length=1)
    decision_ids: list[str] = Field(min_length=1)
    touched_files: list[str] = Field(min_length=1)
    risk: str
    approval_status: str
    metadata: dict = Field(default_factory=dict)


def _decision_dict(item: Decision) -> dict:
    return {"id":item.id,"title":item.title,"decision":item.decision,"status":item.status,
            "rationale":item.rationale,"source":item.source_ref,"confidence":item.confidence,
            "supersedes_id":item.supersedes_id,"metadata":item.metadata_json or {}}


def _goal_dict(item: Goal) -> dict:
    return {"id":item.id,"title":item.title,"description":item.description,
            "type":item.objective_type,"status":item.status,"priority":item.priority,
            "success_criteria":item.success_criteria or [],"metadata":item.metadata_json or {}}


@router.get("/knowledge/goals")
def get_goals(model: TrustedModel = Depends(get_trusted_model),
              session: Session = Depends(get_session)):
    require(model, "knowledge:read")
    return {"project_id":"36OS","goals":[_goal_dict(x) for x in list_goals(session)]}


@router.get("/knowledge/decisions")
def get_decisions(model: TrustedModel = Depends(get_trusted_model),
                  session: Session = Depends(get_session)):
    require(model, "knowledge:read")
    return {"project_id":"36OS","decisions":[_decision_dict(x) for x in list_decisions(session)]}


@router.post("/knowledge/decisions", status_code=201)
def create_decision(payload: DecisionInput, request: Request,
                    model: TrustedModel = Depends(get_trusted_model),
                    session: Session = Depends(get_session)):
    require(model, "knowledge:write")
    if session.get(Decision, payload.id):
        raise HTTPException(status_code=409, detail="Decision ID already exists; create a new ID and supersede the prior decision")
    if payload.supersedes_id and not session.get(Decision, payload.supersedes_id):
        raise HTTPException(status_code=422, detail="supersedes_id does not reference an existing decision")
    item = Decision(id=payload.id, project_id="36OS", title=payload.title,
                    decision=payload.decision, status=payload.status, rationale=payload.rationale,
                    source_ref=payload.source, confidence=payload.confidence,
                    supersedes_id=payload.supersedes_id, metadata_json=payload.metadata)
    session.add(item)
    session.commit()
    return _decision_dict(item)


@router.post("/knowledge/goals/{goal_id}/status")
def update_goal_status(goal_id: str, payload: GoalStatusInput, request: Request,
                       model: TrustedModel = Depends(get_trusted_model),
                       session: Session = Depends(get_session)):
    require(model, "knowledge:write")
    item = session.get(Goal, goal_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    previous = item.status
    item.status = payload.status
    metadata = dict(item.metadata_json or {})
    history = list(metadata.get("status_history", []))
    history.append({"from":previous,"to":payload.status,"rationale":payload.rationale,
                    "actor":model.model_id,"date":date.today().isoformat()})
    metadata["status_history"] = history
    item.metadata_json = metadata
    session.commit()
    return _goal_dict(item)


@router.post("/change-records", status_code=201)
def create_change_record(payload: ChangeRecordInput, request: Request,
                         model: TrustedModel = Depends(get_trusted_model),
                         session: Session = Depends(get_session)):
    require(model, "changes:record")
    if session.get(ChangeRecord, payload.id):
        raise HTTPException(status_code=409, detail="Change record already exists")
    known_goals = {x.id for x in list_goals(session)}
    known_decisions = {x.id for x in list_decisions(session)}
    if not set(payload.goal_ids).issubset(known_goals):
        raise HTTPException(status_code=422, detail="Unknown goal ID")
    if not set(payload.decision_ids).issubset(known_decisions):
        raise HTTPException(status_code=422, detail="Unknown decision ID")
    item = ChangeRecord(id=payload.id, project_id="36OS", summary=payload.summary,
                        actor_id=model.model_id, goal_ids=payload.goal_ids,
                        decision_ids=payload.decision_ids, touched_files=payload.touched_files,
                        risk=payload.risk, approval_status=payload.approval_status,
                        metadata_json=payload.metadata)
    session.add(item)
    session.commit()
    return {"id":item.id,"status":"recorded","actor_id":item.actor_id}


@router.get("/audit-events")
def get_audit_events(model: TrustedModel = Depends(get_trusted_model),
                     limit: int = 100, session: Session = Depends(get_session)):
    require(model, "audit:read")
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    rows = session.scalars(select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(limit))
    return {"events":[{"id":x.id,"actor_id":x.actor_id,"actor_type":x.actor_type,
                       "action":x.action,"resource_type":x.resource_type,
                       "resource_id":x.resource_id,"request_id":x.request_id,
                       "correlation_id":x.correlation_id,"outcome":x.outcome,
                       "payload_hash":x.payload_hash,"occurred_at":x.occurred_at.isoformat(),
                       "metadata":x.metadata_json or {}} for x in rows]}
