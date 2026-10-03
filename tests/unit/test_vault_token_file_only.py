"""Vault token is a FILE, never an environment variable (VIBE Rule 164).

``os.environ`` is visible in ``ps``, in ``/proc/*/environ`` and in every crash
dump. A token exported to the shell is a token in the process table. The vault
client must therefore take its token only from the file named by
``VAULT_TOKEN_FILE`` (a path — topology), and refuse to run when that file is
missing or empty. There is deliberately no ``VAULT_TOKEN`` /
``SOMABRAIN_VAULT_TOKEN`` environment fallback anywhere in the client.

Reference contract: somaAgent01/services/common/vault_secrets.py — token from
``VAULT_TOKEN_FILE`` only; empty/missing raises.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

BRAIN_ROOT = Path(__file__).resolve().parents[2]
VAULT_CLIENT = BRAIN_ROOT / "somabrain" / "core" / "security" / "vault_client.py"

# The token value itself must never appear as an environment lookup. The token
# *path* (VAULT_TOKEN_FILE) is topology and is allowed.
_FORBIDDEN_ENV_NAMES = frozenset({"VAULT_TOKEN", "SOMABRAIN_VAULT_TOKEN"})


def _env_lookups(tree: ast.AST) -> list[tuple[str, int, str]]:
    """Return (name, lineno, api) for every os.environ/os.getenv lookup."""
    found: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # os.environ.get("NAME") / os.environ["NAME"] via .get
            if isinstance(func, ast.Attribute) and func.attr == "get":
                value = func.value
                if isinstance(value, ast.Attribute) and value.attr == "environ":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        found.append((str(node.args[0].value), node.lineno, "environ.get"))
            # os.getenv("NAME")
            if isinstance(func, ast.Attribute) and func.attr == "getenv":
                value = func.value
                if isinstance(value, ast.Name) and value.id == "os":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        found.append((str(node.args[0].value), node.lineno, "os.getenv"))
        if isinstance(node, ast.Subscript):
            value = node.value
            if isinstance(value, ast.Attribute) and value.attr == "environ":
                key = node.slice
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    found.append((str(key.value), node.lineno, "environ[]"))
    return found


def test_vault_client_never_reads_token_from_environ():
    """Static: no environ/os.getenv lookup of VAULT_TOKEN / SOMABRAIN_VAULT_TOKEN."""
    source = VAULT_CLIENT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    offenders = [
        f"{api}:{lineno} -> {name}"
        for name, lineno, api in _env_lookups(tree)
        if name in _FORBIDDEN_ENV_NAMES
    ]
    assert offenders == [], f"vault client still reads a token from the environment: {offenders}"


def test_vault_client_error_message_does_not_advertise_env_token():
    """Static: the failure message must not tell operators to export a token."""
    source = VAULT_CLIENT.read_text(encoding="utf-8")
    assert "VAULT_TOKEN environment" not in source
    assert "SOMABRAIN_VAULT_TOKEN" not in source


def _load_token_reader():
    """Import the token-file reader without booting Django settings."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "somabrain_vault_client_under_test", VAULT_CLIENT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def vault_mod():
    return _load_token_reader()


def test_token_file_present_yields_token(vault_mod, tmp_path, monkeypatch):
    """VAULT_TOKEN_FILE present -> the token is read from that file."""
    token_file = tmp_path / "vault_token"
    token_file.write_text("hvs.test-only-token-from-file\n", encoding="utf-8")
    monkeypatch.setenv("VAULT_TOKEN_FILE", str(token_file))
    # A token in the environment must not shadow or replace the file.
    monkeypatch.setenv("VAULT_TOKEN", "env-token-must-not-be-used")
    monkeypatch.setenv("SOMABRAIN_VAULT_TOKEN", "env-token-must-not-be-used")

    token = vault_mod._read_vault_token()
    assert token == "hvs.test-only-token-from-file"


def test_token_file_absent_raises(vault_mod, monkeypatch):
    """No VAULT_TOKEN_FILE -> refusal. Never falls back to env."""
    monkeypatch.delenv("VAULT_TOKEN_FILE", raising=False)
    monkeypatch.setenv("VAULT_TOKEN", "env-token-must-not-be-used")
    monkeypatch.setenv("SOMABRAIN_VAULT_TOKEN", "env-token-must-not-be-used")

    with pytest.raises(vault_mod.VaultNotConfigured) as excinfo:
        vault_mod._read_vault_token()
    assert "VAULT_TOKEN_FILE" in str(excinfo.value)


def test_empty_token_file_raises(vault_mod, tmp_path, monkeypatch):
    """An empty token file is not 'no secrets' — it is a broken credential."""
    token_file = tmp_path / "vault_token"
    token_file.write_text("   \n", encoding="utf-8")
    monkeypatch.setenv("VAULT_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("VAULT_TOKEN", "env-token-must-not-be-used")

    with pytest.raises(vault_mod.VaultNotConfigured):
        vault_mod._read_vault_token()


def test_missing_token_file_path_raises(vault_mod, tmp_path, monkeypatch):
    """A named token file that does not exist is a refusal, not None."""
    monkeypatch.setenv("VAULT_TOKEN_FILE", str(tmp_path / "does-not-exist"))
    monkeypatch.setenv("VAULT_TOKEN", "env-token-must-not-be-used")

    with pytest.raises(vault_mod.VaultNotConfigured):
        vault_mod._read_vault_token()


def test_get_secret_refuses_without_token_file(vault_mod, monkeypatch):
    """Behavioural: the public API fails closed when no token file is named."""
    monkeypatch.delenv("VAULT_TOKEN_FILE", raising=False)
    monkeypatch.setenv("VAULT_TOKEN", "env-token-must-not-be-used")
    monkeypatch.setenv("SOMABRAIN_VAULT_TOKEN", "env-token-must-not-be-used")
    if hasattr(vault_mod._get_vault_client, "cache_clear"):
        vault_mod._get_vault_client.cache_clear()

    with pytest.raises(vault_mod.VaultNotConfigured):
        vault_mod.get_secret("somabrain/auth", "jwt_secret")
