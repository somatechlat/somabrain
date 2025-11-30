from __future__ import annotations
import os
import sys
import importlib.util
import sysconfig
from common.logging import logger

"""Proxy module that forwards to the real PyJWT package.

This repository previously shipped a local ``jwt`` stub. To enforce
"no stubs", this module now dynamically loads the actual PyJWT installed in
site-packages and exposes its symbols. If PyJWT is not installed, import fails.
"""



_purelib = sysconfig.get_paths().get("purelib") or ""
_real_init = os.path.join(_purelib, "jwt", "__init__.py")

if not os.path.exists(_real_init):
    raise ImportError("PyJWT is not installed; install PyJWT>=2.9")

spec = importlib.util.spec_from_file_location("_pyjwt_real", _real_init)
if spec is None or spec.loader is None:  # pragma: no cover
    raise ImportError("Unable to load real PyJWT from site-packages")
_mod = importlib.util.module_from_spec(spec)
sys.modules["_pyjwt_real"] = _mod
spec.loader.exec_module(_mod)  # type: ignore[assignment]

# Re-export everything from the real PyJWT
globals().update(
    {k: v for k, v in _mod.__dict__.items() if not k.startswith("__loader__")}
)
