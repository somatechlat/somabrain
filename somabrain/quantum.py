"""BHDC quantum layer implementation for SomaBrain.

mask-based composers. Binding is hardware-friendly and invertible by
construction.

Mathematical Properties:
- Spectral properties: |H_k|≈1 for all operations
- Perfect binding invertibility
- Role orthogonality
- Superposition normalization
"""

from __future__ import annotations

from somabrain.metrics_extra.math_metrics import MathematicalMetrics

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from somabrain.math.bhdc_encoder import BHDCEncoder, PermutationBinder
from somabrain.numerics import normalize_array
from somabrain import roles as _roles
from somabrain.seed import seed_to_uint64

try:
    from memory.density import DensityMatrix  # type: ignore
except Exception as exc: raise  # pragma: no cover - optional dependency
    DensityMatrix = None  # type: ignore


@dataclass
class HRRConfig:
    """Configuration for BHDC hyperdimensional operations."""

    dim: int = 2048
    seed: int = 42
    dtype: str = "float32"
    renorm: bool = True
    binding_method: str = "bhdc"
    sparsity: float = 0.1
    binary_mode: str = "pm_one"
    mix: str = "none"
    roles_unitary: bool = True
    binding_seed: Optional[str] = None
    binding_tenant: Optional[str] = None
    binding_model_version: Optional[str] = None

    def __post_init__(self) -> None:
        if self.dim <= 0:
            raise ValueError("HRRConfig.dim must be a positive integer")
        if self.dtype not in ("float32", "float64"):
            raise ValueError("HRRConfig.dtype must be 'float32' or 'float64'")
        method = (self.binding_method or "bhdc").lower()
        if method != "bhdc":
            raise ValueError(f"Unsupported binding_method '{method}'")
        self.binding_method = "bhdc"
        mode = (self.binary_mode or "pm_one").lower()
        if mode not in {"pm_one", "zero_one"}:
            raise ValueError("binary_mode must be 'pm_one' or 'zero_one'")
        self.binary_mode = mode
        mix_mode = (self.mix or "none").lower()
        if mix_mode not in {"none", "hadamard"}:
            raise ValueError("mix must be 'none' or 'hadamard'")
        self.mix = mix_mode
        self.roles_unitary = bool(self.roles_unitary)


