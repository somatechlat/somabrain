#!/usr/bin/env python3
"""Drift state dump utility.

Prints current drift baselines and last_drift timestamps for each domain:tenant key.

Usage:
    SOMABRAIN_DRIFT_STORE=./data/drift/state.json python scripts/drift_dump.py

If the detector is not enabled, it will still attempt to read the persistence file.
"""

import json
from pathlib import Path
from datetime import datetime

from somabrain.monitoring.drift_detector import drift_detector


def _human(ts: float) -> str:
    """Execute human.

    Args:
        ts: The ts.
    """

    if not ts:
        return "-"
    try:
        return datetime.utcfromtimestamp(ts).isoformat() + "Z"
    except Exception:
        return str(ts)


def main() -> None:
    # Prefer live in-memory state (centralized mode gating); use persistence file alternative if detector disabled
    """Execute main."""

    if drift_detector.enabled:
        state = drift_detector.export_state()
    else:
        # Use centralized Settings for drift store path
        from django.conf import settings

        store_path = settings.drift_store_path
        p = Path(store_path)
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                state = data.get("entries", {}) if isinstance(data, dict) else {}
            except Exception:
                state = {}
        else:
            state = {}
    if not state:
        print("No drift state available.")
        return
    # Render table
    print("domain:tenant, last_drift, entropy_baseline, regret_baseline, initialized")
    for key, entry in sorted(state.items()):
        print(
            f"{key}, {_human(entry.get('last_drift_time', 0.0))}, {entry.get('entropy_baseline', 0.0):.4f}, {entry.get('regret_baseline', 0.0):.4f}, {bool(entry.get('baseline_initialized'))}"
        )


if __name__ == "__main__":
    main()
