"""Proxy module that forwards to the real PyJWT package.

VIBE Compliance:
    This repository previously shipped a local ``jwt`` stub. To enforce
    "no stubs" per VIBE Coding Rules, this module now dynamically loads
    the actual PyJWT installed in site-packages and exposes its symbols.

Dynamic Loading Rationale:
    Python's import system would normally find this local ``jwt`` package
    before the real PyJWT in site-packages. To work around this, we:
    1. Locate PyJWT's __init__.py in site-packages using sysconfig
    2. Load it as a separate module using importlib
    3. Re-export all its symbols to make this module behave like PyJWT

    If PyJWT is not installed, import fails immediately with a clear error.
"""

from __future__ import annotations
import os
import sys
import importlib.util
import sysconfig
from common.logging import logger  # noqa: F401


_purelib = sysconfig.get_paths().get("purelib") or ""
_real_init = os.path.join(_purelib, "jwt", "__init__.py")

if not os.path.exists(_real_init):
    raise ImportError("PyJWT is not installed; install PyJWT>=2.9")

spec = importlib.util.spec_from_file_location("_pyjwt_real", _real_init)
if spec is None or spec.loader is None:  # pragma: no cover
    raise ImportError("Unable to load real PyJWT from site-packages")
_mod = importlib.util.module_from_spec(spec)
sys.modules["_pyjwt_real"] = _mod
spec.loader.exec_module(_mod)

# Re-export everything from the real PyJWT
globals().update({k: v for k, v in _mod.__dict__.items() if not k.startswith("__loader__")})
