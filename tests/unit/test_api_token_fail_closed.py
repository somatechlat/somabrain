"""get_api_token() must raise on failure, never look like "no token" (Rule 91).

``django_core.get_api_token`` used to swallow every file-read error
(``except Exception: pass``) and return ``None``. A caller that sees ``None``
cannot tell "nothing is configured" from "the credential file is missing,
unreadable or empty". Those are different states: the first is a deployment
choice, the second is a broken credential and must raise.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

BRAIN_ROOT = Path(__file__).resolve().parents[2]
DJANGO_CORE = BRAIN_ROOT / "somabrain" / "settings" / "django_core.py"


def _get_api_token_node() -> ast.FunctionDef:
    tree = ast.parse(DJANGO_CORE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "get_api_token":
            return node
    raise AssertionError("django_core.get_api_token is missing")


def _install_get_api_token(namespace: dict) -> None:
    """Exec the real get_api_token body into ``namespace`` (no Django boot)."""
    node = _get_api_token_node()
    module = ast.Module(body=[node], type_ignores=[])
    code = compile(module, filename=str(DJANGO_CORE), mode="exec")
    namespace.setdefault("Path", Path)
    namespace.setdefault("SOMA_API_TOKEN", None)
    namespace.setdefault("SOMA_API_TOKEN_FILE", None)
    import environ as _environ

    namespace.setdefault("environ", _environ)
    exec(code, namespace)  # noqa: S102 - exercising the shipped function body
    assert "get_api_token" in namespace


def test_get_api_token_source_never_swallows_errors():
    """Static: no bare except/pass inside get_api_token."""
    node = _get_api_token_node()
    for child in ast.walk(node):
        if isinstance(child, ast.ExceptHandler):
            # `except Exception: pass` or `except: pass` is the defect.
            body = child.body
            swallowed = all(
                isinstance(stmt, ast.Pass) or (
                    isinstance(stmt, ast.Expr)
                    and isinstance(stmt.value, ast.Constant)
                )
                for stmt in body
            )
            assert not swallowed, (
                f"get_api_token swallows a read failure at line {child.lineno}"
            )
    # Stronger: the function must contain at least one Raise.
    raises = [n for n in ast.walk(node) if isinstance(n, ast.Raise)]
    assert raises, "get_api_token must raise on a failed credential load"


def test_missing_token_file_raises():
    """A named token file that does not exist is a refusal, not None."""
    ns: dict = {"SOMA_API_TOKEN": None, "SOMA_API_TOKEN_FILE": "/no/such/token-file"}
    _install_get_api_token(ns)
    with pytest.raises(Exception) as excinfo:
        ns["get_api_token"]()
    assert not isinstance(excinfo.value, AssertionError)
    message = str(excinfo.value).lower()
    assert "token" in message or "soma_api_token_file" in message


def test_unreadable_token_file_raises(tmp_path):
    """An OSError on read must raise, not return None."""
    target = tmp_path / "api_token"
    # A directory is unreadable as a text file.
    target.mkdir()
    ns: dict = {"SOMA_API_TOKEN": None, "SOMA_API_TOKEN_FILE": str(target)}
    _install_get_api_token(ns)
    with pytest.raises(Exception):
        ns["get_api_token"]()


def test_empty_token_file_raises(tmp_path):
    """An empty credential file is broken, not 'no token configured'."""
    token_file = tmp_path / "api_token"
    token_file.write_text("   \n", encoding="utf-8")
    ns: dict = {"SOMA_API_TOKEN": None, "SOMA_API_TOKEN_FILE": str(token_file)}
    _install_get_api_token(ns)
    with pytest.raises(Exception):
        ns["get_api_token"]()


def test_token_file_is_read_when_present(tmp_path):
    """A provisioned file yields the credential."""
    token_file = tmp_path / "api_token"
    token_file.write_text("test-only-api-token\n", encoding="utf-8")
    ns: dict = {"SOMA_API_TOKEN": None, "SOMA_API_TOKEN_FILE": str(token_file)}
    _install_get_api_token(ns)
    assert ns["get_api_token"]() == "test-only-api-token"


def test_inline_token_wins_over_file(tmp_path):
    """A token already held in module state is returned as-is."""
    token_file = tmp_path / "api_token"
    token_file.write_text("from-file", encoding="utf-8")
    ns: dict = {"SOMA_API_TOKEN": "from-module-state", "SOMA_API_TOKEN_FILE": str(token_file)}
    _install_get_api_token(ns)
    assert ns["get_api_token"]() == "from-module-state"


def test_nothing_configured_returns_none():
    """With neither token nor file named, there is legitimately no token.

    This is the only path allowed to return None — it is "not configured",
    not "configured but failed".
    """
    ns: dict = {"SOMA_API_TOKEN": None, "SOMA_API_TOKEN_FILE": None}
    _install_get_api_token(ns)
    assert ns["get_api_token"]() is None
