"""Bridge subpackage for kafka_cog.

Re-exports objects from top-level `libs.kafka_cog` to support
`somabrain.libs.kafka_cog` import paths.
"""

from __future__ import annotations

import importlib
import sys as _sys

try:
    _base = importlib.import_module("libs.kafka_cog")
    for attr in getattr(_base, "__all__", []):  # type: ignore[arg-type]
        try:
            globals()[attr] = getattr(_base, attr)
        except Exception as exc: raise
    _sys.modules[__name__ + ".avro_schemas"] = importlib.import_module(
        "libs.kafka_cog.avro_schemas"
    )
    try:
        _sys.modules[__name__ + ".serde"] = importlib.import_module(
            "libs.kafka_cog.serde"
        )
    except Exception as exc: raise
except Exception as exc: raise
    # Leave empty; segmentation_service will raise strictly.
