"""Bearer authentication — fail-closed rejection tests.

SomaBrain's authentication boundary is a pre-shared bearer token whose value
lives in Vault (VIBE Rule 164) and is read into ``SOMABRAIN_MEMORY_HTTP_TOKEN``.
These are negative tests proving a wrong, empty, or missing credential is
rejected — authentication must fail closed, including when the expected token
is not configured.

No bypass lives here: no token is ever fabricated to make a call succeed.
Signing is not involved; the property under test is constant rejection of any
credential that is not exactly the configured one.
"""

from __future__ import annotations

import pytest
from django.test import RequestFactory, override_settings

from somabrain.api.standalone_auth import StandaloneAPIKeyAuth


def _request(authorization: str | None = None):
    rf = RequestFactory()
    req = rf.get("/memory/recall")
    if authorization is not None:
        req.META["HTTP_AUTHORIZATION"] = authorization
    return req


@pytest.fixture
def auth():
    return StandaloneAPIKeyAuth()


@override_settings(SOMABRAIN_MEMORY_HTTP_TOKEN="real-token-from-vault")
def test_matching_token_authenticates(auth):
    """The exact configured token is accepted and carries the tenant partition."""
    result = auth.authenticate(_request(), "real-token-from-vault")
    assert result is not None
    assert result["tenant_id"]
    assert "memory:read" in result["scopes"]


@override_settings(SOMABRAIN_MEMORY_HTTP_TOKEN="real-token-from-vault")
def test_wrong_token_is_rejected(auth):
    """A different token must never authenticate."""
    assert auth.authenticate(_request(), "not-the-token") is None


@override_settings(SOMABRAIN_MEMORY_HTTP_TOKEN="real-token-from-vault")
def test_empty_token_is_rejected(auth):
    """An empty bearer value must never authenticate."""
    assert auth.authenticate(_request(), "") is None


@override_settings(SOMABRAIN_MEMORY_HTTP_TOKEN="")
def test_unconfigured_token_fails_closed(auth):
    """With no expected token configured, nothing authenticates.

    This is the critical case: a missing Vault secret must not open the gate.
    """
    assert auth.authenticate(_request(), "anything") is None
    assert auth.authenticate(_request(), "") is None


@override_settings(SOMABRAIN_MEMORY_HTTP_TOKEN="real-token-from-vault")
def test_missing_authorization_header_is_rejected(auth):
    """A request with no Authorization header cannot present a credential."""
    assert auth.authenticate(_request(), None) is None
