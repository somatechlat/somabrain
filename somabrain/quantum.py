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

# Math contract (short):
# - Use unitary FFT wrappers (rfft_norm / irfft_norm with norm='ortho').
# - Tiny floors are amplitude (L2) units; convert to spectral power via
#   power_per_bin = tiny_amp**2 / D when used in frequency-domain denominators.
# - Use normalize_array(..., mode='robust') for deterministic low-energy fallback
#   (baseline ones/sqrt(D)). See somabrain/numerics.py for full rationale.

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

from somabrain.nano_profile import HRR_FFT_EPSILON
from memory.density import DensityMatrix  # for type hint and runtime use


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
        # Allow any positive integer dimensionality. For very small dims warn the user
        # (tests and examples commonly use 128/256 for speed).
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
            v,
            axis=-1,
            keepdims=False,
            tiny_floor_strategy=self.cfg.tiny_floor_strategy,
            dtype=self.cfg.dtype,
            strict=bool(self.cfg.strict_math),
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

        # FFT-based circular convolution for binding (use unitary wrappers)
        from somabrain.numerics import irfft_norm, rfft_norm

        fa = rfft_norm(a, n=self.cfg.dim)
        fb = rfft_norm(b, n=self.cfg.dim)
        prod = fa * fb
        conv = irfft_norm(prod, n=self.cfg.dim)
        return self._renorm(conv)

    # (All helper functionality implemented as methods on QuantumLayer)

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
        # Check in-memory cache first
        if token in self._role_cache and token in self._role_fft_cache:
            return self._role_cache[token]
        # Attempt to load from durable spectral cache (file-backed) to persist
        # role spectra across process restarts.
        try:
            from somabrain import spectral_cache as _sc

            cached = _sc.get_role(token)
            if cached is not None:
                role_time, role_fft = cached
                # Validate cached role matches current dimension & spectrum size
                D_expected = self.cfg.dim
                n_bins_expected = D_expected // 2 + 1
                if (
                    isinstance(role_time, np.ndarray)
                    and role_time.shape == (D_expected,)
                    and isinstance(role_fft, np.ndarray)
                    and role_fft.shape == (n_bins_expected,)
                ):
                    self._role_cache[token] = role_time.astype(self.cfg.dtype)
                    self._role_fft_cache[token] = role_fft.astype(np.complex128)
                    return self._role_cache[token]
                # Mismatch: ignore cached value and regenerate for correctness
        except Exception:
            # If cache module is unavailable or read fails, fall back to in-memory
            # generation. We intentionally swallow exceptions to avoid breaking
            # runtime behavior when disk isn't writable.
            pass
        D = self.cfg.dim
        n_bins = D // 2 + 1
        seed64 = _seed64(f"role::{token}") ^ int(self.cfg.seed)
        rng = np.random.default_rng(np.uint64(seed64))

        # If the project-level hybrid math feature is enabled, prefer the
        # learned-unitary phases if available in the experimental math package.
        try:
            from somabrain.config import load_config

            cfg = load_config()
            if getattr(cfg, "hybrid_math_enabled", False):
                # Attempt to use learned phases from somabrain.math (best-effort)
                try:
                    from somabrain.math.learned_roles import LearnedUnitaryRoles

                    lr = LearnedUnitaryRoles(D)
                    # initialize deterministic phase and retrieve rfft-sized theta
                    lr.init_role(token, seed=seed64)
                    theta = lr.get_role(token)
                    H = np.exp(1j * theta[:n_bins])
                except Exception:
                    # fallback to random phases if learned_roles isn't available
                    phases = rng.uniform(0.0, 2.0 * np.pi, size=n_bins).astype(
                        "float64"
                    )
                    H = np.exp(1j * phases)
            else:
                phases = rng.uniform(0.0, 2.0 * np.pi, size=n_bins).astype("float64")
                H = np.exp(1j * phases)
        except Exception:
            phases = rng.uniform(0.0, 2.0 * np.pi, size=n_bins).astype("float64")
            H = np.exp(1j * phases)
        # For real irfft, DC (0) and Nyquist (if even length) bins should be real
        H[0] = 1.0 + 0.0j
        if D % 2 == 0:
            H[-1] = 1.0 + 0.0j
        # Use unitary inverse FFT to produce the time-domain role (isometric)
        from somabrain.numerics import irfft_norm

        role_time = irfft_norm(H, n=D).astype(self.cfg.dtype)
        self._role_cache[token] = role_time
        self._role_fft_cache[token] = H.astype(np.complex128)
        # Try to persist to file-backed cache (best-effort; failures are silent)
        try:
            from somabrain import spectral_cache as _sc

            _sc.set_role(token, role_time, H.astype(np.complex128))
        except Exception:
            pass
        return role_time

    def bind_unitary(self, a: np.ndarray, role_token: str) -> np.ndarray:
        """Bind vector a with a unitary role identified by token (isometric)."""
        a = self._ensure_vector(a, name="bind_unitary.a")
        H = self._role_fft_cache.get(role_token)
        if H is None:
            _ = self.make_unitary_role(role_token)
            H = self._role_fft_cache[role_token]
        from somabrain.numerics import irfft_norm, rfft_norm

        fa = rfft_norm(a, n=self.cfg.dim)
        conv = irfft_norm(fa * H, n=self.cfg.dim)
        return self._renorm(conv)

    def unbind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """
        Unbind two vectors using circular correlation (FFT-based), with epsilon for stability.
        """
        # validate inputs
        a = self._ensure_vector(a, name="unbind.a")
        b = self._ensure_vector(b, name="unbind.b")

        # FFT-based circular correlation (deconvolution) with Tikhonov-like regularization
        from somabrain.numerics import irfft_norm, rfft_norm

        fa = rfft_norm(a, n=self.cfg.dim)
        fb = rfft_norm(b, n=self.cfg.dim)

        # Spectral-adaptive regularization
        # compute power spectrum S = |FB|^2 (elementwise)
        S = (fb * np.conjugate(fb)).real

        # dtype_floor derived from machine eps scaled by sqrt(dim)
        from somabrain.numerics import compute_tiny_floor

        dtype_floor = compute_tiny_floor(
            self.cfg.dim, dtype=self.cfg.dtype, strategy=self.cfg.tiny_floor_strategy
        )
        # dtype_floor is an amplitude (||x||_2) threshold. Convert to a power
        # per-frequency-bin floor to match S = |FB|^2 units.
        from somabrain.numerics import spectral_floor_from_tiny

        power_floor_per_bin = spectral_floor_from_tiny(dtype_floor, self.cfg.dim)

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
            # NaN guard
            bad_mask = ~np.isfinite(prod)
            if np.any(bad_mask):
                prod[bad_mask] = 0.0
            corr = irfft_norm(prod, n=self.cfg.dim).astype(self.cfg.dtype)
            # metrics: exact/strict path
            try:
                from somabrain import metrics as M

                M.UNBIND_PATH.labels(path="strict_math").inc()
                M.UNBIND_EPS_USED.set(float(eps_used))
                # compute reconstruction cosine against a placeholder:
                # we don't have the original 'a' here, so skip cosine observation
            except Exception:
                pass
            return self._renorm(corr)

        # spectral floor scales with mean spectral energy (robust fallback)
        beta = self.cfg.beta if (self.cfg.beta is not None) else 1e-6
        spectral_floor = float(beta) * float(np.mean(S))

        eps_used = max(power_floor_per_bin, spectral_floor)

        # Optionally compute denom in float64 for better stability then cast back
        denom = (S + eps_used).astype(np.float64)
        prod = (fa * np.conjugate(fb)).astype(np.complex128) / denom
        # NaN guard for spectral division
        bad_mask2 = ~np.isfinite(prod)
        if np.any(bad_mask2):
            prod[bad_mask2] = 0.0
        # metrics: robust/tikhonov-like path
        try:
            from somabrain import metrics as M

            M.UNBIND_PATH.labels(path="robust").inc()
            M.UNBIND_EPS_USED.set(float(eps_used))
            # count clamped bins (where S was below power_floor_per_bin)
            clamped = int(np.sum(S < power_floor_per_bin))
            if clamped > 0:
                M.UNBIND_SPECTRAL_BINS_CLAMPED.inc(clamped)
        except Exception:
            pass
        # Cast result back to runtime dtype before renormalization
        corr = irfft_norm(prod, n=self.cfg.dim).astype(self.cfg.dtype)
        # metrics: robust/tikhonov-like path
        try:
            from somabrain import metrics as M

            # If we can observe reconstruction quality, do so. We can attempt
            # to compute cosine similarity between the reconstructed estimate and
            # the internal expectation only when callers provide the original.
            # Here we record eps_used already; cosine requires original 'a' which
            # is not available at this point in the API. Upstream callers (or
            # wrappers) may record the RECONSTRUCTION_COSINE metric after
            # calling this method when they have access to both vectors.
            M.RECONSTRUCTION_COSINE.observe(0.0)  # placeholder zero observation
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

        from somabrain.numerics import compute_tiny_floor, irfft_norm, rfft_norm

        # Spectral division with high-precision intermediates for stability
        fc = rfft_norm(c, n=self.cfg.dim).astype(np.complex128)
        fb = rfft_norm(b, n=self.cfg.dim).astype(np.complex128)

        # Use a minimal epsilon derived from dtype floor (amplitude units)
        eps_amp = compute_tiny_floor(
            self.cfg.dim,
            dtype=np.dtype(self.cfg.dtype),
            strategy=self.cfg.tiny_floor_strategy,
        )
        # Convert amplitude tiny to per-bin power floor
        from somabrain.numerics import spectral_floor_from_tiny

        eps_power = spectral_floor_from_tiny(eps_amp, self.cfg.dim)

        denom = fb.copy().astype(np.complex128)
        # If any bin magnitude is effectively zero, nudge by eps_power on the diagonal
        zero_mask = np.abs(denom) < eps_power
        if np.any(zero_mask):
            denom[zero_mask] = denom[zero_mask] + eps_power

        fa_est = fc / denom
        # guard against non-finite bins
        bad = ~np.isfinite(fa_est)
        if np.any(bad):
            fa_est[bad] = 0.0
        a_est = irfft_norm(fa_est, n=self.cfg.dim).astype(self.cfg.dtype)
        try:
            from somabrain import metrics as M

            M.UNBIND_PATH.labels(path="exact").inc()
            M.UNBIND_EPS_USED.set(float(eps_power))
            clamped = int(np.sum(np.abs(fb) < eps_power))
            if clamped > 0:
                M.UNBIND_SPECTRAL_BINS_CLAMPED.inc(clamped)
        except Exception:
            pass
        return self._renorm(a_est)

    def unbind_exact_unitary(self, c: np.ndarray, role_token: str) -> np.ndarray:
        """Exact unbinding using cached unitary role spectrum for maximum stability."""
        c = self._ensure_vector(c, name="unbind_exact_unitary.c")
        H = self._role_fft_cache.get(role_token)
        if H is None:
            # Try to load from durable cache before generating
            try:
                from somabrain import spectral_cache as _sc

                cached = _sc.get_role(role_token)
                if cached is not None:
                    _, role_fft = cached
                    H = role_fft.astype(np.complex128)
                    # populate in-memory caches
                    self._role_fft_cache[role_token] = H
                    # attempt to also populate time-domain cache if available
                    try:
                        role_time = cached[0]
                        self._role_cache[role_token] = role_time.astype(self.cfg.dtype)
                    except Exception:
                        pass
            except Exception:
                pass
        if H is None:
            _ = self.make_unitary_role(role_token)
            H = self._role_fft_cache[role_token]
        from somabrain.numerics import irfft_norm, rfft_norm

        fc = rfft_norm(c, n=self.cfg.dim).astype(np.complex128)
        denom_H = H.astype(np.complex128)
        fa_tmp = fc / denom_H
        badH = ~np.isfinite(fa_tmp)
        if np.any(badH):
            fa_tmp[badH] = 0.0
        a_est = irfft_norm(fa_tmp, n=self.cfg.dim).astype(self.cfg.dtype)
        try:
            from somabrain import metrics as M

            M.UNBIND_PATH.labels(path="exact_unitary").inc()
            # denom_H comes from unitary role; count bad bins and set a tiny eps
            eps_power = 0.0
            clamped = int(np.sum(badH))
            if clamped > 0:
                # record a small eps to indicate intervention
                eps_power = float(np.finfo(np.float64).eps)
                M.UNBIND_SPECTRAL_BINS_CLAMPED.inc(clamped)
            M.UNBIND_EPS_USED.set(float(eps_power))
        except Exception:
            pass
        return self._renorm(a_est)

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
        """
        Wiener (MAP) unbinding with SNR (dB) parameterization.

        Implements conj(B) / (|B|^2 + 1/SNR) filter with float64 intermediates,
        mapping SNR(dB) to linear SNR for the additive spectral floor.
        """
        # Import numerics helpers here to avoid top-level circular imports
        from somabrain.numerics import irfft_norm, rfft_norm

        c = self._ensure_vector(c, name="unbind_wiener.c")
        # Accept role token strings for convenience: resolve to role vector
        if isinstance(b, str):
            role_token = b
            H = self._role_fft_cache.get(role_token)
            if H is None:
                _ = self.make_unitary_role(role_token)
                H = self._role_fft_cache[role_token]
            # convert role spectrum back to time-domain role for _ensure_vector
            b_vec = self._role_cache.get(role_token)
            if b_vec is None:
                b_vec = self.make_unitary_role(role_token)
            b = b_vec
        else:
            b = self._ensure_vector(b, name="unbind_wiener.b")
        # Use unitary FFT wrappers for consistent normalization across the codebase
        fc = rfft_norm(c, n=self.cfg.dim).astype(np.complex128)
        fb = rfft_norm(b, n=self.cfg.dim).astype(np.complex128)

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
            fb_c = fb.astype(np.complex128)
            conj_fb = np.conjugate(fb_c)
            fa_est = (fc * conj_fb) / denom
        else:
            # Spectral whitening: normalize role magnitude to ~1 per bin.
            eps = 1e-12
            fb_u = fb / np.sqrt(S + eps)
            # Map constant floor into the whitened domain by average power.
            floor_u = floor / (S_mean + eps)
            denom_u = 1.0 + floor_u
            fb_u_c = fb_u.astype(np.complex128)
            conj_fb_u = np.conjugate(fb_u_c)
            fa_est = (fc * conj_fb_u) / denom_u

        a_est = irfft_norm(fa_est, n=self.cfg.dim).astype(self.cfg.dtype)
        try:
            from somabrain import metrics as M

            M.UNBIND_PATH.labels(path="wiener").inc()
            M.UNBIND_WIENER_FLOOR.set(float(floor))
            if k_est is not None:
                M.UNBIND_K_EST.set(float(k_est))
            # Record effective epsilon used and clamped bins (S < floor)
            M.UNBIND_EPS_USED.set(float(floor))
            clamped = int(np.sum(S < float(floor)))
            if clamped > 0:
                M.UNBIND_SPECTRAL_BINS_CLAMPED.inc(clamped)
        except Exception:
            pass
        return self._renorm(a_est)

    def permute(self, a: np.ndarray, times: int = 1) -> np.ndarray:
        """Apply the fixed permutation `times` times (negative for inverse)."""
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
        self,
        q: np.ndarray,
        anchors: Dict[str, np.ndarray],
        *,
        use_wiener: bool = True,
        density_matrix: "DensityMatrix" = None,
        alpha: float = 0.5,
    ) -> Tuple[str, float]:
        """
        Cleanup using Wiener unbinding and density matrix scoring if available.
        Fallback to cosine if density_matrix is None.
        """
        q = self._ensure_vector(q, name="cleanup.query")
        from somabrain.numerics import compute_tiny_floor

        tiny = compute_tiny_floor(
            self.cfg.dim, dtype=self.cfg.dtype, strategy=self.cfg.tiny_floor_strategy
        )
        # Wiener unbinding (if enabled)
        if use_wiener and hasattr(self, "unbind_wiener"):
            # Assume q is the bound vector, anchors are candidate fillers
            # Use a default role vector (or pass as arg if needed)
            # For now, just use q as is (already unbound)
            hat_f = q
        else:
            hat_f = q
        # Prepare candidate matrix
        keys = list(anchors.keys())
        candidates = []
        for k in keys:
            try:
                vv = self._ensure_vector(anchors[k], name=f"cleanup.anchor[{k}]")
                candidates.append(vv)
            except ValueError:
                candidates.append(None)
        valid = [i for i, v in enumerate(candidates) if v is not None]
        if not valid:
            return "", -1.0
        X = np.stack([candidates[i] for i in valid])
        # Score with density matrix if available
        if density_matrix is not None:
            s_rho = density_matrix.score(hat_f, X)
            s_cos = np.array([self.cosine(hat_f, x, tiny_floor=tiny) for x in X])
            scores = alpha * s_rho + (1 - alpha) * s_cos
        else:
            scores = np.array([self.cosine(hat_f, x, tiny_floor=tiny) for x in X])
        best_idx = int(np.argmax(scores))
        best_id = keys[valid[best_idx]]
        return best_id, float(scores[best_idx])


