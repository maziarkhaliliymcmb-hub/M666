"""Shared bearer authentication dependency for all protected API routes."""
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.security.trusted_models import TrustedModel, authenticate_token

bearer_scheme = HTTPBearer(auto_error=False)

def get_trusted_model(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> TrustedModel:
    if credentials is None or credentials.scheme.lower() != "bearer":
        request.state.actor_id = "anonymous"
        raise HTTPException(status_code=401, detail="Bearer credentials required")
    model = authenticate_token(credentials.credentials)
    request.state.actor_id = model.model_id
    request.state.actor_type = "trusted_model"
    return model
