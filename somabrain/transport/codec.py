"""Proto <-> seam value codec — the field-fidelity layer.

This module is the only place that knows both sides of the wire: the
``soma.brain.v1`` protobuf messages and the seam value shapes from
``services/common/memory_contract.py`` (SOMA-ARCH-INVARIANTS-001 §5). Every
field crosses here, and every field is named explicitly.

Why this file exists: the failure mode this whole triad has already been bitten
by is a boundary that *looks* like it forwards a request while silently
dropping fields. A past regression rebuilt the store body as
``{coord, payload, memory_type}`` and quietly lost ``embedding`` and
``tenant_id`` — every stored memory then fell back to hash vectors and tenant
isolation stopped meaning anything. That class of bug is what the exhaustive
mapping and the round-trip tests below are for.

Rules:
  * Every field in the seam is mapped in both directions. Adding one to
    ``brain.proto`` without adding it here is a test failure, not a silent gap.
  * Absence is explicit. proto3 scalars have no null, so ``optional`` fields
    are the only ones that may be absent; a non-optional scalar always carries
    a value and must not be used where the seam allows ``None``.
  * Enum values are validated. An unrecognised ``MemoryKind`` or ``StoreName``
    is a protocol error, never coerced to a default.
"""

from __future__ import annotations

from typing import Any

from somabrain.proto.brain_pb2 import (
    MEMORY_KIND_BELIEF,
    MEMORY_KIND_EPISODIC,
    MEMORY_KIND_SEMANTIC,
    MEMORY_KIND_UNSPECIFIED,
    STORE_NAME_SOMABRAIN,
    STORE_NAME_SOMAFRACTALMEMORY,
    STORE_NAME_UNSPECIFIED,
    MemoryAck,
    MemoryHit,
    MemoryWrite,
    Vector,
)
from somabrain.transport.vector_codec import (
    DTYPE_FLOAT32,
    PackedVector,
    VectorCodecError,
    pack_vector,
    unpack_single,
)

# ---------------------------------------------------------------------------
# Seam values. The decode side produces plain ``dict[str, Any]`` keyed exactly
# like the seam's MemoryWrite / MemoryHit / MemoryAck fields, and the encode
# side consumes those dicts — so the transport layer carries no pydantic
# dependency into the cognitive trees. An attribute-bearing object (the agent's
# pydantic models) is equally acceptable; see :func:`_field`.
# ---------------------------------------------------------------------------

# Defaults are not invented here: they are the seam's own declared defaults
# (``services/common/memory_contract.py`` — ``kind: Literal[...] = "episodic"``,
# ``salience: float = 0.5``, ``source: str = "agent-chat"``). A proto3 field
# that is not ``optional`` carries no presence, so an omitted kind arrives as
# ``MEMORY_KIND_UNSPECIFIED`` and an omitted source as ``""``; both mean
# "the caller did not set it" and resolve to the seam default.
SEAM_DEFAULT_KIND = "episodic"
SEAM_DEFAULT_SALIENCE = 0.5
SEAM_DEFAULT_SOURCE = "agent-chat"

_MEMORY_KIND_TO_PROTO = {
    "episodic": MEMORY_KIND_EPISODIC,
    "semantic": MEMORY_KIND_SEMANTIC,
    "belief": MEMORY_KIND_BELIEF,
}
_PROTO_TO_MEMORY_KIND = {
    MEMORY_KIND_EPISODIC: "episodic",
    MEMORY_KIND_SEMANTIC: "semantic",
    MEMORY_KIND_BELIEF: "belief",
}

_STORE_TO_PROTO = {
    "somabrain": STORE_NAME_SOMABRAIN,
    "somafractalmemory": STORE_NAME_SOMAFRACTALMEMORY,
}
_PROTO_TO_STORE = {
    STORE_NAME_SOMABRAIN: "somabrain",
    STORE_NAME_SOMAFRACTALMEMORY: "somafractalmemory",
}


class CodecError(ValueError):
    """Raised when a value cannot be represented on the wire or decoded back.

    Fail-closed (VIBE Rule 91): never coerce an unknown enum, never substitute
    a default for a missing required field, never drop a field to make a
    message fit.
    """


def _field(value: Any, name: str, default: Any = None) -> Any:
    """Read one seam field from a mapping or an attribute-bearing object.

    The decode half of this module returns plain dicts and the serve layer
    builds plain dicts, while the agent's seam values are pydantic models.
    Both are legitimate inputs to an encoder, so every field read goes through
    here rather than ``getattr`` — ``getattr`` on a dict silently returns the
    default even when the key is present, which is exactly how ``session_id``
    and ``role`` were being dropped from recalled hits.

    Args:
        value: A mapping, or any object carrying the field as an attribute.
        name: The seam field name.
        default: Returned when the field is absent. A present-but-``None``
            value is returned as ``None`` and is not replaced by ``default``.

    Returns:
        The field value, or ``default`` when it is genuinely absent.
    """
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


