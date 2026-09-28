"""Canonical embedding-dimension resolver (settings-owned, fail-closed).

Seam dim unity (ARCHITECTURE-INVARIANTS §2)::

    MEM_EMBED_DIM (somaAgent01) == SOMABRAIN_EMBED_DIM (somabrain)
    == SOMA_VECTOR_DIM (somafractalmemory)

Both the effective dim and the certified seam contract are *configuration* —
declared in Django settings (env ``EMBED_DIM`` / ``EMBED_DIM_SEAM``), auditable
via the system-health endpoint. Runtime code never hardcodes a dimension and
never invents a fallback: misconfigured deployments fail closed.
"""

from __future__ import annotations

from typing import Any


class EmbeddingDimensionError(ValueError):
    """Raised when an embedding violates the configured seam dim."""


def resolve_embed_dim(settings: Any = None) -> int:
    """Return the configured embed dim, failing closed on missing/mismatched config.

    Reads ``SOMABRAIN_EMBED_DIM`` (effective dim) and validates it against
    ``SOMABRAIN_EMBED_DIM_SEAM`` (the certified seam contract). Both live in
    Django settings; nothing here guesses a dimension.
    """
    if settings is None:
        from django.conf import settings as dj_settings

        settings = dj_settings

    dim = getattr(settings, "SOMABRAIN_EMBED_DIM", None)
    if dim is None:
        raise RuntimeError(
            "SOMABRAIN_EMBED_DIM is not configured; refusing to guess a vector dim"
        )
    dim = int(dim)

    seam = getattr(settings, "SOMABRAIN_EMBED_DIM_SEAM", None)
    if seam is None:
        raise RuntimeError(
            "SOMABRAIN_EMBED_DIM_SEAM is not configured; refusing to guess a seam contract"
        )
    seam = int(seam)

    if dim != seam:
        raise RuntimeError(
            f"SOMABRAIN_EMBED_DIM={dim} violates the seam contract {seam} "
            "(MEM_EMBED_DIM == SOMABRAIN_EMBED_DIM == SOMA_VECTOR_DIM); "
            "refusing to continue"
        )
    return dim


def ensure_embedding_dim(embedding: Any, *, dim: int | None = None, settings: Any = None) -> Any:
    """Validate an embedding against the configured seam dim; pass None through."""
    if embedding is None:
        return None
    expected = resolve_embed_dim(settings) if dim is None else int(dim)
    try:
        size = len(embedding)
    except TypeError as exc:
        raise EmbeddingDimensionError(
            "embedding must be a sequence of floats"
        ) from exc
    if size != expected:
        raise EmbeddingDimensionError(
            f"embedding dim {size} violates seam contract {expected}; refusing to continue"
        )
    return embedding
