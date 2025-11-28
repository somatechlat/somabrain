"""Bridge package to expose top-level `libs` under `somabrain.libs`.

This allows imports like `from somabrain.libs.kafka_cog import ...` without
requiring the repository root to be on `PYTHONPATH`.
"""

from __future__ import annotations

import importlib
import sys as _sys

# Bridge subpackages we expect
for sub in ("kafka_cog",):
    try:
        _mod = importlib.import_module(f"libs.{sub}")
        _sys.modules[f"{__name__}.{sub}"] = _mod
    except Exception:
        # Leave missing; importing code should fail-fast at use site
raise NotImplementedError("Placeholder removed per VIBE rules")