# ---------------------------------------------------------------------------
# Value -> proto
# ---------------------------------------------------------------------------


def encode_memory_write(write: Any) -> MemoryWrite:
    """Encode a seam ``MemoryWrite`` into its protobuf message.

    Args:
        write: Object with ``text``, ``kind``, ``tenant_id``, ``session_id``,
            ``coord``, ``embedding``, ``salience``, ``source`` — the pydantic
            model or any duck-typed equivalent.

    Returns:
        The protobuf ``MemoryWrite``.

    Raises:
        CodecError: On an unrecognised ``kind``, a missing ``tenant_id`` or
            ``coord``, or an embedding that cannot be packed. A required field
            is never empty-substituted.
    """
    text = _field(write, "text")
    if not isinstance(text, str) or not text.strip():
        raise CodecError("MemoryWrite.text is required and must be non-empty")

    tenant_id = _field(write, "tenant_id")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise CodecError(
            "MemoryWrite.tenant_id is required and must be non-empty; an absent "
            "tenant is a cross-tenant leak, not a default"
        )

    coord = _field(write, "coord")
    if not isinstance(coord, str) or not coord.strip():
        raise CodecError(
            "MemoryWrite.coord is required and must be non-empty; the coordinate "
            "scheme is the record identity and may not be invented here"
        )

    kind = str(_field(write, "kind", SEAM_DEFAULT_KIND) or SEAM_DEFAULT_KIND)
    proto_kind = _MEMORY_KIND_TO_PROTO.get(kind)
    if proto_kind is None or proto_kind == MEMORY_KIND_UNSPECIFIED:
        raise CodecError(
            f"unrecognised MemoryWrite.kind {kind!r}; expected one of "
            f"{sorted(_MEMORY_KIND_TO_PROTO)}"
        )

    msg = MemoryWrite(
        text=text,
        kind=proto_kind,
        tenant_id=tenant_id,
        coord=coord,
        source=str(_field(write, "source", SEAM_DEFAULT_SOURCE) or SEAM_DEFAULT_SOURCE),
    )

    session_id = _field(write, "session_id")
    if session_id is not None and str(session_id).strip():
        msg.session_id = str(session_id)

    salience = _field(write, "salience")
    if salience is not None:
        msg.salience = float(salience)

    embedding = _field(write, "embedding")
    if embedding is not None:
        msg.embedding.CopyFrom(_encode_vector(embedding))

    return msg


def _encode_vector(embedding: Any) -> Vector:
    """Pack a ``list[float]`` embedding into a wire ``Vector``."""
    try:
        packed = pack_vector(list(embedding), dtype=DTYPE_FLOAT32)
    except (VectorCodecError, TypeError) as exc:
        raise CodecError(f"MemoryWrite.embedding cannot be packed: {exc}") from exc
    return Vector(
        data=packed.data, dtype=packed.dtype, dim=packed.dim, count=packed.count
    )


def encode_recall_hit(hit: Any) -> MemoryHit:
    """Encode a seam ``MemoryHit`` into its protobuf message.

    Args:
        hit: Object with ``text``, ``coord``, ``score``, ``store``,
            ``created_at``, and optional ``session_id`` / ``role``.

    Returns:
        The protobuf ``MemoryHit``.

    Raises:
        CodecError: On an unrecognised ``store`` or a missing identity field.
    """
    text = _field(hit, "text")
    coord = _field(hit, "coord")
    created_at = _field(hit, "created_at")
    for name, value in (("text", text), ("coord", coord), ("created_at", created_at)):
        if not isinstance(value, str) or not value.strip():
            raise CodecError(f"MemoryHit.{name} is required and must be non-empty")

    store = str(_field(hit, "store", "") or "")
    proto_store = _STORE_TO_PROTO.get(store)
    if proto_store is None or proto_store == STORE_NAME_UNSPECIFIED:
        raise CodecError(
            f"unrecognised MemoryHit.store {store!r}; expected one of "
            f"{sorted(_STORE_TO_PROTO)}"
        )

    score = _field(hit, "score")
    if score is None:
        raise CodecError("MemoryHit.score is required; an unscored hit is not a hit")

    msg = MemoryHit(
        text=text,
        coord=coord,
        score=float(score),
        store=proto_store,
        created_at=created_at,
    )
    session_id = _field(hit, "session_id")
    if session_id is not None and str(session_id).strip():
        msg.session_id = str(session_id)
    role = _field(hit, "role")
    if role is not None and str(role).strip():
        msg.role = str(role)
    return msg


