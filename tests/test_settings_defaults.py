"""Module test_settings_defaults."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from somabrain.microcircuits import MCConfig
from somabrain.mt_wm import MTWMConfig
from somabrain.planner_rwr import rwr_plan
from somabrain.prediction import BudgetedPredictor, SlowPredictor
from somabrain.wm import WorkingMemory

"""Invariant tests ensuring config defaults are centralized in settings."""


def test_mcconfig_defaults_follow_settings() -> None:
    """Execute test mcconfig defaults follow settings."""

    cfg = MCConfig()
    assert cfg.columns == max(1, int(settings.SOMABRAIN_MICRO_CIRCUITS))
    assert cfg.vote_temperature == settings.SOMABRAIN_MICRO_VOTE_TEMPERATURE
    assert cfg.max_tenants == settings.SOMABRAIN_MICRO_MAX_TENANTS
    assert cfg.recency_time_scale == settings.SOMABRAIN_WM_RECENCY_TIME_SCALE
    assert cfg.recency_max_steps == settings.SOMABRAIN_WM_RECENCY_MAX_STEPS


def test_mtwm_defaults_follow_settings() -> None:
    """Execute test mtwm defaults follow settings."""

    cfg = MTWMConfig()
    assert cfg.max_tenants == settings.SOMABRAIN_MTWM_MAX_TENANTS
    assert cfg.per_tenant_capacity == max(
        1, int(settings.SOMABRAIN_WM_PER_TENANT_CAPACITY)
    )
    assert cfg.recency_time_scale == settings.SOMABRAIN_WM_RECENCY_TIME_SCALE
    assert cfg.recency_max_steps == settings.SOMABRAIN_WM_RECENCY_MAX_STEPS


def test_working_memory_defaults_use_settings() -> None:
    """Execute test working memory defaults use settings."""

    wm = WorkingMemory(capacity=4, dim=2)
    assert wm.alpha == settings.SOMABRAIN_WM_ALPHA
    assert wm.beta == settings.SOMABRAIN_WM_BETA
    assert wm.gamma == settings.SOMABRAIN_WM_GAMMA
    assert wm._recency_scale == settings.SOMABRAIN_WM_RECENCY_TIME_SCALE
    assert wm._recency_cap == settings.SOMABRAIN_WM_RECENCY_MAX_STEPS


def test_budgeted_predictor_uses_settings_timeout() -> None:
    """Verify BudgetedPredictor uses SOMABRAIN_PREDICTOR_TIMEOUT_MS from settings."""

    bp = BudgetedPredictor(SlowPredictor())
    # BudgetedPredictor uses getattr(settings, "SOMABRAIN_PREDICTOR_TIMEOUT_MS", 1000)
    expected_timeout = getattr(settings, "SOMABRAIN_PREDICTOR_TIMEOUT_MS", None)
    if expected_timeout is None:
        expected_timeout = getattr(settings, "PREDICTOR_TIMEOUT_MS", 1000)
    assert bp.timeout_ms == expected_timeout


def test_rwr_plan_respects_settings_limits() -> None:
    """Execute test rwr plan respects settings limits."""

    class _Mem:
        """Mem class implementation."""

        def __init__(self):
            """Initialize the instance."""

            self.calls = 0

        def coord_for_key(self, task_key, universe=None):
            """Execute coord for key.

            Args:
                task_key: The task_key.
                universe: The universe.
            """

            return (0.0, 0.0, 0.0)

        def links_from(self, coord, type_filter=None, limit=None):
            """Execute links from.

            Args:
                coord: The coord.
                type_filter: The type_filter.
                limit: The limit.
            """

            assert limit == max(1, int(settings.planner_rwr_edges_per_node))
            return []

        def payloads_for_coords(self, coords, universe=None):
            """Execute payloads for coords.

            Args:
                coords: The coords.
                universe: The universe.
            """

            self.calls += 1
            return []

    mem = _Mem()
    out = rwr_plan("t", mem)
    assert out == []


def test_no_direct_getenv_outside_settings() -> None:
    """Execute test no direct getenv outside settings."""

    root = Path(__file__).resolve().parents[1]
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        # Allow settings module and its subpackage (base.py contains the canonical helpers)
        if "common/config/settings" in str(path) or path == Path(__file__):
            continue
        if path.name.endswith("_pb2.py") or "/.venv/" in str(path):
            continue
        # Allow test files to use os.getenv for test configuration
        if "/tests/" in str(path) or str(path).startswith(str(root / "tests")):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "os.getenv(" in text:
            offenders.append(str(path))
    assert not offenders, f"Direct getenv usage detected: {offenders}"
