"""Module avro_schemas."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
from common.logging import logger


def _repo_root() -> Path:
    """Resolve repository root strictly.

    Strict mode: no heuristic alternatives; assumes canonical layout.
    """
    here = Path(__file__).resolve()
    return here.parent.parent.parent


def load_schema(name: str) -> Dict[str, Any]:
    """Strict Avro schema loader.

    Resolves `proto/cog/<name>.avsc` and returns JSON dict. Raises if the file
    is missing, unreadable, or not a dict. No silent optional alternatives.
    """
    root = _repo_root()
    stem = name.strip()
    if not stem:
        raise ValueError("Empty schema name")
    path = root / "proto" / "cog" / f"{stem}.avsc"
    if not path.exists():
        raise FileNotFoundError(f"Avro schema not found: {path}")
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.exception("Exception caught: %s", e)
        raise
    raise RuntimeError(f"Failed to read schema '{stem}': {e}") from e
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid schema format for '{stem}' (expected object)")
    return data


def load_all() -> Dict[str, Dict[str, Any]]:
    """Load a fixed set of required schemas only.

    Strict mode: no optional suppression; missing required schema raises.
    """
    required = [
        "belief_update",
        "global_frame",
        "segment_boundary",
        "reward_event",
        "next_event",
        "config_update",
        # Oak option events – added for ROAMDP integration
        "option_created",
        "option_updated",
    ]
    out: Dict[str, Dict[str, Any]] = {}
    for name in required:
        out[name] = load_schema(name)
    return out


__all__ = ["load_schema", "load_all"]