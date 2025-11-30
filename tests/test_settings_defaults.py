from __future__ import annotations

from pathlib import Path

from common.config.settings import settings
from somabrain.microcircuits import MCConfig
from somabrain.mt_wm import MTWMConfig
from somabrain.planner_rwr import rwr_plan
from somabrain.prediction import BudgetedPredictor, SlowPredictor
from somabrain.wm import WorkingMemory

"""Invariant tests ensuring config defaults are centralized in settings."""


def test_mcconfig_defaults_follow_settings() -> None:
    cfg = MCConfig()
    assert cfg.columns == max(1, int(settings.micro_circuits))
    assert cfg.vote_temperature == settings.micro_vote_temperature
    assert cfg.max_tenants == settings.micro_max_tenants
    assert cfg.recency_time_scale == settings.wm_recency_time_scale
    assert cfg.recency_max_steps == settings.wm_recency_max_steps


def test_mtwm_defaults_follow_settings() -> None:
    cfg = MTWMConfig()
    assert cfg.max_tenants == settings.mtwm_max_tenants
    assert cfg.per_tenant_capacity == max(1, int(settings.wm_per_tenant_capacity))
    assert cfg.recency_time_scale == settings.wm_recency_time_scale
    assert cfg.recency_max_steps == settings.wm_recency_max_steps


def test_working_memory_defaults_use_settings() -> None:
    wm = WorkingMemory(capacity=4, dim=2)
    assert wm.alpha == settings.wm_alpha
    assert wm.beta == settings.wm_beta
    assert wm.gamma == settings.wm_gamma
    assert wm._recency_scale == settings.wm_recency_time_scale
    assert wm._recency_cap == settings.wm_recency_max_steps


def test_budgeted_predictor_uses_settings_timeout() -> None:
    bp = BudgetedPredictor(SlowPredictor())
    assert bp.timeout_ms == settings.predictor_timeout_ms


def test_rwr_plan_respects_settings_limits() -> None:
    class _Mem:
        def __init__(self):
            self.calls = 0

        def coord_for_key(self, task_key, universe=None):
            return (0.0, 0.0, 0.0)

        def links_from(self, coord, type_filter=None, limit=None):
            assert limit == max(1, int(settings.planner_rwr_edges_per_node))
            return []

        def payloads_for_coords(self, coords, universe=None):
            self.calls += 1
            return []

    mem = _Mem()
    out = rwr_plan("t", mem)
    assert out == []


def test_no_direct_getenv_outside_settings() -> None:
    root = Path(__file__).resolve().parents[1]
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if "common/config/settings.py" in str(path) or path == Path(__file__):
            continue
        if path.name.endswith("_pb2.py") or "/.venv/" in str(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "os.getenv(" in text:
            offenders.append(str(path))
    assert not offenders, f"Direct getenv usage detected: {offenders}"
