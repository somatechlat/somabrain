"""Governed HRR superposition trace with decay, rotation, and cleanup.

This module implements the core mathematical constructs required by the
SomaBrain v3.0 roadmap for interference governance. It provides a
`SuperposedTrace` class that maintains an exponentially decayed HRR state,
optionally applies deterministic orthogonal rotations to key vectors, and can
perform nearest-neighbour cleanup against a managed anchor set. The design is
compatible with the existing `QuantumLayer` binder and keeps the API narrow so
it can slot into the upcoming memory service refactor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

import numpy as np

from somabrain.quantum import HRRConfig, QuantumLayer


@dataclass(frozen=True)
class TraceConfig:
    """Configuration parameters for :class:`SuperposedTrace`.

    Attributes
    ----------
    dim:
        Dimensionality of the HRR space.
    eta:
        Exponential decay/injection factor. Values in (0, 1]. When set to 1 the
        state becomes the latest binding; values <1 retain history with bounded
        interference.
    rotation_enabled:
        Controls whether keys are rotated before binding. Rotations help keep
        tenant namespaces spectrally independent.
    rotation_seed:
        Seed for the deterministic orthogonal matrix when rotations are
        enabled.
    cleanup_topk:
        The number of best anchors to evaluate during cleanup when a custom ANN
        index is not supplied.
    epsilon:
        Numerical guard to avoid division by zero during renormalisation.
    """

    dim: int = 1024
    eta: float = 0.08
    rotation_enabled: bool = True
    rotation_seed: int = 0
    cleanup_topk: int = 64
    epsilon: float = 1e-12

    def validate(self) -> "TraceConfig":
        dim = int(self.dim)
        if dim <= 0:
            raise ValueError("dim must be positive")
        eta = float(self.eta)
        if not math.isfinite(eta) or eta <= 0.0 or eta > 1.0:
            raise ValueError("eta must be in (0, 1]")
        cleanup_topk = int(self.cleanup_topk)
        if cleanup_topk <= 0:
            raise ValueError("cleanup_topk must be positive")
        eps = float(self.epsilon)
        if eps <= 0:
            raise ValueError("epsilon must be positive")
        # normalise booleans
        rotation_enabled = bool(self.rotation_enabled)
        seed = int(self.rotation_seed)
        return TraceConfig(
            dim=dim,
            eta=eta,
            rotation_enabled=rotation_enabled,
            rotation_seed=seed,
            cleanup_topk=cleanup_topk,
            epsilon=eps,
        )


class SuperposedTrace:
    """Maintains a decayed HRR superposition with cleanup anchors.

    The trace stores bindings of (key, value) pairs. Keys are optionally passed
    through a deterministic orthonormal matrix before binding to reduce
    structured interference between tenants. Each update applies exponential
    decay so interference remains bounded as the trace size grows.
    """

    def __init__(
        self,
        cfg: TraceConfig,
        *,
        quantum: Optional[QuantumLayer] = None,
        rotation_matrix_factory: Optional[Callable[[int, int], np.ndarray]] = None,
    ) -> None:
        self.cfg = cfg.validate()
        self._q = quantum or QuantumLayer(HRRConfig(dim=self.cfg.dim, seed=self.cfg.rotation_seed))
        self._state = np.zeros((self.cfg.dim,), dtype=np.float32)
        self._anchors: Dict[str, np.ndarray] = {}
        self._rotation = None
        if self.cfg.rotation_enabled:
            factory = rotation_matrix_factory or _make_orthogonal_matrix
            self._rotation = factory(self.cfg.dim, self.cfg.rotation_seed).astype("float32", copy=False)
        self._eta = self.cfg.eta
        self._eps = self.cfg.epsilon

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def state(self) -> np.ndarray:
        """Return a copy of the current superposition vector."""

        return self._state.copy()

    @property
    def anchors(self) -> Dict[str, np.ndarray]:
        """A shallow copy of the managed anchor vectors."""

        return dict(self._anchors)

    @property
    def quantum(self) -> QuantumLayer:
        """Expose the underlying :class:`QuantumLayer` for diagnostics/tests."""

        return self._q

    def upsert(self, anchor_id: str, key: np.ndarray, value: np.ndarray) -> None:
        """Bind *key* and *value*, update the state, and store the anchor.

        The binding uses the configured exponential decay:

        .. math::
            M_{t+1} = (1-\eta) M_t + \eta \cdot bind(Rk, v)

        where :math:`R` is the rotation matrix (identity when disabled).
        """

        key_vec = self._prepare_key(key)
        val_vec = self._ensure_vector(value, "value")
        binding = self._q.bind(key_vec, val_vec)
        self._state = self._decayed_update(binding)
        self._anchors[anchor_id] = val_vec

    def recall_raw(self, key: np.ndarray) -> np.ndarray:
        """Return the unbound vector without cleanup."""

        key_vec = self._prepare_key(key)
        return self._q.unbind(self._state, key_vec)

    def recall(self, key: np.ndarray) -> Tuple[np.ndarray, Tuple[str, float, float]]:
        """Recall a value by key with basic cleanup against managed anchors."""

        raw = self.recall_raw(key)
        best_id, best_score, second_score = self._cleanup(raw)
        return raw, (best_id, best_score, second_score)

    def register_anchor(self, anchor_id: str, vector: np.ndarray) -> None:
        """Register or replace an anchor used for cleanup."""

        self._anchors[anchor_id] = self._ensure_vector(vector, "anchor")

    def remove_anchor(self, anchor_id: str) -> None:
        """Remove an anchor from the cleanup index if it exists."""

        self._anchors.pop(anchor_id, None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _prepare_key(self, key: np.ndarray) -> np.ndarray:
        vec = self._ensure_vector(key, "key")
        if self._rotation is not None:
            vec = self._rotation @ vec
        return vec

    def _decayed_update(self, binding: np.ndarray) -> np.ndarray:
        new_state = (1.0 - self._eta) * self._state + self._eta * binding
        norm = float(np.linalg.norm(new_state))
        if not math.isfinite(norm) or norm <= self._eps:
            return np.zeros_like(self._state)
        return (new_state / norm).astype(np.float32, copy=False)

    def _cleanup(self, query: np.ndarray) -> Tuple[str, float, float]:
        if not self._anchors:
            return "", 0.0, 0.0
        query_vec = self._ensure_vector(query, "cleanup_query")
        best_id = ""
        best_score = -1.0
        second_score = -1.0
        # Evaluate up to cleanup_topk anchors. Deterministic order to aid tests.
        for anchor_id, anchor_vec in list(self._anchors.items())[: self.cfg.cleanup_topk]:
            score = self._q.cosine(query_vec, anchor_vec)
            if score > best_score:
                second_score = best_score
                best_score = score
                best_id = anchor_id
            elif score > second_score:
                second_score = score
        if best_score < 0.0:
            best_score = 0.0
        if second_score < 0.0:
            second_score = 0.0
        return best_id, float(best_score), float(second_score)

    def _ensure_vector(self, vec: np.ndarray, name: str) -> np.ndarray:
        if not isinstance(vec, np.ndarray):
            raise TypeError(f"{name} must be a numpy.ndarray")
        if vec.shape[-1] != self.cfg.dim:
            raise ValueError(f"{name} must have dimension {self.cfg.dim}")
        norm = float(np.linalg.norm(vec))
        if norm <= self._eps or not math.isfinite(norm):
            return np.zeros((self.cfg.dim,), dtype=np.float32)
        return (vec / norm).astype(np.float32, copy=False)


def _make_orthogonal_matrix(dim: int, seed: int) -> np.ndarray:
    """Return a deterministic orthonormal matrix using QR factorisation."""

    rng = np.random.default_rng(int(seed))
    mat = rng.normal(0.0, 1.0, size=(dim, dim)).astype(np.float64)
    q, r = np.linalg.qr(mat)
    # Ensure deterministic sign by normalising diagonal of R
    diag = np.sign(np.diag(r))
    diag[diag == 0] = 1.0
    q *= diag
    return q.astype(np.float32)


__all__ = ["TraceConfig", "SuperposedTrace"]
