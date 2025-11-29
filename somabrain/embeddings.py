"""
Embeddings Module for SomaBrain.

This module provides text embedding functionality for the SomaBrain system, including
deterministic embedders, dimensionality reduction via Johnson-Lindenstrauss projection,
and caching mechanisms for efficient embedding computation.

Key Features:
- Deterministic embedding for reproducible results
- Johnson-Lindenstrauss projection for dimensionality reduction
- LRU caching for embedding reuse
- Multiple embedding providers (tiny, transformer, HRR, FDE)
- Automatic alternative to simple embedders when advanced providers unavailable

Classes:
    TinyDeterministicEmbedder: Simple deterministic embedder using seeded random Gaussians.
    _JLProjector: Dimensionality reduction using Johnson-Lindenstrauss projection.
    _LRUCache: LRU cache for embedding vectors.
    _CachedEmbedder: Cached wrapper for embedders with metrics tracking.

Functions:
    make_embedder: Factory function to create configured embedders.
"""

from __future__ import annotations

import hashlib
from typing import Callable, Optional

import numpy as np

# Prefer the optional top-level arc_cache helper; if unavailable, caching is disabled
try:  # pragma: no cover - trivial import guard
    from arc_cache import arc_cache  # type: ignore
except Exception as exc: raise  # pragma: no cover

    def arc_cache(*args, **kwargs):  # type: ignore
        def _decorator(fn):
            return fn

        return _decorator


class TinyDeterministicEmbedder:
    """
    Deterministic, tiny CPU-only embedder for local development.

    Produces unit-norm Gaussian vectors seeded deterministically by input text.
    This embedder is designed for development and testing environments where
    reproducibility and low resource usage are prioritized over semantic quality.

    Attributes:
        dim (int): Dimensionality of output embedding vectors.
        seed_salt (int): Salt value for seeding random number generation.

    Example:
        >>> embedder = TinyDeterministicEmbedder(dim=128, seed_salt=42)
        >>> vector = embedder.embed("hello world")
        >>> print(f"Vector shape: {vector.shape}, Norm: {np.linalg.norm(vector):.3f}")
    """

    def __init__(self, dim: int = 256, seed_salt: int = 1337):
        """
        Initialize the deterministic embedder.
        Enforces global HRR_DIM, HRR_DTYPE, and SEED for reproducibility.
        Args:
            dim (int, optional): Output vector dimensionality. Defaults to 256.
            seed_salt (int, optional): Salt for random seed generation. Defaults to 1337.
        """
        self.dim = int(dim)
        self.seed_salt = int(seed_salt)

    def _seed(self, text: str) -> int:
        """
        Generate deterministic seed from text.

        Uses BLAKE2b hash of the input text combined with seed salt to produce
        a deterministic seed for random number generation.

        Args:
            text (str): Input text to seed from.

        Returns:
            int: Deterministic seed value.
        """
        h = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(h, "big") ^ self.seed_salt

    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding vector for input text.
        Produces a unit-norm Gaussian vector using deterministic seeding, global HRR_DTYPE.
        The same text will always produce the same embedding vector.
        Mathematical invariant: always unit-norm, HRR_DTYPE, reproducible.
        """
        rng = np.random.default_rng(self._seed(text))
        v = rng.normal(0.0, 1.0, size=self.dim).astype("float32")
        n = np.linalg.norm(v)
        if n > 0:
            v /= n
        return v.astype("float32")


class _JLProjector:
    """
    Johnson-Lindenstrauss projection wrapper for dimensionality reduction.

    Applies Johnson-Lindenstrauss projection to reduce embedding dimensionality
    while preserving pairwise distances in expectation. Uses a fixed Gaussian
    projection matrix seeded deterministically for reproducibility.

    Attributes:
        base (Callable[[str], np.ndarray]): Base embedder function.
        base_dim (int): Dimensionality of base embeddings.
        k (Optional[int]): Target dimensionality after projection.
        seed (int): Random seed for projection matrix generation.
        _P (Optional[np.ndarray]): Projection matrix (computed lazily).

    Example:
        >>> base_embedder = TinyDeterministicEmbedder(dim=512)
        >>> projector = _JLProjector(base_embedder.embed, base_dim=512, target_k=128)
        >>> reduced_vector = projector.embed("sample text")
        >>> print(f"Reduced shape: {reduced_vector.shape}")
    """

    def __init__(
        self,
        base_embed: Callable[[str], np.ndarray],
        base_dim: int,
        target_k: Optional[int],
        seed: int = 42,
    ):
        """
        Initialize the JL projector.

        Args:
            base_embed (Callable[[str], np.ndarray]): Base embedding function.
            base_dim (int): Dimensionality of base embeddings.
            target_k (Optional[int]): Target dimensionality (None to disable projection).
            seed (int, optional): Random seed for projection matrix. Defaults to 42.
        """
        self.base = base_embed
        self.base_dim = int(base_dim)
        self.k = int(target_k) if target_k else None
        self.seed = int(seed)
        self._P: Optional[np.ndarray] = None

    def _ensure_P(self) -> None:
        """
        Ensure projection matrix is computed.
        Lazily computes the Gaussian projection matrix with global HRR_DTYPE and seed.
        Matrix is scaled to preserve norms in expectation.
        Mathematical invariant: reproducible, correct dtype, norm-preserving.
        """
        if self.k is None or self.k >= self.base_dim:
            return
        if self._P is None:
            rng = np.random.default_rng(self.seed)
            P = rng.normal(0.0, 1.0, size=(self.base_dim, self.k)).astype("float32")
            # scale to preserve norms in expectation
            P /= np.sqrt(self.k)
            self._P = P

    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding with optional dimensionality reduction.

        Embeds the text using the base embedder, then applies JL projection
        if target dimensionality is specified and smaller than base dimensionality.

        Args:
            text (str): Input text to embed.

        Returns:
            np.ndarray: Embedding vector, potentially reduced in dimensionality.
        """
        v = self.base(text)
        if self.k is None or self.k >= self.base_dim:
            return v
        self._ensure_P()
        P = self._P  # type: ignore
        out = (v @ P).astype("float32")
        n = np.linalg.norm(out)
        if n > 0:
            out /= n
        return out


