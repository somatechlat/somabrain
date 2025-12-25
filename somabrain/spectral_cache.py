"""Simple file-backed spectral cache for role spectra and time-domain vectors.

API:
 - get_role(token) -> tuple(role_time: np.ndarray, role_fft: np.ndarray) | None
 - set_role(token, role_time, role_fft) -> None

Implementation notes:
 - Stores a per-token .npz file under a cache directory.
 - Filenames are safe-hashed (blake2b hex) to avoid filesystem issues.
 - Writes are atomic using a temporary file and os.replace.
 - Directory is configurable via env SOMABRAIN_SPECTRAL_CACHE_DIR.
 - This is intentionally minimal and dependency-free to keep the runtime
     surface small and deterministic.
"""

from __future__ import annotations

import hashlib
import os
from django.conf import settings
from pathlib import Path
from typing import Optional, Tuple

import numpy as np


def _default_cache_dir() -> Path:
    env = settings.SOMABRAIN_SPECTRAL_CACHE_DIR
    if env:
        p = Path(env).expanduser()
    else:
        # use repository-local .cache/spectral by default
        repo_root = Path(__file__).resolve().parents[1]
        p = repo_root / ".cache" / "spectral"
    p.mkdir(parents=True, exist_ok=True)
    return p


_CACHE_DIR = _default_cache_dir()


def _token_to_filename(token: str) -> str:
    # use blake2b hex to make safe filenames and keep them short
    h = hashlib.blake2b(token.encode("utf-8"), digest_size=16).hexdigest()
    return f"role_{h}.npz"


def get_role(token: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """Return (role_time, role_fft) for token if present, otherwise None.

    role_time is a real-valued time-domain vector (dtype float32/64 depending
    on what was saved). role_fft is a complex128-valued spectrum.
    """
    fn = _CACHE_DIR / _token_to_filename(token)
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
    fn = _CACHE_DIR / _token_to_filename(token)
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
