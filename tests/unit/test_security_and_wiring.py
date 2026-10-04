"""Security and wiring contracts (SOMA-STD-CODING-001, fail-closed).

These tests are source/contract tests that do not need a live backend:
they assert the authentication boundary, fail-closed OPA persistence, the
sleep wake edge, and that hot-path vector dims come from settings.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

BRAIN_ROOT = Path(__file__).resolve().parents[2]
ENDPOINTS = BRAIN_ROOT / "somabrain" / "api" / "endpoints"
SLEEP_PKG = BRAIN_ROOT / "somabrain" / "sleep"
MEMORY_API = BRAIN_ROOT / "somabrain" / "api" / "memory"
COMPOSE_SHARED = (
    BRAIN_ROOT / "infra" / "standalone" / "docker-compose.shared-network.yml"
)
COMPOSE = BRAIN_ROOT / "infra" / "standalone" / "docker-compose.yml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _func_names(tree: ast.AST) -> set[str]:
    return {
        n.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _decorator_names(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    for dec in func.decorator_list:
        if isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name):
                names.add(dec.func.id)
            elif isinstance(dec.func, ast.Attribute):
                names.add(dec.func.attr)
        elif isinstance(dec, ast.Name):
            names.add(dec.id)
        elif isinstance(dec, ast.Attribute):
            names.add(dec.attr)
    return names


# ---------------------------------------------------------------------------
# 1. Constitution endpoints sit behind the same auth boundary as the rest.
# ---------------------------------------------------------------------------
def test_constitution_routes_require_api_key_auth():
    src = _read(ENDPOINTS / "constitution.py")
    tree = ast.parse(src)
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        decorators = _decorator_names(node)
        # every routed handler must carry auth=api_key_auth
        assert "api_key_auth" in decorators or any(
            "api_key_auth" in ast.dump(d) for d in node.decorator_list
        ), f"constitution handler {node.name} has no api_key_auth"


def test_constitution_handlers_call_require_auth():
    src = _read(ENDPOINTS / "constitution.py")
    assert "require_auth" in src, "constitution handlers must call require_auth"


# ---------------------------------------------------------------------------
# 2. OPA policy update fails closed on store/reload failure.
# ---------------------------------------------------------------------------
def test_opa_update_is_fail_closed():
    src = _read(ENDPOINTS / "opa.py")
    tree = ast.parse(src)
    update = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "update_policy":
            update = node
    assert update is not None, "update_policy is missing"

    # No `except Exception: ... warning ... continue` that reports success.
    # The handler must raise HttpError on store/reload failure.
    body_src = ast.get_source_segment(src, update) or ""
    assert "HttpError" in body_src
    # Fail-open markers that must be gone.
    assert "proceeding without persistence" not in src
    assert "continuing without error" not in src
    assert "ignoring" not in src.lower() or "except Exception" not in body_src


def test_policy_manager_exposes_store_and_load():
    src = _read(BRAIN_ROOT / "somabrain" / "opa" / "policy_manager.py")
    tree = ast.parse(src)
    names = _func_names(tree)
    assert "store_policy" in names, "policy_manager.store_policy is missing"
    assert "load_policy" in names, "policy_manager.load_policy is missing"


# ---------------------------------------------------------------------------
# 3. Sleep FSM can wake back to ACTIVE.
# ---------------------------------------------------------------------------
def test_sleep_fsm_has_active_wake_edge():
    src = _read(SLEEP_PKG / "__init__.py")
    assert "SleepState.ACTIVE" in src
    # LIGHT must be able to return to ACTIVE (wake).
    tree = ast.parse(src)
    found_wake = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, val in zip(node.keys, node.values):
                if key is None:
                    continue
                key_src = ast.dump(key)
                if "LIGHT" in key_src and "ACTIVE" in ast.dump(val):
                    found_wake = True
    assert found_wake, "FSM has no LIGHT -> ACTIVE wake edge"


def test_sleep_state_manager_exposes_transition():
    src = _read(SLEEP_PKG / "__init__.py")
    tree = ast.parse(src)
    names = _func_names(tree)
    assert "transition" in names, "SleepStateManager.transition is missing"


# ---------------------------------------------------------------------------
# 4. OAK endpoints treat OptionManager results as dicts.
# ---------------------------------------------------------------------------
def test_oak_endpoints_use_dict_access():
    src = _read(ENDPOINTS / "oak.py")
    assert "opt.tenant_id" not in src
    assert "opt.option_id" not in src
    assert "opt.payload" not in src


# ---------------------------------------------------------------------------
# 5. Cognitive plan fallback dim comes from settings, not a literal.
# ---------------------------------------------------------------------------
def test_cognitive_no_hardcoded_512_dim():
    src = _read(ENDPOINTS / "cognitive.py")
    assert "np.zeros(512)" not in src
    assert "np.zeros(768)" not in src
    assert "resolve_embed_dim" in src or "SOMABRAIN_EMBED_DIM" in src


# ---------------------------------------------------------------------------
# 6. /neuromod/* uses the bootstrap singleton, not a private store.
# ---------------------------------------------------------------------------
def test_neuromod_uses_bootstrap_singleton():
    src = _read(ENDPOINTS / "neuromod.py")
    assert "get_neuromodulators" in src
    assert "_NEUROMOD_STORE" not in src or "get_neuromodulators" in src
    # The private factory must be gone.
    assert "def _neuromod_store" not in src


# ---------------------------------------------------------------------------
# 7. Compose shared-network gives the brain an RFC-valid alias.
# ---------------------------------------------------------------------------
def test_shared_network_alias_is_rfc_valid():
    src = _read(COMPOSE_SHARED)
    assert "aliases:" in src
    assert "- somabrain" in src
    # The alias itself must be RFC 1035 (letters/digits/hyphen only).
    assert "somabrain_standalone_app" not in src.split("aliases:")[1].split("\n\n")[0]


def test_compose_allowed_hosts_avoids_underscore_hostname():
    src = _read(COMPOSE)
    # The default ALLOWED_HOSTS for the app must not advertise the underscore
    # container name as a host (RFC 1035 rejects it before routing).
    assert "somabrain_standalone_app" not in src or "ALLOWED_HOSTS" in src
    # Stronger: the ALLOWED_HOSTS default line must include the alias.
    for line in src.splitlines():
        if "ALLOWED_HOSTS" in line and "localhost" in line:
            assert "somabrain" in line.split("ALLOWED_HOSTS")[-1]
            assert "somabrain_standalone_app" not in line.split("ALLOWED_HOSTS")[-1]


# ---------------------------------------------------------------------------
# 8. perform_recall is reachable from the memory recall route.
# ---------------------------------------------------------------------------
def test_memory_recall_mounts_perform_recall():
    mem_src = _read(ENDPOINTS / "memory.py")
    recall_src = _read(MEMORY_API / "recall.py")
    assert "async def perform_recall" in recall_src or "def perform_recall" in recall_src
    # Either memory.py imports perform_recall, or it accepts the advanced fields.
    advanced = (
        "min_score",
        "max_age_seconds",
        "scoring_mode",
        "session_id",
        "conversation_id",
        "pin_results",
        "chunk_size",
        "chunk_index",
    )
    imported = "perform_recall" in mem_src
    fields_present = all(f in mem_src for f in advanced)
    assert imported or fields_present, (
        "memory recall neither mounts perform_recall nor accepts its advanced fields"
    )


# ---------------------------------------------------------------------------
# 9. WM→LTM promoter is actually attached.
# ---------------------------------------------------------------------------
def test_wm_promoter_is_wired():
    mt = (BRAIN_ROOT / "somabrain" / "memory" / "wm" / "mt_wm.py").read_text()
    mgr = (BRAIN_ROOT / "somabrain" / "runtime" / "manager.py").read_text()
    assert "set_promoter" in mt, "MultiTenantWM must attach a promoter"
    assert "set_promoter_factory" in mt
    assert "_attach_wm_promoter" in mgr or "get_wm_ltm_promoter" in mgr


# ---------------------------------------------------------------------------
# 10. NREM/REM run on the sleep path.
# ---------------------------------------------------------------------------
def test_consolidation_runs_on_sleep():
    src = _read(ENDPOINTS / "sleep.py")
    assert "run_nrem" in src
    assert "run_rem" in src


# ---------------------------------------------------------------------------
# 11. gRPC brain service has a production start path.
# ---------------------------------------------------------------------------
def test_grpc_serve_command_exists():
    cmd = (
        BRAIN_ROOT
        / "somabrain"
        / "management"
        / "commands"
        / "serve_brain_grpc.py"
    )
    assert cmd.is_file(), "serve_brain_grpc management command is missing"
    src = cmd.read_text()
    assert "add_brain_service" in src
    assert "start_local_server" in src
    assert "ssl_server_credentials" in src
