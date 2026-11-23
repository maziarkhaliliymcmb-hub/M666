"""Trusted-model authentication and scope enforcement.

The registry is configured through environment variables. An empty registry denies
all model access by default. Raw bearer tokens are never stored in source control.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from typing import Mapping

from fastapi import HTTPException, status


@dataclass(frozen=True)
class TrustedModel:
    model_id: str
    scopes: frozenset[str]


def _load_json_env(name: str) -> dict[str, object]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} must contain valid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{name} must be a JSON object")
    return value


def load_trusted_registry() -> tuple[Mapping[str, str], Mapping[str, object]]:
    """Return model-id -> SHA-256 token digest and model-id -> scopes."""
    hashes_raw = _load_json_env("TRUSTED_MODEL_TOKEN_HASHES")
    scopes_raw = _load_json_env("TRUSTED_MODEL_SCOPES")

    hashes: dict[str, str] = {}
    for model_id, digest in hashes_raw.items():
        if not isinstance(model_id, str) or not isinstance(digest, str):
            raise RuntimeError("Trusted model IDs and token hashes must be strings")
        normalized = digest.lower().strip()
        if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
            raise RuntimeError(f"Invalid SHA-256 token hash for model {model_id!r}")
        hashes[model_id] = normalized

    scopes: dict[str, object] = {}
    for model_id, value in scopes_raw.items():
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise RuntimeError(f"Scopes for model {model_id!r} must be a list of strings")
        scopes[model_id] = frozenset(value)

    return hashes, scopes


def authenticate_token(token: str, *, hashes: Mapping[str, str] | None = None,
                       scopes: Mapping[str, object] | None = None) -> TrustedModel:
    """Authenticate a bearer token against the approved-model allowlist."""
    if not token or len(token) > 4096:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid model credentials")

    if hashes is None or scopes is None:
        loaded_hashes, loaded_scopes = load_trusted_registry()
        hashes = loaded_hashes if hashes is None else hashes
        scopes = loaded_scopes if scopes is None else scopes

    candidate = hashlib.sha256(token.encode("utf-8")).hexdigest()
    for model_id, expected_digest in hashes.items():
        if hmac.compare_digest(candidate, expected_digest):
            model_scopes = scopes.get(model_id, frozenset())
            if not isinstance(model_scopes, (set, frozenset)):
                raise RuntimeError(f"Invalid scopes for trusted model {model_id!r}")
            return TrustedModel(model_id=model_id, scopes=frozenset(model_scopes))

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Model is not approved or credentials are invalid")


def require_scope(model: TrustedModel, required_scope: str) -> None:
    if required_scope not in model.scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Trusted model lacks the required scope")
