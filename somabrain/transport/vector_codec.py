"""Vector wire encoding — raw floats with an explicit (dtype, dim, count) header.

PLAN §1.4: embeddings are the fat payload and must travel as raw bytes with a
header, never as a JSON number array. A 768-dim float32 embedding is 3072 bytes
on the wire here; the same vector as a JSON list of Python floats is roughly
10-12 KB and costs a parse on both ends.

The codec is the only place that knows the byte layout. Everything above it
sees ``list[float]``, matching ``MemoryWrite.embedding`` in
``services/common/memory_contract.py`` unchanged (SOMA-ARCH-INVARIANTS-001 §5
invariant 3: the seam DTO does not move when the transport does).
"""

from __future__ import annotations

import struct
from collections.abc import Sequence
from dataclasses import dataclass

# Recognised dtypes. A receiver that does not recognise the dtype must reject
# the payload rather than reinterpret the bytes — float32 and float64 of the
# same dim are different lengths and silently misreading one as the other
# corrupts every downstream score.
DTYPE_FLOAT32 = "float32"
DTYPE_FLOAT64 = "float64"

_STRUCT_FMT = {DTYPE_FLOAT32: "<f", DTYPE_FLOAT64: "<d"}
_ITEM_SIZE = {DTYPE_FLOAT32: 4, DTYPE_FLOAT64: 8}
_MAX_DIM = 65536
_MAX_COUNT = 65536


class VectorCodecError(ValueError):
    """Raised when a vector payload cannot be encoded or decoded.

    Fail-closed: never guess a layout, never zero-pad, never truncate. A
    malformed vector is a protocol error, not a shorter vector.
    """


@dataclass(frozen=True)
class PackedVector:
    """The wire form of one or more vectors, header included."""

    data: bytes
    dtype: str
    dim: int
    count: int


def pack_vector(
    vectors: Sequence[Sequence[float]] | Sequence[float],
    *,
    dtype: str = DTYPE_FLOAT32,
) -> PackedVector:
    """Pack one vector, or a sequence of equal-width vectors, into wire form.

    A flat sequence of floats is treated as a single vector (count=1). A
    sequence of sequences is packed contiguously as count vectors of one dim.

    Args:
        vectors: One vector, or several vectors of identical width.
        dtype: ``float32`` or ``float64``.

    Returns:
        PackedVector with ``data``, ``dtype``, ``dim`` and ``count`` set.

    Raises:
        VectorCodecError: On unknown dtype, empty input, ragged widths,
            non-finite-free numeric values that cannot be packed, or a dim /
            count above the protocol ceiling.
    """
    if dtype not in _STRUCT_FMT:
        raise VectorCodecError(
            f"unknown vector dtype {dtype!r}; expected one of {sorted(_STRUCT_FMT)}"
        )

    if not vectors:
        raise VectorCodecError("cannot pack an empty vector payload")

    first = vectors[0]
    # A flat sequence of numbers is one vector; a sequence of sequences is many.
    is_nested = not isinstance(first, (int, float))
    rows: list[Sequence[float]] = list(vectors) if is_nested else [vectors]  # type: ignore[list-item]

    dim = len(rows[0])
    if dim == 0:
        raise VectorCodecError("cannot pack a zero-width vector")
    if dim > _MAX_DIM:
        raise VectorCodecError(f"vector dim {dim} exceeds protocol ceiling {_MAX_DIM}")
    if len(rows) > _MAX_COUNT:
        raise VectorCodecError(
            f"vector count {len(rows)} exceeds protocol ceiling {_MAX_COUNT}"
        )
    for i, row in enumerate(rows):
        if len(row) != dim:
            raise VectorCodecError(
                f"ragged vector batch: row 0 has dim {dim}, row {i} has dim {len(row)}"
            )

    fmt = _STRUCT_FMT[dtype]
    try:
        data = b"".join(struct.pack(fmt, float(x)) for row in rows for x in row)
    except (struct.error, OverflowError, TypeError, ValueError) as exc:
        raise VectorCodecError(f"vector values cannot be packed as {dtype}: {exc}") from exc

    return PackedVector(data=data, dtype=dtype, dim=dim, count=len(rows))


def unpack_vector(packed: PackedVector) -> list[list[float]]:
    """Decode wire-form vectors back into ``list[list[float]]``.

    Args:
        packed: The wire form produced by :func:`pack_vector` (or an equivalent
            message decoded off the transport).

    Returns:
        ``count`` vectors, each of width ``dim``.

    Raises:
        VectorCodecError: On unknown dtype, a header that contradicts the byte
            length, or a dim / count outside the protocol ceiling. The payload
            is never partially decoded.
    """
    if packed.dtype not in _STRUCT_FMT:
        raise VectorCodecError(
            f"unknown vector dtype {packed.dtype!r}; refusing to reinterpret bytes"
        )
    if packed.dim <= 0 or packed.dim > _MAX_DIM:
        raise VectorCodecError(f"vector dim {packed.dim} outside (0, {_MAX_DIM}]")
    if packed.count <= 0 or packed.count > _MAX_COUNT:
        raise VectorCodecError(f"vector count {packed.count} outside (0, {_MAX_COUNT}]")

    item = _ITEM_SIZE[packed.dtype]
    expected = packed.dim * packed.count * item
    actual = len(packed.data)
    if actual != expected:
        raise VectorCodecError(
            f"vector payload length {actual} does not match header "
            f"(dtype={packed.dtype}, dim={packed.dim}, count={packed.count}) "
            f"which requires {expected} bytes"
        )

    fmt = _STRUCT_FMT[packed.dtype]
    width = item
    out: list[list[float]] = []
    for i in range(packed.count):
        start = i * packed.dim * width
        chunk = packed.data[start : start + packed.dim * width]
        out.append([struct.unpack_from(fmt, chunk, j * width)[0] for j in range(packed.dim)])
    return out


def unpack_single(packed: PackedVector) -> list[float]:
    """Decode a single-vector payload.

    Args:
        packed: Wire form whose header declares ``count == 1``.

    Returns:
        The one vector as ``list[float]``.

    Raises:
        VectorCodecError: If the payload holds more or fewer than one vector,
            or is otherwise undecodable.
    """
    if packed.count != 1:
        raise VectorCodecError(
            f"expected a single vector, payload header declares count={packed.count}"
        )
    return unpack_vector(packed)[0]
