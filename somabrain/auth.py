"""
Authentication Module for SomaBrain.

Extends bearer token checks with optional JWT validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import jwt
from fastapi import HTTPException, Request
from jwt.exceptions import PyJWTError
import os

from .config import Config

try:  # optional: legacy deployments may not ship shared settings yet
    from common.config.settings import settings as shared_settings
except Exception:  # pragma: no cover - backwards compatibility
    shared_settings = None  # type: ignore

_JWT_PUBLIC_CACHE: Optional[str] = None
_TRUE_VALUES = ("1", "true", "yes", "on")


def _auth_disabled() -> bool:
    if shared_settings is not None:
        try:
            return bool(getattr(shared_settings, "disable_auth", False))
        except Exception:
            return False
    env_flag = os.getenv("SOMABRAIN_DISABLE_AUTH")
    if env_flag is not None:
        try:
            return env_flag.strip().lower() in _TRUE_VALUES
        except Exception:
            return False
    return False


def _get_jwt_key(cfg: Config) -> Optional[str]:
    global _JWT_PUBLIC_CACHE
    if cfg.jwt_public_key_path:
        if _JWT_PUBLIC_CACHE is None:
            try:
                _JWT_PUBLIC_CACHE = Path(cfg.jwt_public_key_path).read_text(
                    encoding="utf-8"
                )
            except Exception:
                return None
        return _JWT_PUBLIC_CACHE
    if cfg.jwt_secret:
        return cfg.jwt_secret
    return None


def _jwt_algorithms(cfg: Config) -> list[str]:
    if cfg.jwt_public_key_path:
        return ["RS256", "RS384", "RS512"]
    return ["HS256", "HS384", "HS512"]


def require_auth(request: Request, cfg: Config) -> None:
    """Validate authentication for API requests."""
    # Allow tests/dev to disable auth via env or consolidated settings.
    if _auth_disabled():
        return
    auth = request.headers.get("Authorization", "")

    jwt_key = _get_jwt_key(cfg)
    if jwt_key:
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token = auth.split(" ", 1)[1].strip()
        options = {"verify_aud": bool(cfg.jwt_audience)}
        kwargs = {}
        if cfg.jwt_audience:
            kwargs["audience"] = cfg.jwt_audience
        if cfg.jwt_issuer:
            kwargs["issuer"] = cfg.jwt_issuer
        try:
            jwt.decode(
                token,
                jwt_key,
                algorithms=_jwt_algorithms(cfg),
                options=options,
                **kwargs,
            )
        except PyJWTError as exc:
            raise HTTPException(status_code=403, detail="invalid token") from exc
        return

    if cfg.api_token:
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token = auth.split(" ", 1)[1].strip()
        if token != cfg.api_token:
            raise HTTPException(status_code=403, detail="invalid token")
        return

    if cfg.auth_required:
        if not auth.startswith("Bearer ") or not auth.split(" ", 1)[1].strip():
            raise HTTPException(status_code=401, detail="missing bearer token")


def require_admin_auth(request: Request, cfg: Config) -> None:
    # Allow tests/dev to disable admin auth as well
    if _auth_disabled():
        return
    if not cfg.api_token:
        return
    token_header = request.headers.get("Authorization", "")
    if not token_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = token_header.split(" ", 1)[1].strip()
    if token != cfg.api_token:
        raise HTTPException(status_code=403, detail="invalid admin token")
