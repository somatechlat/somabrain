"""Module serde."""

from __future__ import annotations

from typing import Any, Dict

try:
    from fastavro import parse_schema, schemaless_reader, schemaless_writer
except Exception:  # pragma: no cover
    parse_schema = None
    schemaless_reader = None
    schemaless_writer = None


class AvroSerde:
    """Avroserde class implementation."""

    def __init__(self, schema: Dict[str, Any]):
        """Initialize the instance."""

        if parse_schema is None:
            raise RuntimeError(
                "fastavro not installed; Avro serde required in strict mode"
            )
        self._schema = parse_schema(schema)

    def serialize(self, record: Dict[str, Any]) -> bytes:
        """Execute serialize.

        Args:
            record: The record.
        """

        if schemaless_writer is None:
            raise RuntimeError("fastavro not available for serialization")
        import io

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
        import io

        buf = io.BytesIO(payload)
        return schemaless_reader(buf, self._schema)


__all__ = ["AvroSerde"]
