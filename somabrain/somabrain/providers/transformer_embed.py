from __future__ import annotations

"""
Lightweight transformer embedding provider.

Attempts to use sentence-transformers if available; otherwise falls back to
transformers with mean pooling over the last hidden state. If neither is available,
raises ImportError so the caller can gracefully fallback to a tiny provider.

This provider is CPU-friendly for small batches and local dev. For large scale,
prefer an ONNX/quantized model or a service-backed provider.
"""

from typing import Optional, List
import numpy as np


class TransformerEmbedder:
    def __init__(self, model_name: Optional[str] = None, normalize: bool = True, max_length: int = 256):
        self.model_name = model_name or "sentence-transformers/all-MiniLM-L6-v2"
        self.normalize = bool(normalize)
        self.max_length = int(max_length)
        self._backend = None
        self._dim = None
        self._init_backend()

    @property
    def dim(self) -> int:
        return int(self._dim or 384)

    def _init_backend(self) -> None:
        # Try sentence-transformers first
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._backend = ("st", SentenceTransformer(self.model_name))
            # Probe dim
            v = self._backend[1].encode(["probe"], normalize_embeddings=self.normalize)
            self._dim = int(v.shape[1]) if hasattr(v, "shape") else len(v[0])
            return
        except Exception:
            pass
        # Fallback to transformers
        try:
            from transformers import AutoTokenizer, AutoModel  # type: ignore
            import torch  # type: ignore
            tok = AutoTokenizer.from_pretrained(self.model_name)
            mdl = AutoModel.from_pretrained(self.model_name)
            mdl.eval()
            self._backend = ("hf", tok, mdl)
            # Probe dim (hidden size)
            try:
                self._dim = int(mdl.config.hidden_size)
            except Exception:
                self._dim = 384
            return
        except Exception as e:
            raise ImportError("No transformer embedding backend available") from e

    def _normalize(self, v: np.ndarray) -> np.ndarray:
        if not self.normalize:
            return v.astype("float32")
        n = np.linalg.norm(v)
        if n > 0:
            v = v / n
        return v.astype("float32")

    def embed(self, text: str) -> np.ndarray:
        if not text:
            return np.zeros((self.dim,), dtype="float32")
        if self._backend is None:
            self._init_backend()
        kind = self._backend[0]
        if kind == "st":
            model = self._backend[1]
            try:
                v = model.encode([text], normalize_embeddings=self.normalize)
                return np.asarray(v[0], dtype="float32")
            except Exception:
                return np.zeros((self.dim,), dtype="float32")
        else:
            # transformers
            tok, mdl = self._backend[1], self._backend[2]
            try:
                import torch  # type: ignore
                with torch.no_grad():
                    inputs = tok(text, return_tensors="pt", truncation=True, max_length=self.max_length)
                    out = mdl(**inputs)
                    last = out.last_hidden_state  # [1, T, H]
                    v = torch.mean(last, dim=1).squeeze(0).cpu().numpy()
                return self._normalize(v)
            except Exception:
                return np.zeros((self.dim,), dtype="float32")

