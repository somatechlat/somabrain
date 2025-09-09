"""
Authentication Module for SomaBrain.

This module provides authentication utilities for the SomaBrain API, supporting
token-based authentication with configurable requirements and validation.

Key Features:
- Bearer token authentication
- Configurable authentication requirements
- Support for specific API tokens or general token presence
- FastAPI integration with automatic HTTP exception handling

Functions:
    require_auth: Validate authentication for API requests.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from .config import Config


def require_auth(request: Request, cfg: Config) -> None:
    """
    Validate authentication for API requests.

    Performs authentication validation based on configuration settings.
    Supports three modes:
    1. Specific API token validation (exact match required)
    2. General bearer token presence (any non-empty token)
    3. No authentication required

    Args:
        request (Request): FastAPI request object containing headers.
        cfg (Config): Configuration object with auth settings.

    Raises:
        HTTPException: With status 401 for missing/invalid tokens, 403 for token mismatch.

    Example:
        >>> from fastapi import Request
        >>> from somabrain.config import Config
        >>> cfg = Config(api_token="secret-token", auth_required=True)
        >>> # In FastAPI route:
        >>> # require_auth(request, cfg)
        >>> # If auth fails, HTTPException is raised automatically
    """
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
