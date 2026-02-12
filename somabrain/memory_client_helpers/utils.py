"""
Memory Client Utilities.

Standalone helper functions for coordinate generation, parsing, and filtering.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, List, Optional, Tuple

from django.conf import settings


def http_setting(attr: str, default_val: int) -> int:
    """Fetch HTTP client tuning knobs from shared settings with default."""
    if settings is not None:
        try:
            value = getattr(settings, attr)
            if value is None:
                return default_val
            return int(value)
        except Exception:
            pass
    return default_val


def stable_coord(key: str) -> Tuple[float, float, float]:
    """Derive a deterministic 3D coordinate in [-1,1]^3 from a string key."""
    h = hashlib.blake2b(key.encode("utf-8"), digest_size=12).digest()
    a = int.from_bytes(h[0:4], "big") / 2**32
    b = int.from_bytes(h[4:8], "big") / 2**32
    c = int.from_bytes(h[8:12], "big") / 2**32
    return (2 * a - 1, 2 * b - 1, 2 * c - 1)


def parse_coord_string(s: str) -> Tuple[float, float, float] | None:
    """Parse a comma-separated coordinate string to a 3-tuple."""
    try:
        parts = [float(x.strip()) for x in str(s).split(",")]
        if len(parts) >= 3:
            return (parts[0], parts[1], parts[2])
    except Exception:
        return None
    return None


def filter_payloads_by_keyword(payloads: Iterable[Any], keyword: str) -> List[dict]:
    """Return payloads that include *keyword* in common string fields.

    The filter is intentionally lightweight so it can run on every recall even
    when the backend service does not support lexical search. If no payloads
    match, the original list is returned to preserve behaviour.
    """
    items: List[dict] = [p for p in payloads if isinstance(p, dict)]
    key = str(keyword or "").strip().lower()
    if not key:
        return items

    filtered: List[dict] = []
    fields = ("what", "headline", "text", "content", "who", "task", "session")
    for entry in items:
        for field in fields:
            value = entry.get(field)
            if isinstance(value, str) and key in value.lower():
                filtered.append(entry)
                break
    return filtered or items


def extract_memory_coord(
    resp: Any,
    idempotency_key: str | None = None,
) -> Tuple[float, float, float] | None:
    """Try to derive a coordinate tuple from the memory-service response."""
    if not resp:
        return None

    data = resp
    json_attr = getattr(resp, "json", None)
    if callable(json_attr):
        try:
            data = json_attr()
        except (ValueError, TypeError):
            data = resp

    data_dict = data if isinstance(data, dict) else None

    if data_dict is not None:
        for key in ("coord", "coordinate"):
            value = data_dict.get(key)
            parsed: Optional[Tuple[float, float, float]] = None
            if isinstance(value, str):
                parsed = parse_coord_string(value)
            elif isinstance(value, (list, tuple)) and len(value) >= 3:
                try:
                    parsed = (float(value[0]), float(value[1]), float(value[2]))
                except (TypeError, ValueError):
                    parsed = None
            if parsed:
                return parsed

        mem_section = data_dict.get("memory")
        if isinstance(mem_section, dict):
            for key in ("coordinate", "coord", "location"):
                value = mem_section.get(key)
                parsed = None
                if isinstance(value, str):
                    parsed = parse_coord_string(value)
                elif isinstance(value, (list, tuple)) and len(value) >= 3:
                    try:
                        parsed = (float(value[0]), float(value[1]), float(value[2]))
                    except (TypeError, ValueError):
                        parsed = None
                if parsed:
                    return parsed

            mid = mem_section.get("id") or mem_section.get("memory_id")
            if mid is not None:
                try:
                    return stable_coord(str(mid))
                except (TypeError, ValueError):
                    pass

        mid = data_dict.get("id") or data_dict.get("memory_id")
        if mid is not None:
            try:
                return stable_coord(str(mid))
            except (TypeError, ValueError):
                pass

    if idempotency_key:
        try:
            return stable_coord(f"idempotency:{idempotency_key}")
        except (TypeError, ValueError):
            return None
    return None