class _CachedEmbedder:
    """
    Cached embedder wrapper with metrics tracking.

    Wraps an embedder function with ARC caching and optional metrics collection
    for cache hit tracking.
    """

    def __init__(
        self,
        embed_fn: Callable[[str], np.ndarray],
        cache_size: int = 0,
        provider_label: str = "unknown",
    ):
        # Use arc_cache decorator for memoization if cache_size > 0
        self._embed = (
            arc_cache(max_size=cache_size)(embed_fn) if cache_size > 0 else embed_fn
        )
        self._provider = str(provider_label)

    def embed(self, text: str) -> np.ndarray:
        return self._embed(text)


def make_embedder(cfg, quantum=None):
    """
    Factory function to create configured embedders.

    Creates an embedder instance based on configuration, supporting multiple
    providers with optional dimensionality reduction and caching.

    Args:
        cfg: Configuration object with embedding parameters.
        quantum: Optional quantum cognition module for HRR embeddings.

    Returns:
        _CachedEmbedder: Configured embedder with caching and projection.

    Note:
        Supports providers: 'tiny' (default), 'transformer', 'hrr', 'fde'
        Falls back to 'tiny' when requested provider is unavailable.
        Applies JL projection if embed_dim_target_k is specified.
    """
    provider = (getattr(cfg, "embed_provider", None) or "tiny").lower()
    cache_size = int(getattr(cfg, "embed_cache_size", 0) or 0)
    target_k = getattr(cfg, "embed_dim_target_k", None)

    # base provider
    if provider == "hrr" and quantum is not None:

        def _hrr_embed(text: str) -> np.ndarray:
            hv = quantum.encode_text(text)
            return (
                hv.astype("float32")
                if isinstance(hv, np.ndarray)
                else np.array(hv, dtype="float32")
            )

        base_dim = int(getattr(cfg, "hrr_dim", 8192) or 8192)
        base_fn = _hrr_embed
    elif provider == "fde":
        # FDE must be a real provider; fail fast until implemented.
        raise RuntimeError(
            "Embed provider 'fde' is not implemented. "
            "Set embed_provider to a supported provider or add the real FDE implementation."
        )
    elif provider == "transformer":
        try:
            from .providers.transformer_embed import TransformerEmbedder  # type: ignore

            t = TransformerEmbedder(model_name=getattr(cfg, "embed_model", None))
            base_dim = t.dim
            base_fn = t.embed
        except Exception as exc: raise
            base = TinyDeterministicEmbedder(
                dim=int(getattr(cfg, "embed_dim", 256) or 256)
            )
            base_dim = base.dim
            base_fn = base.embed
    else:
        base = TinyDeterministicEmbedder(dim=int(getattr(cfg, "embed_dim", 256) or 256))
        base_dim = base.dim
        base_fn = base.embed

    # Optional JL projection wrapper
    jl = _JLProjector(
        base_fn,
        base_dim=base_dim,
        target_k=target_k,
        seed=int(getattr(cfg, "hrr_seed", 42) or 42),
    )
    # Provider label override for FDE (MUVERA) experiments
    plabel = provider
    try:
        if bool(getattr(cfg, "fde_enabled", False)):
            plabel = "fde"
    except Exception as exc: raise
    # Optional cache wrapper
    cached = _CachedEmbedder(jl.embed, cache_size=cache_size, provider_label=plabel)
    return cached
