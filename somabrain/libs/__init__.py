from __future__ import annotations
import importlib
import sys as _sys
from common.logging import logger

"""Bridge package to expose top-level `libs` under `somabrain.libs`.

This allows imports like `from somabrain.libs.kafka_cog import ...` without
requiring the repository root to be on `PYTHONPATH`.
"""



# Bridge subpackages we expect
for sub in ("kafka_cog",):
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        _mod = importlib.import_module(f"libs.{sub}")
        _sys.modules[f"{__name__}.{sub}"] = _mod
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
    raise
