from __future__ import annotations
import importlib
import sys as _sys
from common.logging import logger

"""Bridge subpackage for kafka_cog.

Re-exports objects from top-level `libs.kafka_cog` to support
`somabrain.libs.kafka_cog` import paths.
"""



try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
    _base = importlib.import_module("libs.kafka_cog")
    for attr in getattr(_base, "__all__", []):  # type: ignore[arg-type]
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            globals()[attr] = getattr(_base, attr)
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
    raise
    _sys.modules[__name__ + ".avro_schemas"] = importlib.import_module(
        "libs.kafka_cog.avro_schemas"
    )
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        _sys.modules[__name__ + ".serde"] = importlib.import_module(
            "libs.kafka_cog.serde"
        )
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
    raise
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
