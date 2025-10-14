import importlib

import pytest

from somabrain.quantum import HRRConfig

LEGACY_MODULES = [
    "somabrain.math.mask_composer",
    "examples.train_role",
    "examples.train_role_adam",
]


@pytest.mark.parametrize("module_name", LEGACY_MODULES)
def test_legacy_modules_removed(module_name: str) -> None:
    with pytest.raises((ImportError, RuntimeError)):
        importlib.import_module(module_name)


@pytest.mark.parametrize("method", ["mask", "fft", "legacy"])
def test_legacy_binding_methods_blocked(method: str) -> None:
    with pytest.raises(ValueError):
        HRRConfig(binding_method=method)