def encode_memory_ack(ack: Any) -> MemoryAck:
    """Encode a seam ``MemoryAck`` into its protobuf message.

    Raises:
        CodecError: On an unrecognised ``store``. ``error`` is preserved
            verbatim whenever present — a failed write must never arrive as a
            successful one.
    """
    coord = _field(ack, "coord")
    if not isinstance(coord, str) or not coord.strip():
        raise CodecError("MemoryAck.coord is required and must be non-empty")

    store = str(_field(ack, "store", "") or "")
    proto_store = _STORE_TO_PROTO.get(store)
    if proto_store is None or proto_store == STORE_NAME_UNSPECIFIED:
        raise CodecError(
            f"unrecognised MemoryAck.store {store!r}; expected one of "
            f"{sorted(_STORE_TO_PROTO)}"
        )

    msg = MemoryAck(coord=coord, store=proto_store, ok=bool(_field(ack, "ok", False)))
    error = _field(ack, "error")
    if error is not None and str(error):
        msg.error = str(error)
    return msg


# ---------------------------------------------------------------------------
# proto -> value
# ---------------------------------------------------------------------------


def decode_memory_write(msg: MemoryWrite) -> dict[str, Any]:
    """Decode a protobuf ``MemoryWrite`` into the seam field dict.

    Returns:
        A dict with exactly the seam keys: ``text``, ``kind``, ``tenant_id``,
        ``session_id``, ``coord``, ``embedding``, ``salience``, ``source``.
        ``session_id`` and ``embedding`` are ``None`` when absent. ``kind``,
        ``salience`` and ``source`` resolve to the seam's own declared
        defaults when the caller omitted them.

    Raises:
        CodecError: On an unrecognised ``kind``, a required field left empty,
            or an embedding whose declared layout contradicts its bytes.
    """
    if not msg.text.strip():
        raise CodecError("MemoryWrite.text is required and must be non-empty")
    if not msg.tenant_id.strip():
        raise CodecError("MemoryWrite.tenant_id is required and must be non-empty")
    if not msg.coord.strip():
        raise CodecError("MemoryWrite.coord is required and must be non-empty")

    kind = _PROTO_TO_MEMORY_KIND.get(msg.kind)
    if kind is None:
        # MEMORY_KIND_UNSPECIFIED is the proto3 zero value, which is what a
        # non-optional enum carries when the caller omitted it. The seam types
        # ``kind`` with a default, so omission resolves to that default. Any
        # other unmapped value is a genuine protocol error and is refused —
        # an unknown enum is never coerced to a default (Rule 91).
        if msg.kind == MEMORY_KIND_UNSPECIFIED:
            kind = SEAM_DEFAULT_KIND
        else:
            raise CodecError(f"unrecognised MemoryWrite.kind value {int(msg.kind)}")

    embedding: list[float] | None = None
    if msg.HasField("embedding"):
        embedding = _decode_vector(msg.embedding)

    return {
        "text": msg.text,
        "kind": kind,
        "tenant_id": msg.tenant_id,
        "session_id": msg.session_id if msg.HasField("session_id") else None,
        "coord": msg.coord,
        "embedding": embedding,
        "salience": msg.salience if msg.HasField("salience") else SEAM_DEFAULT_SALIENCE,
        "source": msg.source or SEAM_DEFAULT_SOURCE,
    }


def _decode_vector(vec: Vector) -> list[float]:
    """Unpack a wire ``Vector`` into one ``list[float]``."""
    try:
        return unpack_single(
            PackedVector(data=bytes(vec.data), dtype=vec.dtype, dim=vec.dim, count=vec.count)
        )
    except VectorCodecError as exc:
        raise CodecError(f"MemoryWrite.embedding is malformed: {exc}") from exc


def decode_recall_hit(msg: MemoryHit) -> dict[str, Any]:
    """Decode a protobuf ``MemoryHit`` into the seam field dict."""
    store = _PROTO_TO_STORE.get(msg.store)
    if store is None:
        raise CodecError(f"unrecognised MemoryHit.store value {int(msg.store)}")
    return {
        "text": msg.text,
        "coord": msg.coord,
        "score": float(msg.score),
        "store": store,
        "created_at": msg.created_at,
        "session_id": msg.session_id if msg.HasField("session_id") else None,
        "role": msg.role if msg.HasField("role") else None,
    }


def decode_memory_ack(msg: MemoryAck) -> dict[str, Any]:
    """Decode a protobuf ``MemoryAck`` into the seam field dict."""
    store = _PROTO_TO_STORE.get(msg.store)
    if store is None:
        raise CodecError(f"unrecognised MemoryAck.store value {int(msg.store)}")
    return {
        "coord": msg.coord,
        "store": store,
        "ok": bool(msg.ok),
        "error": msg.error if msg.HasField("error") else None,
    }
