import jwt
from fastapi import HTTPException
from starlette.requests import Request

from somabrain.auth import require_auth
from somabrain.config import Config


def _make_request(headers):
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }

    async def receive():
        return {"type": "http.request"}

    return Request(scope, receive)


def test_require_auth_with_jwt_secret():
    cfg = Config(
        jwt_secret="secret",
        auth_required=True,
        jwt_audience="agents",
        jwt_issuer="somabrain",
    )
    token = jwt.encode(
        {"sub": "user", "aud": "agents", "iss": "somabrain"},
        "secret",
        algorithm="HS256",
    )
    req = _make_request({"Authorization": f"Bearer {token}"})
    require_auth(req, cfg)


def test_require_auth_with_invalid_jwt():
    cfg = Config(jwt_secret="secret", auth_required=True)
    token = jwt.encode({"sub": "user"}, "wrong", algorithm="HS256")
    req = _make_request({"Authorization": f"Bearer {token}"})
    try:
        require_auth(req, cfg)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Expected HTTPException for invalid token")
