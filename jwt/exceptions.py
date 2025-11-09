"""Proxy for jwt.exceptions from the real PyJWT package."""

from __future__ import annotations

import os
import sys
import importlib.util
import sysconfig

_purelib = sysconfig.get_paths().get("purelib") or ""
_real_ex = os.path.join(_purelib, "jwt", "exceptions.py")

if not os.path.exists(_real_ex):
    raise ImportError("PyJWT is not installed; install PyJWT>=2.9")

spec = importlib.util.spec_from_file_location("_pyjwt_exceptions_real", _real_ex)
if spec is None or spec.loader is None:  # pragma: no cover
    raise ImportError("Unable to load PyJWT exceptions from site-packages")
_mod = importlib.util.module_from_spec(spec)
sys.modules["_pyjwt_exceptions_real"] = _mod
spec.loader.exec_module(_mod)  # type: ignore[assignment]

# Re-export everything from the real exceptions module
globals().update(
    {k: v for k, v in _mod.__dict__.items() if not k.startswith("__loader__")}
)
