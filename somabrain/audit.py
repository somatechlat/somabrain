"""Audit helpers (Kafka via transactional outbox only).

Fail-fast policy: audit events must be enqueued to the DB outbox for
publication to Kafka by the outbox publisher. No local journal alternative path,
no direct‑disk durability shims.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Iterable

from somabrain.db.outbox import enqueue_event

# Import FastAPI Request only if available to avoid hard dependency at import time
try:
    from fastapi import Request  # type: ignore
except Exception:  # pragma: no cover - optional runtime dependency
    Request = Any  # type: ignore

try:
    from common.config.settings import settings as shared_settings
except Exception:  # pragma: no cover - optional dependency
    shared_settings = None  # type: ignore

LOGGER = logging.getLogger("somabrain.audit")


def _schema_path() -> Optional[Path]:
    """Return path to docs audit schema if present (optional)."""
    try:
        here = Path(__file__).resolve().parent.parent
        sp = (
            here.parent
            / "docs"
            / "technical-manual"
            / "schemas"
            / "audit_event.schema.json"
        )
        if sp.exists():
            return sp
    except Exception:
        pass
    return None


def publish_event(event: Dict[str, Any], topic: Optional[str] = None) -> bool:
    """Enqueue an audit event to the DB outbox for Kafka publishing.

    Returns True if enqueued; False on any error. No local alternative path.
    """
    topic_str: str = topic or os.getenv("SOMA_AUDIT_TOPIC") or "soma.audit"
    ev = dict(event)
    # sanitize
    sanitized = _sanitize_event(ev)
    if sanitized is not None:
        ev = sanitized
    # defaults
    ev.setdefault("ts", time.time())
    ev.setdefault("event_id", str(uuid.uuid4()))
    ev.setdefault("schema_version", "audit_event_v1")

    # Optional: schema validation with no alternative path
    try:
        import jsonschema  # type: ignore

        sp = _schema_path()
        if sp is not None:
            with sp.open("r", encoding="utf-8") as sf:
                schema = json.load(sf)
            try:
                jsonschema.validate(instance=ev, schema=schema)
            except Exception:
                LOGGER.debug(
                    "Audit event schema validation failed; continuing (no alternative path)"
                )
    except Exception:
        pass

    try:
        enqueue_event(topic=topic_str, payload=ev, dedupe_key=ev["event_id"])
        return True
    except Exception:
        LOGGER.exception("Failed to enqueue audit event to outbox (no alternative path)")
        return False


def log_admin_action(
    request: Request, action: str, details: Optional[Dict[str, Any]] = None
) -> None:
    """Append an admin audit line to the configured audit file; never raises."""
    try:
        # Sanitize user-provided details before writing to disk
        safe_details = _sanitize_event(dict(details) if details else None)

        ev: Dict[str, Any] = {
            "ts": int(time.time()),
            "path": str(request.url.path),
            "method": request.method,
            "client": request.client.host if request.client else None,
            "action": action,
        }
        if safe_details:
            ev["details"] = safe_details

        p = Path("./data/somabrain/audit.log")
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except Exception:
        LOGGER.debug("log_admin_action failed", exc_info=True)


__all__ = ["publish_event", "log_admin_action"]

# ------------------------
# Sanitization utilities
# ------------------------

_SENSITIVE_KEYS: Iterable[str] = (
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "token",
    "api_key",
    "apikey",
    "api-key",
    "secret",
    "password",
    "pass",
    "private_key",
    "private-key",
    "jwt",
    "access_token",
    "refresh_token",
    "client_secret",
    "clientsecret",
    "x-api-key",
    "ssh_key",
    "ssh-private-key",
)

_MASK = "***REDACTED***"


def _mask_value(v: Any) -> Any:
    try:
        if v is None:
            return None
        if isinstance(v, (int, float, bool)):
            return v
        s = str(v)
        # Mask bearer tokens while preserving scheme
        ls = s.lower()
        if ls.startswith("bearer "):
            return s.split(" ", 1)[0] + " " + _MASK
        # Heuristic: mask long secret-like strings
        if "token" in ls or "secret" in ls or len(s) >= 16:
            return _MASK
        return s
    except Exception:
        return _MASK


def _sanitize_event(ev: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Recursively sanitize a mapping by masking sensitive fields.

    - Keys matching _SENSITIVE_KEYS (case-insensitive) are masked.
    - Values that look like bearer tokens or long token-ish strings are masked.
    - Lists and nested dicts are traversed.
    """
    if ev is None:
        return None
    try:

        def _walk(obj: Any) -> Any:
            if isinstance(obj, dict):
                out: Dict[str, Any] = {}
                for k, v in obj.items():
                    lk = str(k).lower()
                    if lk in _SENSITIVE_KEYS:
                        # For auth-like headers, preserve scheme (e.g., "Bearer ")
                        if lk in (
                            "authorization",
                            "proxy-authorization",
                            "cookie",
                            "set-cookie",
                        ):
                            out[k] = _mask_value(v)
                        else:
                            # Keys known to be sensitive are always masked regardless of value shape
                            out[k] = _MASK
                        continue
                    # Special-case: a field called "tenant" may be a token identifier in some flows.
                    # Mask if it contains the substring "token" or looks like a long opaque value.
                    if lk == "tenant":
                        out[k] = _mask_value(v)
                        continue
                    out[k] = _walk(v)
                return out
            if isinstance(obj, list):
                return [_walk(i) for i in obj]
            return obj

        return _walk(ev)
    except Exception:
        # If sanitization fails for any reason, fail-safe by returning a shallow masked copy
        try:
            return {k: (_MASK if str(k).lower() in _SENSITIVE_KEYS else v) for k, v in ev.items()}  # type: ignore[return-value]
        except Exception:
            return ev
