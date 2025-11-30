from __future__ import annotations
from pathlib import Path
from typing import Optional
import jwt
from fastapi import HTTPException, Request
from jwt.exceptions import PyJWTError
from .config import Config
from common.logging import logger

"""
Authentication Module for SomaBrain.

Extends bearer token checks with optional JWT validation.
"""





# Import the canonical settings object directly.

_JWT_PUBLIC_CACHE: Optional[str] = None
_TRUE_VALUES = ("1", "true", "yes", "on")


def _auth_disabled() -> bool:
    # Auth disable capability removed: always enforce auth in strict mode.
    return False


def _get_jwt_key(cfg: Config) -> Optional[str]:
    global _JWT_PUBLIC_CACHE
    if cfg.jwt_public_key_path:
        if _JWT_PUBLIC_CACHE is None:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                _JWT_PUBLIC_CACHE = Path(cfg.jwt_public_key_path).read_text(
                    encoding="utf-8"
                )
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
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
    # Auth always enforced; no early return.
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
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            jwt.decode(
                token,
                jwt_key,
                algorithms=_jwt_algorithms(cfg),
                options=options,
                **kwargs, )
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
    # Admin auth always enforced.
    if not cfg.api_token:
        return
    token_header = request.headers.get("Authorization", "")
    if not token_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = token_header.split(" ", 1)[1].strip()
    if token != cfg.api_token:
        raise HTTPException(status_code=403, detail="invalid admin token")
