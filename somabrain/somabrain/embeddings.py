from __future__ import annotations

import hashlib
from collections import OrderedDict
from typing import Optional, Callable
import numpy as np
from . import metrics as M


class TinyDeterministicEmbedder:
    """Deterministic, tiny CPU-only embedder for local/dev.

    Produces unit-norm Gaussian vectors seeded by input text.
    """

    def __init__(self, dim: int = 256, seed_salt: int = 1337):
        self.dim = int(dim)
        self.seed_salt = int(seed_salt)

    def _seed(self, text: str) -> int:
        h = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(h, "big") ^ self.seed_salt

    def embed(self, text: str) -> np.ndarray:
        rng = np.random.default_rng(self._seed(text))
        v = rng.normal(0.0, 1.0, size=self.dim).astype("float32")
        n = np.linalg.norm(v)
        if n > 0:
            v /= n
        return v


class _JLProjector:
    """Johnson–Lindenstrauss projection wrapper for any base embedder.

    Projects base vectors to target_k dims using a fixed Gaussian matrix
    seeded deterministically for reproducibility.
    """

    def __init__(self, base_embed: Callable[[str], np.ndarray], base_dim: int, target_k: Optional[int], seed: int = 42):
        self.base = base_embed
        self.base_dim = int(base_dim)
        self.k = int(target_k) if target_k else None
        self.seed = int(seed)
        self._P: Optional[np.ndarray] = None

    def _ensure_P(self) -> None:
        if self.k is None or self.k >= self.base_dim:
            return
        if self._P is None:
            rng = np.random.default_rng(self.seed)
            P = rng.normal(0.0, 1.0, size=(self.base_dim, self.k)).astype("float32")
            # scale to preserve norms in expectation
            P /= np.sqrt(self.k)
            self._P = P

    def embed(self, text: str) -> np.ndarray:
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


class _LRUCache:
    def __init__(self, maxsize: int = 0):
        self.maxsize = int(max(0, maxsize))
        self._d: "OrderedDict[str, np.ndarray]" = OrderedDict()

    def get(self, key: str) -> Optional[np.ndarray]:
        if self.maxsize <= 0:
            return None
        v = self._d.get(key)
        if v is not None:
            self._d.move_to_end(key)
        return v

    def set(self, key: str, val: np.ndarray) -> None:
        if self.maxsize <= 0:
            return
        self._d[key] = val
        self._d.move_to_end(key)
        while len(self._d) > self.maxsize:
            self._d.popitem(last=False)


class _CachedEmbedder:
    def __init__(self, embed_fn: Callable[[str], np.ndarray], cache_size: int = 0, provider_label: str = "unknown"):
        self._embed = embed_fn
        self._cache = _LRUCache(cache_size)
        self._provider = str(provider_label)

    def embed(self, text: str) -> np.ndarray:
        v = self._cache.get(text)
        if v is not None:
            try:
                M.EMBED_CACHE_HIT.labels(provider=self._provider).inc()
            except Exception:
                pass
            return v
        v = self._embed(text)
        self._cache.set(text, v)
        return v


def make_embedder(cfg, quantum=None):
    """Factory: returns an embedder with .embed(text)->np.ndarray.

    Respects cfg.embed_provider ('tiny'|'transformer'|'hrr'), optional
    JL target (cfg.embed_dim_target_k), and simple LRU cache.
    Falls back to 'tiny' when provider is unavailable.
    """
    provider = (getattr(cfg, "embed_provider", None) or "tiny").lower()
    cache_size = int(getattr(cfg, "embed_cache_size", 0) or 0)
    target_k = getattr(cfg, "embed_dim_target_k", None)

    # base provider
    if provider == "hrr" and quantum is not None:
        def _hrr_embed(text: str) -> np.ndarray:
            hv = quantum.encode_text(text)
            return hv.astype("float32") if isinstance(hv, np.ndarray) else np.array(hv, dtype="float32")
        base_dim = int(getattr(cfg, "hrr_dim", 8192) or 8192)
        base_fn = _hrr_embed
    elif provider == "fde":
        # Placeholder: treat FDE as tiny provider for now but label via plabel below
        base = TinyDeterministicEmbedder(dim=int(getattr(cfg, "embed_dim", 256) or 256))
        base_dim = base.dim
        base_fn = base.embed
    elif provider == "transformer":
        try:
            from .providers.transformer_embed import TransformerEmbedder  # type: ignore
            t = TransformerEmbedder(model_name=getattr(cfg, "embed_model", None))
            base_dim = t.dim
            base_fn = t.embed
        except Exception:
            base = TinyDeterministicEmbedder(dim=int(getattr(cfg, "embed_dim", 256) or 256))
            base_dim = base.dim
            base_fn = base.embed
    else:
        base = TinyDeterministicEmbedder(dim=int(getattr(cfg, "embed_dim", 256) or 256))
        base_dim = base.dim
        base_fn = base.embed

    # Optional JL projection wrapper
    jl = _JLProjector(base_fn, base_dim=base_dim, target_k=target_k, seed=int(getattr(cfg, "hrr_seed", 42) or 42))
    # Provider label override for FDE (MUVERA) experiments
    plabel = provider
    try:
        if bool(getattr(cfg, "fde_enabled", False)):
            plabel = "fde"
    except Exception:
        pass
    # Optional cache wrapper
    cached = _CachedEmbedder(jl.embed, cache_size=cache_size, provider_label=plabel)
    return cached