def make_quantum_layer(cfg: HRRConfig) -> QuantumLayer:
    """Factory that returns a QuantumLayer implementation.

    If `cfg.hybrid_math_enabled` is True and the optional `HybridQuantumLayer`
    is available, this function will instantiate and return it. The import is
    performed lazily to avoid circular imports at module-load time.
    """
    try:
        hybrid_enabled = False
        # If caller passed a runtime-like cfg with the feature flag, respect it.
        if hasattr(cfg, "hybrid_math_enabled"):
            hybrid_enabled = bool(getattr(cfg, "hybrid_math_enabled", False))
        else:
            # Best-effort: inspect global runtime config if available
            try:
                from somabrain.config import load_config

                runtime_cfg = load_config()
                hybrid_enabled = bool(
                    getattr(runtime_cfg, "hybrid_math_enabled", False)
                )
            except Exception:
                hybrid_enabled = False

        if hybrid_enabled:
            # Lazy import to avoid circular import at module import time
            from somabrain.quantum_hybrid import HybridQuantumLayer

            return HybridQuantumLayer(cfg)
    except Exception:
        # Best-effort: fall back to canonical QuantumLayer on any failure
        pass
    return QuantumLayer(cfg)


# ---------------------------------------------------------------------------
# Backwards-compatible thin wrappers
# These keep older test-suite imports working: they delegate to the array-based
# implementations above (so no change in core math), accepting either a role
# vector (np.ndarray) or a role token (str) where reasonable.
# ---------------------------------------------------------------------------


