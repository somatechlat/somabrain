"""
Quantum Computing Layer Module for SomaBrain

This module implements hyperdimensional computing operations using High-Dimensional
Representations (HDR) and Hyperdimensional Representation (HRR) techniques. It provides
the mathematical foundation for quantum-inspired cognitive processing in SomaBrain.

Key Features:
- Deterministic text encoding with seeded randomness
- Hyperdimensional vector operations (superposition, binding, unbinding)
- Circular convolution via FFT for efficient binding
- Nearest neighbor cleanup using cosine similarity
- Fixed permutation operations for cognitive transformations
- Token vector caching for performance optimization

Operations:
- Superposition: Normalized sum of vectors
- Binding: Circular convolution (FFT-based)
- Unbinding: Circular correlation (inverse binding)
- Permutation: Fixed random permutation with inverse
- Cleanup: Nearest neighbor search against anchor dictionary

Classes:
    HRRConfig: Configuration for hyperdimensional parameters
    QuantumLayer: Main hyperdimensional computing layer

Functions:
    _seed64: Deterministic seeding function for reproducibility
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

from somabrain.nano_profile import HRR_FFT_EPSILON


def _seed64(text: str) -> int:
    # Return a 64-bit integer derived from blake2b in little-endian order
    h = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "little")


@dataclass
class HRRConfig:
    """Configuration for HRR operations.

    Math contract (defaults chosen for tiny-compute friendliness):
    - dim: vector dimensionality (power-of-two recommended for FFT performance)
    - seed: global RNG seed for determinism
    - dtype: floating dtype for dense vectors
    - renorm: whether to renormalize outputs to unit norm after ops
    """

    dim: int = 2048  # tiny-compute default
    seed: int = 42
    dtype: str = "float32"
    renorm: bool = True
    # Optional override for FFT regularization epsilon; if None, falls back to
    # the global HRR_FFT_EPSILON from `nano_profile`.
    # By default use the project-wide HRR_FFT_EPSILON; callers can still override.
    fft_eps: Optional[float] = HRR_FFT_EPSILON
    # Spectral regularization multiplier. If None, a conservative default is used.
    beta: Optional[float] = 1e-6
    # When True enforce pure HRR algebra and numerics (no spectral heuristics):
    # - tiny-floor = eps_machine * D
    # - unbind uses exact frequency-domain division with eps = tiny-floor
    # - normalize raises on sub-tiny norms
    strict_math: bool = False
    # Strategy for compute_tiny_floor: 'sqrt' (recommended) or 'linear' (legacy)
    tiny_floor_strategy: str = "sqrt"
    # When True, enable helpers for unitary role generation and exact unbinding
    roles_unitary: bool = True

    def __post_init__(self):
        # Basic validation to avoid surprising misconfiguration
        if not isinstance(self.dim, int) or self.dim <= 0:
            raise ValueError("HRRConfig.dim must be a positive int")
            # Allow any positive integer dimensionality. For very small dims
            # warn the user (tests and examples commonly use 128/256 for speed).
            import warnings

            if self.dim < 8:
                warnings.warn(
                    "HRRConfig.dim is unusually small (<8); numerical results may be degenerate."
                )
        if self.dtype not in ("float32", "float64"):
            raise ValueError("HRRConfig.dtype must be 'float32' or 'float64'")
        # Allow None to mean "use global HRR_FFT_EPSILON"; otherwise ensure positive
        if self.fft_eps is not None and float(self.fft_eps) <= 0.0:
            raise ValueError("HRRConfig.fft_eps must be a small positive float or None")


class QuantumLayer:
    """Hyperdimensional ops (HRR) with deterministic seeding and FFT binding.

    - superpose: normalized sum
    - bind: circular convolution via FFT
    - unbind: circular correlation via FFT (inverse binding)
    - permute: fixed random permutation (seeded)
    - cleanup: nearest by cosine against anchor dictionary
    """

    def __init__(self, cfg: HRRConfig):
        """
        QuantumLayer constructor.
        Enforces global HRR_DIM, HRR_DTYPE, SEED, and vector family (Gaussian, unit-norm).
        Stores and documents permutation π's seed for reproducibility.
        """
        self.cfg = cfg
        # Use the provided global seed directly; text encoding will mix with
        # blake2b-derived little-endian seed via XOR to ensure deterministic
        # but domain-specific streams.
        self._rng = np.random.default_rng(np.uint64(cfg.seed))
        self._perm_seed = cfg.seed  # Store permutation seed for reproducibility
        self._perm = self._rng.permutation(cfg.dim)
        self._perm_inv = np.argsort(self._perm)
        # cache random base vectors for tokens if needed later
        self._token_cache: Dict[str, np.ndarray] = {}
        # cache for unitary role time-domain vectors and their spectra (rfft)
        self._role_cache: Dict[str, np.ndarray] = {}
        self._role_fft_cache: Dict[str, np.ndarray] = {}

    def _to_dtype(self, v: np.ndarray) -> np.ndarray:
        return v.astype(self.cfg.dtype, copy=False)

    def _ensure_vector(self, v: object, name: str = "vector") -> np.ndarray:
        """
        Ensure the provided object is a 1-D numpy vector of the configured dimension
        and dtype. Returns the converted numpy array (not renormalized).
        Raises ValueError for contract violations.
        """
        if isinstance(v, np.ndarray):
            arr = v
        else:
            try:
                arr = np.asarray(v, dtype=self.cfg.dtype)
            except Exception as e:
                raise ValueError(f"{name}: cannot convert to ndarray: {e}")
        if arr.ndim != 1:
            arr = arr.reshape(-1)
        if arr.shape[0] != self.cfg.dim:
            raise ValueError(
                f"{name} must be 1-D of length {self.cfg.dim}, got {arr.shape}"
            )
        # ensure dtype
        if arr.dtype != np.dtype(self.cfg.dtype):
            arr = arr.astype(self.cfg.dtype)
        return arr

    def _renorm(self, v: np.ndarray) -> np.ndarray:
        if not self.cfg.renorm:
            return self._to_dtype(v)
        # Use canonical normalization helper to ensure consistent tiny-floor
        from somabrain.numerics import normalize_array

        return normalize_array(
            v, self.cfg.dim, self.cfg.dtype, raise_on_subtiny=bool(self.cfg.strict_math)
        )

    def random_vector(self) -> np.ndarray:
        """
        Generate a random base vector from the global Gaussian family, always unit-norm.
        Uses global HRR_DIM, HRR_DTYPE, and SEED for reproducibility.
        """
        v = self._rng.normal(0.0, 1.0, size=self.cfg.dim)
        return self._renorm(v)

    def encode_text(self, text: str) -> np.ndarray:
        """
        Deterministic encoding using seeded RNG based on text and global seed.
        Output is always unit-norm, Gaussian family, and reproducible.
        """
        # Strict deterministic pipeline: blake2b-64 (little-endian) XOR global
        # seed, then cast to uint64 for numpy.default_rng reproducibility.
        seed64 = _seed64(text) ^ int(self.cfg.seed)
        rng = np.random.default_rng(np.uint64(seed64))
        v = rng.normal(0.0, 1.0, size=self.cfg.dim)
        return self._renorm(v)

    def superpose(self, *vectors) -> np.ndarray:
        """
        Superpose multiple vectors by normalized summation.

        Parameters
        ----------
        *vectors : np.ndarray
            Variable number of vectors to superpose. Each argument can be a single
            numpy array or an iterable of arrays.

        Returns
        -------
        np.ndarray
            Normalized superposition of all input vectors.
        """
        s: Optional[np.ndarray] = None
        for v in vectors:
            # allow passing iterables of vectors or single vectors
            if isinstance(v, (list, tuple)):
                for x in v:
                    xv = self._ensure_vector(x, name="superpose_item")
                    s = xv if s is None else (s + xv)
            else:
                xv = self._ensure_vector(v, name="superpose_item")
                s = xv if s is None else (s + xv)
        if s is None:
            return self._to_dtype(np.zeros((self.cfg.dim,), dtype=self.cfg.dtype))
        return self._renorm(s)

    def bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """
        Bind two vectors using circular convolution (FFT-based), with epsilon for stability.
        """
        a = self._ensure_vector(a, name="bind.a")
        b = self._ensure_vector(b, name="bind.b")
        # FFT-based circular convolution for binding
        fa = np.fft.rfft(a)
        fb = np.fft.rfft(b)
        prod = fa * fb
        conv = np.fft.irfft(prod, n=self.cfg.dim)
        return self._renorm(conv)

    # --- Unitary Roles Helpers -------------------------------------------------
    def make_unitary_role(self, token: str) -> np.ndarray:
        """
        Generate a deterministic unitary role vector for a given token.

        The role is constructed by sampling random phases in the frequency domain
        (non-redundant rFFT bins) with unit magnitude, ensuring that binding with
        this role is an isometry (preserves L2 norm). The corresponding real-valued
        time-domain vector is obtained via irfft. Both time-domain vector and its
        spectrum are cached for reuse.
        """
        if token in self._role_cache and token in self._role_fft_cache:
            return self._role_cache[token]
        D = self.cfg.dim
        n_bins = D // 2 + 1
        seed64 = _seed64(f"role::{token}") ^ int(self.cfg.seed)
        rng = np.random.default_rng(np.uint64(seed64))
        phases = rng.uniform(0.0, 2.0 * np.pi, size=n_bins).astype("float64")
        H = np.exp(1j * phases)
        # For real irfft, DC (0) and Nyquist (if even length) bins should be real
        H[0] = 1.0 + 0.0j
        if D % 2 == 0:
            H[-1] = 1.0 + 0.0j
        role_time = np.fft.irfft(H, n=D).astype(self.cfg.dtype)
        self._role_cache[token] = role_time
        self._role_fft_cache[token] = H.astype(np.complex128)
        return role_time

    def bind_unitary(self, a: np.ndarray, role_token: str) -> np.ndarray:
        """Bind vector a with a unitary role identified by token (isometric)."""
        a = self._ensure_vector(a, name="bind_unitary.a")
        H = self._role_fft_cache.get(role_token)
        if H is None:
            _ = self.make_unitary_role(role_token)
            H = self._role_fft_cache[role_token]
        fa = np.fft.rfft(a)
        conv = np.fft.irfft(fa * H, n=self.cfg.dim)
        return self._renorm(conv)

    def unbind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """
        Unbind two vectors using circular correlation (FFT-based), with epsilon for stability.
        """
        # validate inputs
        a = self._ensure_vector(a, name="unbind.a")
        b = self._ensure_vector(b, name="unbind.b")

        # FFT-based circular correlation (deconvolution) with Tikhonov-like regularization
        fa = np.fft.rfft(a)
        fb = np.fft.rfft(b)

        # Spectral-adaptive regularization
        # compute power spectrum S = |FB|^2 (elementwise)
        S = (fb * np.conjugate(fb)).real

        # dtype_floor derived from machine eps scaled by sqrt(dim)
        from somabrain.numerics import compute_tiny_floor

        dtype_floor = compute_tiny_floor(
            self.cfg.dtype, self.cfg.dim, strategy=self.cfg.tiny_floor_strategy
        )
        # dtype_floor is an amplitude (||x||_2) threshold. Convert to a power
        # per-frequency-bin floor to match S = |FB|^2 units.
        power_floor_per_bin = float(dtype_floor) ** 2 / float(self.cfg.dim)

        # base_eps comes from config or global fallback
        base_eps = (
            float(self.cfg.fft_eps)
            if (self.cfg.fft_eps is not None)
            else float(HRR_FFT_EPSILON)
        )
        # Interpret base_eps as a power-floor if it looks like a small number
        # intended for spectra; ensure we compare power-to-power.
        base_eps_power = float(base_eps)
        power_floor_per_bin = max(power_floor_per_bin, base_eps_power)

        # spectral floor scales with mean spectral energy
        if self.cfg.strict_math:
            # Pure algebraic division: use power_floor_per_bin in power units
            eps_used = power_floor_per_bin
            denom = (S + eps_used).astype(np.float64)
            prod = (fa * np.conjugate(fb)).astype(np.complex128) / denom
            corr = np.fft.irfft(prod, n=self.cfg.dim).astype(self.cfg.dtype)
            return self._renorm(corr)

        # spectral floor scales with mean spectral energy (robust fallback)
        beta = self.cfg.beta if (self.cfg.beta is not None) else 1e-6
        spectral_floor = float(beta) * float(np.mean(S))

        eps_used = max(power_floor_per_bin, spectral_floor)

        # Optionally compute denom in float64 for better stability then cast back
        denom = (S + eps_used).astype(np.float64)
        prod = (fa * np.conjugate(fb)).astype(np.complex128) / denom
        # Cast result back to runtime dtype before renormalization
        corr = np.fft.irfft(prod, n=self.cfg.dim).astype(self.cfg.dtype)
        # metrics: robust/tikhonov-like path
        try:
            from somabrain import metrics as M

            M.UNBIND_PATH.labels(path="robust").inc()
        except Exception:
            pass
        return self._renorm(corr)

    def unbind_exact(self, c: np.ndarray, b: np.ndarray) -> np.ndarray:
        """
        Exact frequency-domain unbinding (deconvolution) with float64 intermediates.

        This method is intended for use with unitary roles where the spectrum has
        unit magnitude (|H|=1), making the operation numerically stable and
        isometric. For general vectors, consider using the robust `unbind` method.
        """
        c = self._ensure_vector(c, name="unbind_exact.c")
        b = self._ensure_vector(b, name="unbind_exact.b")
        fc = np.fft.rfft(c).astype(np.complex128)
        fb = np.fft.rfft(b).astype(np.complex128)
        # Use a minimal epsilon derived from dtype floor to avoid accidental div/0
        from somabrain.numerics import compute_tiny_floor

        eps = compute_tiny_floor(
            self.cfg.dtype, self.cfg.dim, strategy=self.cfg.tiny_floor_strategy
        )
        denom = fb.copy()
        # If any bin is effectively zero, nudge by eps on the diagonal (rare for unitary roles)
        zero_mask = np.isclose(denom, 0 + 0j, atol=eps)
        if np.any(zero_mask):
            denom[zero_mask] = denom[zero_mask] + eps
        fa_est = fc / denom
        a_est = np.fft.irfft(fa_est, n=self.cfg.dim).astype(self.cfg.dtype)
        try:
            from somabrain import metrics as M

            M.UNBIND_PATH.labels(path="exact").inc()
        except Exception:
            pass
        return self._renorm(a_est)

    def unbind_exact_unitary(self, c: np.ndarray, role_token: str) -> np.ndarray:
        """Exact unbinding using cached unitary role spectrum for maximum stability."""
        c = self._ensure_vector(c, name="unbind_exact_unitary.c")
        H = self._role_fft_cache.get(role_token)
        if H is None:
            _ = self.make_unitary_role(role_token)
            H = self._role_fft_cache[role_token]
        fc = np.fft.rfft(c).astype(np.complex128)
        a_est = np.fft.irfft(fc / H, n=self.cfg.dim).astype(self.cfg.dtype)
        try:
            from somabrain import metrics as M

            M.UNBIND_PATH.labels(path="exact_unitary").inc()
        except Exception:
            pass
        return self._renorm(a_est)

    def unbind_wiener(
        self,
        c: np.ndarray,
        b: np.ndarray,
        snr_db: float = 40.0,
        *,
        k_est: int | None = None,
        alpha: float = 1e-3,
        whiten: bool = False,
    ) -> np.ndarray:
        """
        Wiener (MAP) unbinding with SNR (dB) parameterization.

        Implements conj(B) / (|B|^2 + 1/SNR) filter with float64 intermediates,
        mapping SNR(dB) to linear SNR for the additive spectral floor.
        """
        c = self._ensure_vector(c, name="unbind_wiener.c")
        b = self._ensure_vector(b, name="unbind_wiener.b")
        fc = np.fft.rfft(c).astype(np.complex128)
        fb = np.fft.rfft(b).astype(np.complex128)

        # Optional env overrides
        try:
            import os as _os

            _snr = _os.getenv("SOMABRAIN_WIENER_SNR_DB", "").strip() or None
            if _snr is not None:
                snr_db = float(_snr)
            _alpha = _os.getenv("SOMABRAIN_WIENER_ALPHA", "").strip() or None
            if _alpha is not None:
                alpha = float(_alpha)
            _wh = _os.getenv("SOMABRAIN_WIENER_WHITEN", "").strip().lower() or ""
            if _wh in ("1", "true", "yes", "on"):
                whiten = True
            if _wh in ("0", "false", "no", "off"):
                whiten = False
        except Exception:
            pass
        S = (fb * np.conjugate(fb)).real.astype(np.float64)
        snr = float(10.0 ** (snr_db / 10.0))
        floor_snr = 1.0 / max(snr, 1e-12)
        # k-aware adaptive floor: scales with mean spectral energy and estimated k
        k_term = max(1, int(k_est)) if k_est is not None else 1
        S_mean = float(np.mean(S)) if S.size else 1.0
        adapt = float(alpha) * k_term * S_mean
        floor = max(floor_snr, adapt)
        if not whiten:
            denom = S + floor
            fa_est = (fc * np.conjugate(fb).astype(np.complex128)) / denom
        else:
            # Spectral whitening: normalize role magnitude to ~1 per bin.
            eps = 1e-12
            fb_u = fb / np.sqrt(S + eps)
            # Map constant floor into the whitened domain by average power.
            floor_u = floor / (S_mean + eps)
            denom_u = 1.0 + floor_u
            fa_est = (fc * np.conjugate(fb_u).astype(np.complex128)) / denom_u
        a_est = np.fft.irfft(fa_est, n=self.cfg.dim).astype(self.cfg.dtype)
        try:
            from somabrain import metrics as M

            M.UNBIND_PATH.labels(path="wiener").inc()
            M.UNBIND_WIENER_FLOOR.set(float(floor))
            if k_est is not None:
                M.UNBIND_K_EST.set(float(k_est))
        except Exception:
            pass
        return self._renorm(a_est)

    def permute(self, a: np.ndarray, times: int = 1) -> np.ndarray:
        a = self._ensure_vector(a, name="permute.a")
        if times >= 0:
            idx = self._perm
            for _ in range(times):
                a = a[idx]
            return a
        # negative times means inverse
        idx = self._perm_inv
        for _ in range(-times):
            a = a[idx]
        return a

    @staticmethod
    def cosine(a: np.ndarray, b: np.ndarray, tiny_floor: float = 0.0) -> float:
        na = float(np.linalg.norm(a))
        nb = float(np.linalg.norm(b))
        # If tiny_floor supplied, use it to detect numerical singularity;
        # otherwise fall back to previous non-strict check to preserve behavior.
        if tiny_floor > 0.0:
            if na < tiny_floor or nb < tiny_floor:
                return 0.0
        else:
            if na <= 0 or nb <= 0:
                return 0.0
        return float(np.dot(a, b) / (na * nb))

    def cleanup(
        self, q: np.ndarray, anchors: Dict[str, np.ndarray]
    ) -> Tuple[str, float]:
        q = self._ensure_vector(q, name="cleanup.query")
        best_id = ""
        best = -1.0
        from somabrain.numerics import compute_tiny_floor

        tiny = compute_tiny_floor(
            self.cfg.dtype, self.cfg.dim, strategy=self.cfg.tiny_floor_strategy
        )
        for k, v in anchors.items():
            try:
                vv = self._ensure_vector(v, name=f"cleanup.anchor[{k}]")
            except ValueError:
                # skip anchors that don't meet the contract
                continue
            s = self.cosine(q, vv, tiny_floor=tiny)
            if s > best:
                best = s
                best_id = k
        return best_id, best
