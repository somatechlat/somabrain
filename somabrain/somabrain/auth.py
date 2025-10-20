from __future__ import annotations

from fastapi import Request, HTTPException
from .config import Config


def require_auth(request: Request, cfg: Config) -> None:
    auth = request.headers.get("Authorization", "")
    # If a specific API token is configured, enforce an exact match
    if cfg.api_token:
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token = auth.split(" ", 1)[1].strip()
        if token != cfg.api_token:
            raise HTTPException(status_code=403, detail="invalid token")
        return
    # If auth is required but no specific token is configured, require any bearer token presence
    if cfg.auth_required:
        if not auth.startswith("Bearer ") or not auth.split(" ", 1)[1].strip():
            raise HTTPException(status_code=401, detail="missing bearer token")
    # otherwise, no auth required
