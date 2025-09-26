"""Shim package to expose repository-level scripts under `somabrain.scripts`.

This module attempts multiple strategies to make commonly-used script
modules available to test code that imports ``from somabrain.scripts import
replay_journal`` etc.

Strategies (in order):
1. Import the top-level package ``scripts`` (if the repository has a package
   layout that makes it importable).
2. Locate the repository `scripts/` directory relative to this file and
   load individual script modules (``replay_journal.py``, ``audit_probe.py``)
   using importlib if the top-level import fails.

This keeps tests resilient whether ``scripts/`` is installed as a package or
present as a plain script directory in the repository root.
"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Optional


def _load_module_from_file(name: str, path: Path) -> Optional[ModuleType]:
    try:
        spec = importlib.util.spec_from_file_location(name, str(path))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        return None
    return None


_repo_scripts = None
try:
    # Prefer importing if top-level package is available on sys.path
    _repo_scripts = importlib.import_module("scripts")
except Exception:
    _repo_scripts = None


def _try_load(name: str) -> Optional[ModuleType]:
    # 1) Try attribute from imported top-level package
    if _repo_scripts is not None and hasattr(_repo_scripts, name):
        return getattr(_repo_scripts, name)

    # 2) Try to load from scripts/ directory in the repository root
    this_file = Path(__file__).resolve()
    # repo root is two parents up: repo/.../somabrain/somabrain/scripts/__init__.py
    repo_root = this_file.parents[2]
    candidate = repo_root / "scripts" / f"{name}.py"
    if candidate.exists():
        mod = _load_module_from_file(f"somabrain.scripts.{name}", candidate)
        return mod

    return None


replay_journal = _try_load("replay_journal")

# Don't import audit_probe here: it is a CLI-style script that may perform
# sys.exit() or other side-effects when executed at import time. Only expose
# replay_journal which is safe for tests to import and call.
__all__ = ["replay_journal"]
