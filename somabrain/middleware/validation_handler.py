"""Validation Error Handler for SomaBrain API.

This module contains the validation error handler extracted from app.py
for better organization and reduced file size.
"""

from __future__ import annotations

import logging
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Surface validation errors with context for operators.
    
    Provides route-specific hints to reduce confusion when validation fails.
    """
    try:
        body = await request.body()
        body_preview = body[:256].decode("utf-8", errors="ignore") if body else ""
    except Exception:
        body_preview = ""
    
    ip = getattr(request.client, "host", None)
    ua = request.headers.get("user-agent", "")
    
    try:
        logging.getLogger("somabrain").warning(
            "422 validation on %s %s from %s UA=%s bodyPreview=%s",
            request.method,
            request.url.path,
            ip,
            ua,
            body_preview,
        )
    except Exception:
        pass
    
    details = exc.errors() if hasattr(exc, "errors") else []
    
    # Provide route-specific hints to reduce confusion when validation fails
    path = request.url.path if hasattr(request, "url") else ""
    
    if "/recall" in str(path):
        hint = {
            "endpoint": "/recall",
            "expected": {
                "json": [
                    'Either a JSON string body (e.g. "hello world")',
                    {
                        "query": "string",
                        "top_k": 10,
                        "retrievers": ["vector", "wm", "graph", "lexical"],
                        "rerank": "auto|cosine|mmr|hrr",
                        "persist": True,
                        "universe": "optional",
                    },
                ]
            },
        }
    elif "/remember" in str(path):
        hint = {
            "endpoint": "/remember",
            "expected": {
                "json": {
                    "tenant": "string",
                    "namespace": "string",
                    "key": "string",
                    "value": {"task": "string", "memory_type": "episodic"},
                }
            },
        }
    else:
        hint = {
            "endpoint": str(path) or "<unknown>",
            "expected": {"json": "See OpenAPI schema for this route"},
        }
    
    return JSONResponse(
        status_code=422,
        content={"detail": details, "hint": hint, "client": ip},
    )


__all__ = ["handle_validation_error"]