class QuantumLayer:
    """BHDC-powered hyperdimensional operations."""

    def __init__(self, cfg: HRRConfig):
        self.cfg = cfg
        self._role_cache: Dict[str, np.ndarray] = {}
        self._role_fft_cache: Dict[str, np.ndarray] = {}
        self._rng = np.random.default_rng(int(cfg.seed))
        self._encoder = BHDCEncoder(
            dim=cfg.dim,
            sparsity=cfg.sparsity,
            base_seed=int(cfg.seed),
            dtype=cfg.dtype,
            extra_seed=cfg.binding_seed,
            tenant_id=cfg.binding_tenant,
            model_version=cfg.binding_model_version,
            binary_mode=cfg.binary_mode,
        )
        self._binder = PermutationBinder(
            dim=cfg.dim,
            seed=int(cfg.seed),
            dtype=cfg.dtype,
            mix=cfg.mix,
        )
        self._perm = self._binder.permutation
        self._perm_inv = self._binder.inverse_permutation

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ensure_vector(self, v: object, *, name: str = "vector") -> np.ndarray:
        try:
            arr = np.asarray(v, dtype=self.cfg.dtype)
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError(f"{name}: cannot convert to ndarray: {exc}")
        if arr.ndim != 1:
            arr = arr.reshape(-1)
        if arr.shape[0] != self.cfg.dim:
            raise ValueError(
                f"{name} must be 1-D of length {self.cfg.dim}, got {arr.shape}"
            )
        return arr

    def _renorm(self, v: np.ndarray) -> np.ndarray:
        if not self.cfg.renorm:
            return v.astype(self.cfg.dtype, copy=False)
        return normalize_array(v, axis=-1, keepdims=False, dtype=self.cfg.dtype)

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------
    def random_vector(self) -> np.ndarray:
        return self._renorm(self._encoder.random_vector())

    def encode_text(self, text: str) -> np.ndarray:
        return self._renorm(self._encoder.vector_for_key(text))

    def superpose(self, *vectors) -> np.ndarray:
        from somabrain.metrics_extra.advanced_math_metrics import (
            AdvancedMathematicalMetrics,
        )

        acc: Optional[np.ndarray] = None

        first_component: Optional[np.ndarray] = None

        for v in vectors:
            items = v if isinstance(v, (list, tuple)) else [v]
            for item in items:
                vec = self._ensure_vector(item, name="superpose_item")
                if first_component is None:
                    first_component = vec
                acc = vec if acc is None else acc + vec

        if acc is None:
            return np.zeros((self.cfg.dim,), dtype=self.cfg.dtype)

        result = self._renorm(acc)

        # Verify conservation laws against the unit-norm invariant
        final_prob = float(np.dot(result, result))
        AdvancedMathematicalMetrics.verify_probability_conservation(
            "superpose",
            1.0,
            final_prob,
        )

        # Measure interference patterns
        if len(vectors) > 1 and first_component is not None:
            interference = float(np.abs(np.dot(first_component, result)) ** 2)
            AdvancedMathematicalMetrics.record_interference(interference)

        return result

    def bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        a_vec = self._ensure_vector(a, name="bind.a")
        b_vec = self._ensure_vector(b, name="bind.b")
        result = self._renorm(self._binder.bind(a_vec, b_vec))

        # Verify spectral properties
        fft_result = np.fft.fft(result)
        MathematicalMetrics.verify_spectral_property("bind", np.abs(fft_result))

        # Verify operation correctness
        cosine_a = self.cosine(a_vec, result)
        MathematicalMetrics.verify_operation_correctness("bind", cosine_a)

        # Record binder condition number for diagnostics
        from somabrain.metrics_extra.advanced_math_metrics import (
            AdvancedMathematicalMetrics,
        )

        denom_abs = np.abs(b_vec)
        min_val = float(np.min(denom_abs)) if denom_abs.size else 0.0
        max_val = float(np.max(denom_abs)) if denom_abs.size else 0.0
        if max_val > 0.0:
            cond = max_val / max(min_val, 1e-12)
            AdvancedMathematicalMetrics.record_binder_condition(cond)

        return result

    def unbind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        a_vec = self._ensure_vector(a, name="unbind.a")
        b_vec = self._ensure_vector(b, name="unbind.b")
        return self._renorm(self._binder.unbind(a_vec, b_vec))

    # ------------------------------------------------------------------
    # Unitary roles
    # ------------------------------------------------------------------
    def make_unitary_role(self, token: str) -> np.ndarray:
        if token in self._role_cache:
            return self._role_cache[token]

        if self.cfg.roles_unitary:
            seed_val = int(seed_to_uint64(f"role|{token}")) ^ int(self.cfg.seed)
            role_time, role_spec = _roles.make_unitary_role(
                self.cfg.dim,
                seed=seed_val,
                dtype=np.float32 if self.cfg.dtype == "float32" else np.float64,
            )
            role = role_time.astype(self.cfg.dtype, copy=False)
            role = self._renorm(role)
            self._role_fft_cache[token] = role_spec.astype(
                np.complex64 if self.cfg.dtype == "float32" else np.complex128
            )
            self._validate_unitary_role(role, self._role_fft_cache[token])
        else:
            seed64 = np.uint64(
                int(seed_to_uint64(f"role|{token}")) ^ int(self.cfg.seed)
            )
            rng = np.random.default_rng(seed64)
            role = rng.normal(0.0, 1.0, size=self.cfg.dim).astype(self.cfg.dtype)
            role = self._renorm(role)

        # Verify orthogonality against existing roles before caching
        if self._role_cache and self.cfg.roles_unitary:
            from somabrain.metrics_extra.advanced_math_metrics import (
                AdvancedMathematicalMetrics,
            )

            for existing_token, existing_role in self._role_cache.items():
                cosine_sim = self.cosine(existing_role, role)
                MathematicalMetrics.verify_role_orthogonality(
                    token, existing_token, cosine_sim
                )
                AdvancedMathematicalMetrics.check_orthogonality(cosine_sim)

        self._role_cache[token] = role
        return role

    def bind_unitary(self, a: np.ndarray, role_token: str) -> np.ndarray:
        from somabrain.metrics_extra.advanced_math_metrics import (
            AdvancedMathematicalMetrics,
        )

        a_vec = self._ensure_vector(a, name="bind_unitary.a")
        role_vec = self.make_unitary_role(role_token)

        # Record initial energies
        initial_energy = np.sum(a_vec * a_vec)

        result = self._renorm(self._binder.bind(a_vec, role_vec))

        # Verify conservation laws
        final_energy = np.sum(result * result)
        AdvancedMathematicalMetrics.verify_energy_conservation(
            "bind_unitary", initial_energy, final_energy
        )

        # Check frame properties if we have enough roles
        if len(self._role_cache) > 1:
            AdvancedMathematicalMetrics.measure_frame_properties(
                list(self._role_cache.values())
            )

        return result

    # ------------------------------------------------------------------
    # Exact / Wiener aliases (BHDC binder is perfectly invertible)
    # ------------------------------------------------------------------
    def unbind_exact(self, c: np.ndarray, b: np.ndarray) -> np.ndarray:
        return self.unbind(c, b)

    def unbind_exact_unitary(self, c: np.ndarray, role_token: str) -> np.ndarray:
        c_vec = self._ensure_vector(c, name="unbind_exact_unitary.c")
        role_vec = self.make_unitary_role(role_token)
        return self._renorm(self._binder.unbind(c_vec, role_vec))

    def unbind_wiener(
        self,
        c: np.ndarray,
        b: np.ndarray | str,
        snr_db: float = 40.0,
        *,
        k_est: int | None = None,
        alpha: float = 1e-3,
        whiten: bool = False,
    ) -> np.ndarray:
        _ = snr_db, k_est, alpha, whiten  # parameters retained for compatibility
        if isinstance(b, str):
            return self.unbind_exact_unitary(c, b)
        return self.unbind(c, b)

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------
    def permute(self, a: np.ndarray, times: int = 1) -> np.ndarray:
        vec = self._ensure_vector(a, name="permute.a")
        return self._binder.permute(vec, times)

    @staticmethod
    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        na = float(np.linalg.norm(a))
        nb = float(np.linalg.norm(b))
        if na <= 0 or nb <= 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def cleanup(
        self,
        q: np.ndarray,
        anchors: Dict[str, np.ndarray],
        *,
        use_wiener: bool = True,
        density_matrix: "DensityMatrix" = None,
        alpha: float = 0.5,
    ) -> tuple[str, float]:
        _ = use_wiener  # retained for signature compatibility
        query = self._ensure_vector(q, name="cleanup.query")
        best_score = -1.0
        best_id = ""
        for key, vec in anchors.items():
            try:
                candidate = self._ensure_vector(vec, name=f"anchor[{key}]")
            except ValueError:
                continue
            score = self.cosine(query, candidate)
            if density_matrix is not None:
                try:
                    score = (
                        alpha * float(density_matrix.score(query, candidate))
                        + (1 - alpha) * score
                    )
                except Exception as exc: raise
            if score > best_score:
                best_score = score
                best_id = key
        return best_id, float(best_score)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def _validate_unitary_role(
        self, role: np.ndarray, spectrum: Optional[np.ndarray]
    ) -> None:
        """Record invariants that prove a role remains unitary."""

        norm = float(np.linalg.norm(role))
        MathematicalMetrics.verify_mathematical_invariant(
            "unitary_role_norm", abs(norm - 1.0)
        )

        from somabrain.metrics_extra.advanced_math_metrics import (
            AdvancedMathematicalMetrics,
        )

        AdvancedMathematicalMetrics.record_numerical_error(abs(norm - 1.0))

        magnitudes = (
            np.abs(spectrum) if spectrum is not None else np.abs(np.fft.rfft(role))
        )
        MathematicalMetrics.verify_spectral_property("unitary_role", magnitudes)

        # Track worst-case deviation for spectral gap diagnostics
        AdvancedMathematicalMetrics.measure_spectral_properties(np.sort(magnitudes))


def make_quantum_layer(cfg: HRRConfig) -> QuantumLayer:
    return QuantumLayer(cfg)


# ---------------------------------------------------------------------------
# Backwards-compatible wrappers
# ---------------------------------------------------------------------------


def bind_unitary(a: np.ndarray, role: object) -> np.ndarray:
    q = QuantumLayer(HRRConfig(dim=len(a), seed=42))
    if isinstance(role, str):
        return q.bind_unitary(a, role)
    return q.bind(a, np.asarray(role))


def unbind_exact_or_tikhonov_or_wiener(
    c: np.ndarray, role: object, snr_db: float | None = None
) -> np.ndarray:
    q = QuantumLayer(HRRConfig(dim=len(c), seed=42))
    if isinstance(role, str):
        return q.unbind_exact_unitary(c, role)
    if snr_db is None:
        return q.unbind(c, np.asarray(role))
    return q.unbind_wiener(c, np.asarray(role), snr_db=snr_db)
