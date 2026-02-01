"""Module serde."""

from __future__ import annotations
from typing import Any, Dict
from common.logging import logger
from fastavro import parse_schema, schemaless_reader, schemaless_writer
import io


try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
    # Optional dependency; tests may skip when unavailable.
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise


class AvroSerde:
    """Minimal Avro serde using fastavro schemaless APIs (no registry).

    This is sufficient for local tests and round-trips. Schema Registry
    integration can be added later using Confluent serializers with magic bytes.
    """


def __init__(self, schema: Dict[str, Any]):
    """Initialize the instance."""

    if parse_schema is None:
        raise RuntimeError(
            "fastavro not installed; install fastavro or use dev extras to enable Avro serde"
        )
    # fastavro requires named types to be pre-declared; parse_schema handles that.
    self._schema = parse_schema(schema)


def serialize(self, record: Dict[str, Any]) -> bytes:
    """Execute serialize.

    Args:
        record: The record.
    """

    if schemaless_writer is None:
        raise RuntimeError("fastavro not available for serialization")

    buf = io.BytesIO()
    schemaless_writer(buf, self._schema, record)
    return buf.getvalue()


def deserialize(self, payload: bytes) -> Dict[str, Any]:
    """Execute deserialize.

    Args:
        payload: The payload.
    """

    if schemaless_reader is None:
        raise RuntimeError("fastavro not available for deserialization")

    buf = io.BytesIO(payload)
    return schemaless_reader(buf, self._schema)


__all__ = ["AvroSerde"]
