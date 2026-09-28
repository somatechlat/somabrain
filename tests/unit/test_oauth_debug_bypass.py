"""OAuth JWT auth security tests.

Verify that forged tokens are rejected even when DEBUG=True — including when the
JWKS endpoint is unreachable, which is exactly the path that must never fall
back to an unverified decode.

No bypass lives here: these are negative tests proving authentication fails
closed. Signing keys are generated per-test at runtime and never persisted.
"""

from __future__ import annotations

import json
import time
import types

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWK

from somabrain.aaas.auth.oauth import JWTAuth


def _rsa_keypair():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private, private.public_key()


def _signing_key_from_public(public_key, kid: str = "key-1"):
    jwk_dict = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    jwk_dict["kid"] = kid
    return PyJWK(jwk_dict, algorithm="RS256")


def _encode(payload: dict, private_key, kid: str = "key-1") -> str:
    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )


def _claims(**overrides) -> dict:
    now = int(time.time())
    claims = {
        "sub": "user-1",
        "email": "user@example.com",
        "aud": "eye-of-god",
        "iss": "http://keycloak.local/realms/somabrain",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return claims


@pytest.fixture
def keycloak_settings(monkeypatch):
    proxy = types.SimpleNamespace(
        DEBUG=True,
        KEYCLOAK_URL="http://keycloak.local",
        KEYCLOAK_REALM="somabrain",
        KEYCLOAK_CLIENT_ID="eye-of-god",
    )
    monkeypatch.setattr("somabrain.aaas.auth.oauth.settings", proxy)
    return proxy


def _jwks_succeeds(monkeypatch, public_key) -> None:
    signing_key = _signing_key_from_public(public_key)
    monkeypatch.setattr(
        "jwt.PyJWKClient.get_signing_key_from_jwt",
        lambda self, token: signing_key,
    )


def _jwks_unreachable(monkeypatch) -> None:
    """Simulate Keycloak/JWKS being down — the dangerous fallback path."""

    def _raise(self, token):
        raise ConnectionError("JWKS unreachable")

    monkeypatch.setattr("jwt.PyJWKClient.get_signing_key_from_jwt", _raise)


def test_valid_token_accepted(keycloak_settings, monkeypatch):
    """A properly signed token is authenticated."""
    private_key, public_key = _rsa_keypair()
    _jwks_succeeds(monkeypatch, public_key)

    result = JWTAuth().authenticate(None, _encode(_claims(), private_key))
    assert result is not None
    assert result["user_id"] == "user-1"
    assert result["email"] == "user@example.com"


def test_forged_token_rejected_even_in_debug(keycloak_settings, monkeypatch):
    """A token signed by an unknown key must be rejected even when DEBUG=True."""
    good_private, good_public = _rsa_keypair()
    attacker_private, _ = _rsa_keypair()
    _jwks_succeeds(monkeypatch, good_public)

    forged = _encode(_claims(sub="attacker", email="attacker@example.com"), attacker_private)
    result = JWTAuth().authenticate(None, forged)
    assert result is None


def test_forged_token_rejected_when_jwks_unreachable_in_debug(keycloak_settings, monkeypatch):
    """JWKS down + DEBUG=True must NOT fall back to an unverified decode.

    This is the bypass that shipped: on JWKS failure the code used to decode the
    token with ``verify_signature: False`` when DEBUG was set, so any forged JWT
    authenticated. DEBUG is not a license to skip signature verification.
    """
    attacker_private, _ = _rsa_keypair()
    _jwks_unreachable(monkeypatch)

    forged = _encode(
        _claims(sub="attacker", email="attacker@example.com"),
        attacker_private,
    )
    result = JWTAuth().authenticate(None, forged)
    assert result is None, (
        "a forged token authenticated while JWKS was unreachable in DEBUG mode — "
        "signature verification must be enforced unconditionally"
    )


def test_forged_token_rejected_when_jwks_unreachable_in_production(keycloak_settings, monkeypatch):
    """Same guarantee with DEBUG=False: unreachable JWKS fails closed."""
    attacker_private, _ = _rsa_keypair()
    keycloak_settings.DEBUG = False
    _jwks_unreachable(monkeypatch)

    forged = _encode(_claims(sub="attacker"), attacker_private)
    assert JWTAuth().authenticate(None, forged) is None


def test_no_unverified_decode_in_source():
    """The bypass must not exist anywhere in the auth module (vibe: no bypass)."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "somabrain" / "aaas" / "auth" / "oauth.py"
    text = src.read_text(encoding="utf-8")
    assert "verify_signature" not in text, (
        "unverified JWT decode found in oauth.py — signature verification must "
        "never be disabled"
    )