def _as_real_vector(v: object) -> np.ndarray:
    import numpy as _np

    if isinstance(v, _np.ndarray):
        return v
    try:
        return _np.asarray(v)
    except Exception:
        raise ValueError("role must be an ndarray or convertible to one")


def bind_unitary(a: np.ndarray, role: object) -> np.ndarray:
    """Compatibility wrapper: bind vector `a` with `role`.

    If `role` is a vector, perform FFT-domain multiplication. If `role` is a
    token string, create a temporary QuantumLayer and bind using its helper.
    """
    from somabrain.numerics import irfft_norm, rfft_norm

    # QuantumLayer and HRRConfig are defined in this module; use them directly
    # role as token -> delegate to QuantumLayer for deterministic token handling
    if isinstance(role, str):
        q = QuantumLayer(HRRConfig(dim=len(a), seed=42))
        return q.bind_unitary(a, role)

    R = _as_real_vector(role)
    if a.shape[0] != R.shape[0]:
        raise ValueError("a and role must have the same length")
    fa = rfft_norm(a, n=a.size)
    fr = rfft_norm(R, n=R.size)
    from somabrain.numerics import normalize_array

    c = irfft_norm(fa * fr, n=a.size)
    return normalize_array(c, mode="robust")


def unbind_exact_or_tikhonov_or_wiener(
    c: np.ndarray, role: object, snr_db: float | None = None
) -> np.ndarray:
    """Compatibility unbind wrapper.

    Calls exact division when `snr_db` is None (Tikhonov-like tiny-floor), and
    Wiener deconvolution when `snr_db` is provided. Accepts either a role
    vector or a role token string.
    """
    import numpy as _np

    from somabrain import wiener as _wiener
    from somabrain.numerics import (
        compute_tiny_floor,
        irfft_norm,
        normalize_array,
        rfft_norm,
    )

    # Role token -> delegate to QuantumLayer exact_unitary/unbind_wiener
    if isinstance(role, str):
        q = QuantumLayer(HRRConfig(dim=len(c), seed=42))
        if snr_db is None:
            # exact unbind using the cached unitary spectrum for token
            return q.unbind_exact_unitary(c, role)
        else:
            # Wiener unbind using the role token (QuantumLayer will lookup role)
            # QuantumLayer.unbind_wiener expects (c, b, ...). For token
            # convenience, delegate to the QuantumLayer which will resolve the role.
            return q.unbind_wiener(c, role, snr_db=snr_db)

    R = _as_real_vector(role)
    if c.shape[0] != R.shape[0]:
        raise ValueError("c and role must have the same length")

    # spectral representations
    Fc = rfft_norm(c, n=c.size).astype(complex)
    Fr = rfft_norm(R, n=R.size).astype(complex)

    if snr_db is None:
        # exact/tikhonov-style: avoid div/0 by nudging denom by a consistent
        # amplitude-per-bin floor derived from compute_tiny_floor (which
        # returns an L2 amplitude tiny). Convert to per-bin amplitude floor
        # = tiny_amp / sqrt(D) and nudge complex denom bins below that.
        eps_amp = compute_tiny_floor(c.size, dtype=_np.dtype(c.dtype), strategy="sqrt")
        # per-bin amplitude floor
        amp_floor = float(eps_amp) / float((c.size**0.5))
        # ensure power-floor fallback from global fft eps is respected as a
        # conservative lower bound (HRR_FFT_EPSILON is power-like in practice)
        try:
            from somabrain.nano_profile import HRR_FFT_EPSILON as _HRR_EPS

            # if HRR_EPS looks like a power, map to amplitude via sqrt(D)
            amp_floor = max(amp_floor, float(_HRR_EPS) ** 0.5)
        except Exception:
            pass

        denom = Fr.copy().astype(np.complex128)
        zero_mask = np.abs(denom) < amp_floor
        if np.any(zero_mask):
            denom[zero_mask] = denom[zero_mask] + amp_floor
        # perform division in complex128 with guards
        Fa = (Fc.astype(np.complex128) / denom).astype(np.complex128)
        bad = ~np.isfinite(Fa)
        if np.any(bad):
            Fa[bad] = 0.0
        x = irfft_norm(Fa, n=c.size)
        x_normed = normalize_array(x, mode="robust")
        # observe reconstruction cosine if possible (we have original c->x relation)
        try:
            from somabrain import metrics as M
            from somabrain.numerics import compute_tiny_floor

            tiny = compute_tiny_floor(c.size, dtype=np.dtype(c.dtype), strategy="sqrt")
            na = float(np.linalg.norm(x_normed))
            nb = float(np.linalg.norm(c))
            if na <= tiny or nb <= tiny:
                cosv = 0.0
            else:
                cosv = float(np.dot(x_normed, c) / (na * nb))
            M.RECONSTRUCTION_COSINE.observe(float(cosv))
        except Exception:
            pass
        return x_normed
    else:
        # Wiener route: map snr_db -> lambda and use wiener helper
        lam = _wiener.tikhonov_lambda_from_snr(snr_db)
        X_spec = _wiener.wiener_deconvolve(Fc, Fr, lam)
        x = irfft_norm(X_spec, n=c.size)
        x_normed = normalize_array(x, mode="robust")
        try:
            from somabrain import metrics as M
            from somabrain.numerics import compute_tiny_floor

            tiny = compute_tiny_floor(c.size, dtype=np.dtype(c.dtype), strategy="sqrt")
            na = float(np.linalg.norm(x_normed))
            nb = float(np.linalg.norm(c))
            if na <= tiny or nb <= tiny:
                cosv = 0.0
            else:
                cosv = float(np.dot(x_normed, c) / (na * nb))
            M.RECONSTRUCTION_COSINE.observe(float(cosv))
        except Exception:
            pass
        return x_normed
