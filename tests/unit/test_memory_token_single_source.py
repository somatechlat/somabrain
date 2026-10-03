"""One definition of the memory HTTP token (VIBE Rule 164 / Rule 91).

``settings/infra.py`` already resolves ``SOMABRAIN_MEMORY_HTTP_TOKEN`` from
Vault (or, as topology fallback for CI, from the environment). ``cognitive.py``
must import and reuse that single value. Two definitions drift: one can be
empty while the other is set, and the empty one silently becomes "no token".

A missing token is a refusal, never ``""``. An empty string dressed up as a
default is a shim that lets a service authenticate as nobody.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

BRAIN_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_DIR = BRAIN_ROOT / "somabrain" / "settings"
COGNITIVE = SETTINGS_DIR / "cognitive.py"
INFRA = SETTINGS_DIR / "infra.py"

TOKEN_NAME = "SOMABRAIN_MEMORY_HTTP_TOKEN"


def _assignments_of(tree: ast.AST, name: str) -> list[int]:
    """Line numbers of ``name = ...`` assignments (not imports)."""
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    lines.append(node.lineno)
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                lines.append(node.lineno)
    return lines


def _env_reads_of_token(tree: ast.AST) -> list[str]:
    """Find env.str/env()/environ lookups of the memory token name."""
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            args = node.args
            if not args:
                continue
            first = args[0]
            if not (isinstance(first, ast.Constant) and first.value == TOKEN_NAME):
                continue
            func = node.func
            if isinstance(func, ast.Attribute):
                hits.append(f"{func.attr}:{node.lineno}")
            elif isinstance(func, ast.Name):
                hits.append(f"{func.id}:{node.lineno}")
    return hits


def test_cognitive_does_not_redeclare_memory_token():
    """Static: cognitive.py must not assign SOMABRAIN_MEMORY_HTTP_TOKEN itself.

    The value is imported from infra.py. A local ``env.str(..., default="")``
    is a second definition and therefore a drift risk.
    """
    tree = ast.parse(COGNITIVE.read_text(encoding="utf-8"))
    assigns = _assignments_of(tree, TOKEN_NAME)
    assert assigns == [], f"cognitive.py re-declares {TOKEN_NAME} at lines {assigns}"

    env_reads = _env_reads_of_token(tree)
    assert env_reads == [], f"cognitive.py reads {TOKEN_NAME} from env: {env_reads}"


def test_infra_still_owns_the_single_definition():
    """Static: infra.py keeps exactly one assignment of the memory token."""
    tree = ast.parse(INFRA.read_text(encoding="utf-8"))
    assigns = _assignments_of(tree, TOKEN_NAME)
    assert len(assigns) == 1, (
        f"infra.py must define {TOKEN_NAME} exactly once, found at {assigns}"
    )


def test_cognitive_rejects_empty_memory_token():
    """Static: empty token must raise, never be published as ``""``.

    Checked structurally so this gate holds even when Vault is unprovisioned
    and the behavioural import path cannot run.
    """
    source = COGNITIVE.read_text(encoding="utf-8")
    assert TOKEN_NAME in source, "cognitive.py must reference the imported token"

    # No empty-string default anywhere the token name is mentioned.
    for line in source.splitlines():
        if TOKEN_NAME in line:
            assert 'default=""' not in line, (
                f"cognitive.py must not default {TOKEN_NAME} to empty: {line.strip()}"
            )

    tree = ast.parse(source)
    raises_on_empty = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        names = {n.id for n in ast.walk(test) if isinstance(n, ast.Name)}
        if TOKEN_NAME not in names:
            continue
        has_raise = any(isinstance(n, ast.Raise) for n in ast.walk(node))
        if has_raise and isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            raises_on_empty = True
    assert raises_on_empty, (
        f"cognitive.py must refuse an empty {TOKEN_NAME} "
        "(raise when the resolved value is falsy)"
    )


def _purge_somabrain_settings() -> None:
    for name in list(sys.modules):
        if name.startswith("somabrain.settings"):
            del sys.modules[name]


def _load_cognitive_modules():
    """Load infra + cognitive by path, bypassing ``settings/__init__``.

    ``somabrain.settings.__init__`` pulls in django_core (SECRET_KEY, DB).
    These tests exercise only the cognitive/infra seam and must not depend on
    a full Django boot.
    """
    _purge_somabrain_settings()
    if "somabrain" not in sys.modules:
        parent = types.ModuleType("somabrain")
        parent.__path__ = [str(BRAIN_ROOT / "somabrain")]
        sys.modules["somabrain"] = parent

    pkg_name = "somabrain.settings"
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [str(SETTINGS_DIR)]
    pkg.__package__ = pkg_name
    sys.modules[pkg_name] = pkg

    infra_name = f"{pkg_name}.infra"
    infra_spec = importlib.util.spec_from_file_location(infra_name, INFRA)
    assert infra_spec is not None and infra_spec.loader is not None
    infra_mod = importlib.util.module_from_spec(infra_spec)
    infra_mod.__package__ = pkg_name
    sys.modules[infra_name] = infra_mod
    infra_spec.loader.exec_module(infra_mod)

    cog_name = f"{pkg_name}.cognitive"
    cog_spec = importlib.util.spec_from_file_location(cog_name, COGNITIVE)
    assert cog_spec is not None and cog_spec.loader is not None
    cog_mod = importlib.util.module_from_spec(cog_spec)
    cog_mod.__package__ = pkg_name
    sys.modules[cog_name] = cog_mod
    cog_spec.loader.exec_module(cog_mod)
    return infra_mod, cog_mod


def test_cognitive_token_is_the_infra_token():
    """Behavioural: cognitive exports exactly the value infra resolved."""
    token = os.environ.get(TOKEN_NAME)
    if not token:
        pytest.skip(
            f"{TOKEN_NAME} not provisioned; cannot import settings to compare"
        )
    saved_req = os.environ.get("REQUIRE_MEMORY")
    os.environ["REQUIRE_MEMORY"] = "1"
    try:
        infra_mod, cog_mod = _load_cognitive_modules()
        assert cog_mod.SOMABRAIN_MEMORY_HTTP_TOKEN == infra_mod.SOMABRAIN_MEMORY_HTTP_TOKEN
        assert cog_mod.SOMABRAIN_MEMORY_HTTP_TOKEN != ""
    finally:
        _purge_somabrain_settings()
        if saved_req is None:
            os.environ.pop("REQUIRE_MEMORY", None)
        else:
            os.environ["REQUIRE_MEMORY"] = saved_req


def test_cognitive_refuses_when_token_absent():
    """Behavioural: with no token anywhere, importing cognitive is a refusal."""
    saved = {
        k: os.environ.pop(k)
        for k in list(os.environ)
        if TOKEN_NAME in k or k == "REQUIRE_MEMORY"
    }
    # Keep the infra gate from firing first so we observe cognitive's own refusal.
    os.environ["REQUIRE_MEMORY"] = "0"
    try:
        with pytest.raises(Exception) as excinfo:
            _load_cognitive_modules()
        message = str(excinfo.value)
        assert TOKEN_NAME in message, (
            f"refusal must name the missing credential, got: {message}"
        )
    finally:
        _purge_somabrain_settings()
        os.environ.update(saved)
