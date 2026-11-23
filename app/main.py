from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from starlette.responses import Response
from sqlalchemy import text

from app.database import engine, init_database, write_audit_event
from app.knowledge import router as knowledge_router
from app.security.dependencies import get_trusted_model
from app.security.trusted_models import TrustedModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield

app = FastAPI(
    title="Collective Intelligence Engine",
    version="0.3.1",
    description="A human-governed, evidence-based multi-agent decision system.",
    lifespan=lifespan,
)
app.include_router(knowledge_router)


@app.middleware("http")
async def universal_mutation_audit(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    mutating = request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}
    response: Response | None = None
    outcome = "error"
    try:
        response = await call_next(request)
        outcome = "success" if response.status_code < 400 else "rejected"
        return response
    finally:
        if mutating:
            write_audit_event(
                actor_id=getattr(request.state, "actor_id", "unauthenticated"),
                actor_type=getattr(request.state, "actor_type", "unknown"),
                action=request.method.upper(),
                resource_type=request.url.path.split("/")[2] if len(request.url.path.split("/")) > 2 else "unknown",
                resource_id=None,
                request_id=request_id,
                correlation_id=request.headers.get("x-correlation-id"),
                outcome=outcome,
                payload_hash=None,
                metadata={"path":request.url.path,"status_code":response.status_code if response else 500}
            )


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"service":"collective-intelligence-engine","version":app.version,"status":"running"}


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    # Check an actual round-trip to the configured persistent database.
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status":"ok","database":"connected"}


@app.get("/v1/agents/identity", tags=["trusted-models"])
async def trusted_model_identity(model: TrustedModel = Depends(get_trusted_model)) -> dict[str, object]:
    return {"model_id":model.model_id,"scopes":sorted(model.scopes)}
