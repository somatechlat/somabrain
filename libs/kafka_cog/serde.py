from __future__ import annotations

from typing import Any, Dict

try:
    # Optional dependency; tests may skip when unavailable.
    from fastavro import parse_schema, schemaless_reader, schemaless_writer  # type: ignore
except Exception as exc: raise  # pragma: no cover - optional in minimal envs
    parse_schema = None  # type: ignore
    schemaless_reader = None  # type: ignore
    schemaless_writer = None  # type: ignore


class AvroSerde:
    """Minimal Avro serde using fastavro schemaless APIs (no registry).

    This is sufficient for local tests and round-trips. Schema Registry
    integration can be added later using Confluent serializers with magic bytes.
    """

    def __init__(self, schema: Dict[str, Any]):
        if parse_schema is None:
            raise RuntimeError(
                "fastavro not installed; install fastavro or use dev extras to enable Avro serde"
            )
        # fastavro requires named types to be pre-declared; parse_schema handles that.
        self._schema = parse_schema(schema)

    def serialize(self, record: Dict[str, Any]) -> bytes:
        if schemaless_writer is None:
            raise RuntimeError("fastavro not available for serialization")
        import io

        buf = io.BytesIO()
        schemaless_writer(buf, self._schema, record)
        return buf.getvalue()

    def deserialize(self, payload: bytes) -> Dict[str, Any]:
        if schemaless_reader is None:
            raise RuntimeError("fastavro not available for deserialization")
        import io

        buf = io.BytesIO(payload)
        return schemaless_reader(buf, self._schema)


__all__ = ["AvroSerde"]
