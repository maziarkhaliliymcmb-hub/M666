import hashlib

import pytest
from fastapi import HTTPException

from app.security.trusted_models import authenticate_token, require_scope


def test_approved_model_authenticates_and_receives_scopes():
    token = "test-secret-token"
    digest = hashlib.sha256(token.encode()).hexdigest()

    model = authenticate_token(
        token,
        hashes={"vendor:model-v1": digest},
        scopes={"vendor:model-v1": frozenset({"analysis:submit", "evidence:read"})},
    )

    assert model.model_id == "vendor:model-v1"
    assert model.scopes == frozenset({"analysis:submit", "evidence:read"})


def test_unapproved_model_is_denied():
    with pytest.raises(HTTPException) as error:
        authenticate_token("not-approved", hashes={}, scopes={})
    assert error.value.status_code == 401


def test_missing_scope_is_denied():
    token = "test-secret-token"
    digest = hashlib.sha256(token.encode()).hexdigest()
    model = authenticate_token(token, hashes={"model-a": digest}, scopes={"model-a": frozenset()})

    with pytest.raises(HTTPException) as error:
        require_scope(model, "analysis:submit")
    assert error.value.status_code == 403
