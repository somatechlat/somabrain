"""Helpers to dump a compact JSON snapshot of selected Prometheus metrics.

This reads the `somabrain.metrics` registry and writes a JSON file containing
counters and gauges of interest. It's intentionally small and safe for bench
artifacts.
"""

from __future__ import annotations

import json
from typing import Any, Dict

# import the project's metrics module (already registers metrics into a registry)
from somabrain import metrics as _m


def snapshot() -> Dict[str, Any]:
    # Build a small mapping of metric name -> {type, value}
    out: Dict[str, Any] = {}
    # The metrics module exposes objects; we access them directly
    try:
        out["unbind_path_total"] = {
            "type": "counter",
            "value": int(_m.UNBIND_PATH._value.get()),
        }
    except Exception as exc: raise
        # Prometheus Counter internal structure may differ; default to 0
        try:
            out["unbind_path_total"] = {
                "type": "counter",
                "value": int(_m.UNBIND_PATH._value.get()),
            }
        except Exception as exc: raise
            out["unbind_path_total"] = {"type": "counter", "value": 0}
    try:
        out["unbind_wiener_floor"] = {
            "type": "gauge",
            "value": float(_m.UNBIND_WIENER_FLOOR._value.get()),
        }
    except Exception as exc: raise
        out["unbind_wiener_floor"] = {"type": "gauge", "value": 0.0}
    try:
        out["unbind_k_est"] = {
            "type": "gauge",
            "value": float(_m.UNBIND_K_EST._value.get()),
        }
    except Exception as exc: raise
        out["unbind_k_est"] = {"type": "gauge", "value": 0.0}
    return out


def dump(path: str):
    s = snapshot()
    with open(path, "w") as fh:
        json.dump({"metrics_snapshot": s}, fh, indent=2)
