"""Namespace package bridge for :mod:`somabrain.metrics`.

This shim ensures that ``import somabrain.metrics`` exposes the rich metrics
module implemented in ``somabrain/metrics.py`` while still allowing access to
specialised submodules such as ``somabrain.metrics.math_metrics``.  The bridge
loads the legacy module under a private name and re-exports its public
attributes from the package namespace so existing imports keep working.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from types import ModuleType
from typing import Any

_BASE_MODULE_NAME = "somabrain._metrics_module"


def _load_base_module() -> ModuleType:
    module = sys.modules.get(_BASE_MODULE_NAME)
    if module is not None:
        return module
    metrics_path = pathlib.Path(__file__).resolve().parent.parent / "metrics.py"
    spec = importlib.util.spec_from_file_location(_BASE_MODULE_NAME, metrics_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError("Unable to load somabrain.metrics module bridge")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_BASE_MODULE_NAME] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


_base_module = _load_base_module()

# Re-export the public API from the base module.
__all__ = getattr(
    _base_module,
    "__all__",
    [name for name in dir(_base_module) if not name.startswith("_")],
)
for _name in __all__:
    globals()[_name] = getattr(_base_module, _name)


def __getattr__(name: str) -> Any:
    return getattr(_base_module, name)


def __dir__() -> list[str]:  # pragma: no cover - interactive aid
    return sorted(set(__all__) | set(globals().keys()))
