"""LAW sweep: no env secrets, one token name, no call-site magics.

TDD pin for the operator directive:
  1. runtime_config must not fall back to os.getenv (BrainSetting/Django only).
  2. SOMA_API_TOKEN / SOMABRAIN_API_TOKEN / OUTBOX_API_TOKEN collapse to ONE
     canonical Vault-resolved name.
  3. Transport timeout/backoff, integrator OPA paths, and learner tau defaults
     live in settings/contracts — never as call-site literals.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

BRAIN_ROOT = Path(__file__).resolve().parents[2]
SOMA = BRAIN_ROOT / "somabrain"
SETTINGS = SOMA / "settings"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _names_assigned_in(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            out.add(node.target.id)
    return out


class TestRuntimeConfigNoEnv:
    def test_runtime_config_has_no_getenv_or_environ(self) -> None:
        src = _read(SOMA / "runtime_config.py")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in {
                "getenv",
                "environ",
                "putenv",
            }:
                pytest.fail(
                    f"runtime_config.py:{node.lineno} touches os.{node.attr} — "
                    "ENV is never a secret source (Rule 164)"
                )
        assert "os.getenv" not in src
        assert "os.environ" not in src


class TestSingleApiTokenName:
    """One canonical Vault-resolved API token name: SOMA_API_TOKEN."""

    CANONICAL = "SOMA_API_TOKEN"
    BANNED_ALIASES = ("SOMABRAIN_API_TOKEN", "OUTBOX_API_TOKEN")

    def test_settings_modules_do_not_assign_aliases(self) -> None:
        offenders: list[str] = []
        for path in sorted(SETTINGS.glob("*.py")):
            tree = ast.parse(_read(path))
            assigned = _names_assigned_in(tree)
            for alias in self.BANNED_ALIASES:
                if alias in assigned:
                    offenders.append(f"{path.name} assigns {alias}")
        assert offenders == [], f"dual token aliases still assigned: {offenders}"

    def test_django_core_boot_secret_uses_only_canonical(self) -> None:
        src = _read(SETTINGS / "django_core.py")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "_boot_secret":
                    if not node.args:
                        continue
                    first = node.args[0]
                    if (
                        isinstance(first, ast.Constant)
                        and first.value in self.BANNED_ALIASES
                    ):
                        pytest.fail(
                            f"django_core.py:{node.lineno} boot-secrets alias {first.value}"
                        )

    def test_infra_remember_uses_only_canonical(self) -> None:
        src = _read(SETTINGS / "infra.py")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "_remember":
                    if not node.args:
                        continue
                    first = node.args[0]
                    if (
                        isinstance(first, ast.Constant)
                        and first.value in self.BANNED_ALIASES
                    ):
                        pytest.fail(
                            f"infra.py:{node.lineno} remembers alias {first.value}"
                        )

    def test_production_code_reads_only_canonical_api_token(self) -> None:
        offenders: list[str] = []
        for path in SOMA.rglob("*.py"):
            if "settings" in path.parts and path.name in {
                "infra.py",
                "django_core.py",
            }:
                # settings own the declaration; covered above.
                continue
            src = _read(path)
            if "SOMABRAIN_MEMORY_HTTP_TOKEN" in src:
                # different credential, not an alias of api_token
                pass
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if node.value in self.BANNED_ALIASES:
                        offenders.append(
                            f"{path.relative_to(BRAIN_ROOT)}:{node.lineno}"
                        )
        assert (
            offenders == []
        ), f"alias token names referenced from production code: {offenders}"


class TestNoCallSiteMagics:
    """Transport / OPA / learner policy numbers live in settings or contracts."""

    def test_memory_transport_timeout_not_hardcoded(self) -> None:
        src = _read(SOMA / "memory" / "transport.py")
        assert '"timeout": 10.0' not in src
        assert "'timeout': 10.0" not in src
        assert "max_retries: int = 2" not in src

    def test_integrator_opa_path_not_hardcoded(self) -> None:
        src = _read(SOMA / "services" / "integrator_hub_triplet.py")
        assert "soma/policy/integrator" not in src
        assert "timeout=1)" not in src and "timeout=1," not in src

    def test_learner_tau_default_from_contract(self) -> None:
        src = _read(SOMA / "services" / "learner_online.py")
        assert 'event.get("tau", 1.0)' not in src
        assert 'event.get("lr", 0.0)' not in src

    def test_learner_online_has_no_yaml_import(self) -> None:
        tree = ast.parse(_read(SOMA / "services" / "learner_online.py"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "yaml", "unused yaml import remains"
            if isinstance(node, ast.ImportFrom) and node.module == "yaml":
                pytest.fail("yaml import remains in learner_online.py")


class TestContractsHoldTransportLearnerPolicy:
    def test_transport_and_learner_constants_exported(self) -> None:
        import somabrain.math.contracts as C

        required = (
            "HTTP_TIMEOUT_S",
            "HTTP_MAX_RETRIES",
            "HTTP_BACKOFF_BASE_S",
            "HTTP_BACKOFF_JITTER_S",
            "HTTP_BACKOFF_ERROR_BASE_S",
            "HTTP_BACKOFF_ERROR_JITTER_S",
            "OPA_POLICY_PATH_ALLOW",
            "OPA_POLICY_PATH_ALLOW_DEV",
            "OPA_POLICY_PATH_INTEGRATOR",
            "LEARNER_DEFAULT_TAU",
            "LEARNER_DEFAULT_LR",
        )
        missing = [n for n in required if not hasattr(C, n)]
        assert missing == [], f"contracts missing policy constants: {missing}"

    def test_values_match_previous_literals(self) -> None:
        import somabrain.math.contracts as C

        assert C.HTTP_TIMEOUT_S == 10.0
        assert C.HTTP_MAX_RETRIES == 2
        assert C.OPA_POLICY_PATH_ALLOW == "somabrain/auth/allow"
        assert C.OPA_POLICY_PATH_ALLOW_DEV == "somabrain/auth/allow_dev"
        assert C.OPA_POLICY_PATH_INTEGRATOR == "soma/policy/integrator"
        assert C.LEARNER_DEFAULT_TAU == 1.0
        assert C.LEARNER_DEFAULT_LR == 0.0
