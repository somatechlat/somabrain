"""Hybrid Quantum Layer using LearnedUnitaryRoles for production deployment.

This module provides a drop-in replacement for `QuantumLayer` that uses the
`LearnedUnitaryRoles` experimental implementation as the canonical role
generator. It preserves the rest of the `QuantumLayer` API so it can be
instantiated as a drop-in replacement when the runtime enables hybrid math.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from somabrain.quantum import HRRConfig, QuantumLayer


class HybridQuantumLayer(QuantumLayer):
    """QuantumLayer variant that prefers LearnedUnitaryRoles for role generation.

    The implementation performs a lazy import of the experimental
    `LearnedUnitaryRoles` to avoid a hard dependency at import time. If the
    learned roles implementation is not available, this class falls back to
    the parent `QuantumLayer` behavior for role creation.
    """

    def __init__(self, cfg: HRRConfig):
        super().__init__(cfg)
        self._learned_roles: Optional[object] = None
        try:
            from somabrain.math.learned_roles import LearnedUnitaryRoles

            self._learned_roles = LearnedUnitaryRoles(self.cfg.dim)
        except Exception:
            # keep graceful fallback to parent implementation
            self._learned_roles = None

    def make_unitary_role(self, token: str) -> np.ndarray:
        """Generate or load a learned unitary role; fall back to parent on error."""
        if self._learned_roles is not None:
            # deterministic init uses seed xor hash(token) to match parent intent
            seed64 = (int(self.cfg.seed) ^ hash(token)) & ((1 << 64) - 1)
            try:
                self._learned_roles.init_role(token, seed=seed64)
                theta = self._learned_roles.get_role(token)
                # build rfft-sized spectrum and convert to time-domain role
                n_bins = self.cfg.dim // 2 + 1
                H = np.exp(1j * theta[:n_bins])
                from somabrain.numerics import irfft_norm

                role_time = irfft_norm(H, n=self.cfg.dim).astype(self.cfg.dtype)
                self._role_cache[token] = role_time
                self._role_fft_cache[token] = H.astype(np.complex128)
                return role_time
            except Exception:
                # on any failure, fall back to parent behavior
                pass
        return super().make_unitary_role(token)

    def train_role_phases(
        self, token: str, gradient_fn, steps: int = 100, lr: float = 1e-3
    ):
        """Train the learned role phases for `token` using a simple SGD loop.

        gradient_fn: callable(theta) -> gradient on theta (same shape)
        steps: number of SGD steps
        lr: learning rate

        This method persists the updated phases into the LearnedUnitaryRoles store
        if available; otherwise it raises RuntimeError.
        """
        if self._learned_roles is None:
            raise RuntimeError("LearnedUnitaryRoles backend not available")
        # Initialize role deterministically if absent
        seed64 = (int(self.cfg.seed) ^ hash(token)) & ((1 << 64) - 1)
        self._learned_roles.init_role(token, seed=seed64)
        theta = self._learned_roles.get_role(token)
        theta = np.array(theta, dtype=float)
        for _ in range(int(steps)):
            g = gradient_fn(theta)
            theta = theta - float(lr) * np.array(g, dtype=float)
            # wrap phases to [-pi, pi]
            theta = np.mod(theta + np.pi, 2.0 * np.pi) - np.pi
        self._learned_roles.set_role(token, theta)
