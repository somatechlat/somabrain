from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    # libs/kafka_cog/ -> project root
    return here.parent.parent.parent


def load_schema(name: str) -> Dict[str, Any]:
    """
    Load an Avro schema JSON dict from proto/cog/<name>.avsc.

    Args:
        name: base filename without extension, e.g. "belief_update".

    Returns:
        Parsed schema as a Python dict.
    """
    root = _repo_root()
    path = root / "proto" / "cog" / f"{name}.avsc"
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_all() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {
        "belief_update": load_schema("belief_update"),
        "global_frame": load_schema("global_frame"),
        "segment_boundary": load_schema("segment_boundary"),
        # Extended contracts for learning loop
        "reward_event": load_schema("reward_event"),
        "next_event": load_schema("next_event"),
        "config_update": load_schema("config_update"),
    }
    # Optional compatibility schemas (present if files exist)
    try:
        out["integrator_context"] = load_schema("integrator_context")
    except FileNotFoundError:
        pass
    try:
        out["segment_event"] = load_schema("segment_event")
    except FileNotFoundError:
        pass
    try:
        out["belief_update_soma"] = load_schema("belief_update_soma")
    except FileNotFoundError:
        pass
    return out


__all__ = ["load_schema", "load_all"]
