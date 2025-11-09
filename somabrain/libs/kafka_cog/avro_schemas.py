"""Strict Avro schema loader (package-local copy).

Resolves `proto/cog/<name>.avsc` relative to repository root irrespective of
execution CWD. Raises on missing or invalid schemas.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

# Derive repo root by climbing until `proto/cog` exists.
_here = Path(__file__).resolve()
_root = _here
for _ in range(10):  # cap climb depth
    if (_root / "proto" / "cog").exists():
        break
    _root = _root.parent

_BASE = _root / "proto" / "cog"

def load_schema(name: str) -> Dict[str, Any]:
    stem = name.strip()
    if not stem:
        raise ValueError("Empty schema name")
    path = _BASE / f"{stem}.avsc"
    if not path.exists():
        raise FileNotFoundError(f"Avro schema not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to read schema '{stem}': {e}") from e
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid schema format for '{stem}' (expected object)")
    return data

__all__ = ["load_schema"]
