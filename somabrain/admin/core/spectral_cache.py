"""Simple file-backed spectral cache for role spectra and time-domain vectors.

API:
 - get_role(token) -> tuple(role_time: np.ndarray, role_fft: np.ndarray) | None
 - set_role(token, role_time, role_fft) -> None

Implementation notes:
 - Stores a per-token .npz file under a cache directory.
 - Filenames are safe-hashed (blake2b hex) to avoid filesystem issues.
 - Writes are atomic using a temporary file and os.replace.
 - Directory is the declared setting SOMABRAIN_SPECTRAL_CACHE_DIR
     (somabrain.settings.infra). There is no implicit path: an unset value is a
     refusal, never a silently chosen directory (Rule 91).
 - This is intentionally minimal and dependency-free to keep the runtime
     surface small and deterministic.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import numpy as np
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _cache_dir() -> Path:
    """Resolve the spectral cache directory from the declared setting.

    Resolved lazily so importing this module performs no filesystem work and
    never raises. An unset SOMABRAIN_SPECTRAL_CACHE_DIR is a refusal naming the
    setting — there is no fallback path (Rule 2 / Rule 91).
    """
    raw = settings.SOMABRAIN_SPECTRAL_CACHE_DIR
    if not raw:
        raise ImproperlyConfigured(
            "SOMABRAIN_SPECTRAL_CACHE_DIR must be set to a writable directory. "
            "It is declared in somabrain.settings.infra and has no default path."
        )
    p = Path(str(raw)).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _token_to_filename(token: str) -> str:
    # use blake2b hex to make safe filenames and keep them short
    """Execute token to filename.

    Args:
        token: The token.
    """

    h = hashlib.blake2b(token.encode("utf-8"), digest_size=16).hexdigest()
    return f"role_{h}.npz"


def get_role(token: str) -> tuple[np.ndarray, np.ndarray] | None:
    """Return (role_time, role_fft) for token if present, otherwise None.

    role_time is a real-valued time-domain vector (dtype float32/64 depending
    on what was saved). role_fft is a complex128-valued spectrum.
    """
    fn = _cache_dir() / _token_to_filename(token)
    if not fn.exists():
        return None
    try:
        with np.load(fn, allow_pickle=False) as data:
            role_time = data["role_time"]
            role_fft = data["role_fft"]
            # ensure expected dtypes
            role_fft = role_fft.astype(np.complex128, copy=False)
            return role_time, role_fft
    except Exception:
        # If reading fails for any reason, act as cache miss
        return None


def set_role(token: str, role_time: np.ndarray, role_fft: np.ndarray) -> None:
    """Persist role_time and role_fft atomically to the cache directory."""
    fn = _cache_dir() / _token_to_filename(token)
    # create a temporary filename that ends with .tmp.npz so np.savez
    # writes exactly to the path we expect (np.savez appends .npz when
    # the provided name does not already end with .npz).
    tmp = fn.with_suffix(".tmp.npz")
    # Ensure the parent directory exists (needed for tests using tmp dirs)
    fn.parent.mkdir(parents=True, exist_ok=True)

    try:
        # np.savez will write the exact filename when the path ends with
        # .npz; using tmp that ends with .tmp.npz ensures the created
        # temporary file is tmp, and we can atomically replace it into
        # the final .npz filename.
        np.savez(str(tmp), role_time=role_time, role_fft=role_fft)
        # atomic replace
        os.replace(str(tmp), str(fn))
    finally:
        # best-effort cleanup
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass
