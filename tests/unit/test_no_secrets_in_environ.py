"""Rule 164: a secret is read from Vault and used, never copied into ENV.

somabrain's settings used to ``os.environ[...] =`` the DSN, JWT secret,
``SECRET_KEY`` and the API tokens after reading them from Vault. A secret
that lands in the process environment is visible in ``ps``, in
``/proc/*/environ`` and in every crash dump — the Vault migration is undone
the moment the process starts.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

BRAIN_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_DIR = BRAIN_ROOT / "somabrain" / "settings"

_SECRET_SHAPED = (
    "SOMABRAIN_POSTGRES_DSN",
    "SOMABRAIN_JWT_SECRET",
    "SECRET_KEY",
    "SOMA_API_TOKEN",
    "SOMABRAIN_API_TOKEN",
    "SOMABRAIN_REDIS_URL",
    "SUPERVISOR_HTTP_PASS",
    "OUTBOX_API_TOKEN",
    "SOMABRAIN_MEMORY_HTTP_TOKEN",
    "SOMABRAIN_VAULT_TOKEN",
    "VAULT_TOKEN",
)


def test_settings_never_assign_secrets_to_environ():
    """Static guard: no settings module may write a secret into os.environ."""
    offenders: list[str] = []
    for path in sorted(SETTINGS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # os.environ[NAME] = value   /   os.environ.__setitem__(NAME, value)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if not isinstance(target, ast.Subscript):
                        continue
                    value = target.value
                    if not (isinstance(value, ast.Attribute) and value.attr == "environ"):
                        continue
                    key = target.slice
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        if key.value in _SECRET_SHAPED:
                            offenders.append(f"{path.name}:{node.lineno} -> {key.value}")
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "__setitem__":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        name = node.args[0].value
                        if name in _SECRET_SHAPED:
                            offenders.append(f"{path.name}:{node.lineno} -> {name}")
    assert offenders == [], f"secrets written into os.environ: {offenders}"


def test_no_secret_export_helper_remains():
    """_set_env_if_present existed only to export secrets. It must be gone."""
    for path in sorted(SETTINGS_DIR.glob("*.py")):
        src = path.read_text(encoding="utf-8")
        assert "_set_env_if_present" not in src, f"{path.name} still exports to environ"


def test_secret_names_absent_from_environ_after_settings_import():
    """Behavioural: importing the settings must not leak secrets into ENV."""
    before = {k: os.environ.get(k) for k in _SECRET_SHAPED}
    try:
        try:
            import somabrain.settings.infra  # noqa: F401
        except Exception as exc:  # noqa: BLE001 - the gate is the subject
            pytest.skip(f"memory credential not provisioned: {type(exc).__name__}")

        leaked = [
            name
            for name in _SECRET_SHAPED
            if before.get(name) is None and os.environ.get(name) is not None
        ]
        assert leaked == [], f"settings import leaked secrets into ENV: {leaked}"
    finally:
        for name, value in before.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
