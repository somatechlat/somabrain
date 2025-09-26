"""Wiener / regularized deconvolution helpers for HRR unbinding.

Provides robust spectral deconvolution helpers used by unbind algorithms
to avoid amplification of small spectral components.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from . import numerics as _num


def tikhonov_lambda_from_snr(
    snr_db: Optional[float], signal_power: float = 1.0
) -> float:
    """Convert an SNR in dB to a Tikhonov regularization lambda.

    Basic heuristic: lambda = signal_power / (10**(snr_db/10)) if snr_db provided,
    otherwise fallback to a small epsilon based on machine eps.
    """
    if snr_db is None:
        return _num.compute_tiny_floor(1, dtype=np.float64, strategy="absolute")
    snr_lin = 10.0 ** (snr_db / 10.0)
    return float(
        max(_num.compute_tiny_floor(1, dtype=np.float64), signal_power / snr_lin)
    )


def wiener_deconvolve(C_spec: np.ndarray, H_spec: np.ndarray, lam: float) -> np.ndarray:
    """Perform Wiener/Tikhonov deconvolution in the unitary-frequency domain.

    C_spec and H_spec are rfft spectra (complex). Returns estimated X_spec such
    that x_time = irfft_norm(X_spec).
    """
    # Ensure float64 computation for stability
    C = np.asarray(C_spec, dtype=np.complex128)
    H = np.asarray(H_spec, dtype=np.complex128)
    H_conj = np.conjugate(H)
    denom = (np.abs(H) ** 2) + float(lam)
    # Avoid tiny denom
    tiny = _num.compute_tiny_floor(denom.shape[-1], dtype=np.float64)
    denom = np.where(denom < tiny, tiny, denom)
    X = (H_conj * C) / denom
    return X
