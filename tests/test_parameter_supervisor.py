from __future__ import annotations

import pytest

from somabrain.config import Config
from somabrain.services.config_service import ConfigService
from somabrain.services.parameter_supervisor import (
    MetricsSnapshot,
    ParameterSupervisor,
    SupervisorPolicy,
)


def _config_service() -> ConfigService:
    return ConfigService(lambda: Config())


async def _seed_namespace(service: ConfigService) -> None:
    await service.patch_namespace(
        "tenant-a",
        "wm",
        {
            "eta": 0.05,
            "gate": {"tau": 0.65},
            "cleanup": {"hnsw": {"efSearch": 128}},
            "targets": {"top1": 0.9, "margin": 0.12},
        },
        actor="bootstrap",
    )


class _Clock:
    def __init__(self) -> None:
        self._now = 0.0

    def __call__(self) -> float:  # pragma: no cover - simple getter
        return self._now

    def advance(self, delta: float) -> None:
        self._now += delta


@pytest.mark.asyncio
async def test_supervisor_adjusts_when_metrics_below_targets() -> None:
    service = _config_service()
    await _seed_namespace(service)

    clock = _Clock()
    policy = SupervisorPolicy(min_interval_seconds=0.0)
    supervisor = ParameterSupervisor(service, policy, clock=clock)

    patch = await supervisor.evaluate(
        MetricsSnapshot(
            tenant="tenant-a",
            namespace="wm",
            top1_accuracy=0.82,
            margin=0.05,
            latency_p95_ms=120.0,
        )
    )

    assert patch is not None
    assert patch["eta"] == pytest.approx(0.06)

    assert isinstance(patch["cleanup"], dict)
    cleanup = patch["cleanup"]
    assert isinstance(cleanup.get("hnsw"), dict)
    assert cleanup["hnsw"]["efSearch"] == 144

    assert isinstance(patch["gate"], dict)
    gate = patch["gate"]
    assert gate["tau"] == pytest.approx(0.63)

    effective = service.effective_config("tenant-a", "wm")
    assert effective["eta"] == pytest.approx(0.06)
    assert effective["cleanup"]["hnsw"]["efSearch"] == 144
    assert effective["gate"]["tau"] == pytest.approx(0.63)


@pytest.mark.asyncio
async def test_supervisor_respects_min_interval_and_targets_met() -> None:
    service = _config_service()
    await _seed_namespace(service)

    clock = _Clock()
    policy = SupervisorPolicy(min_interval_seconds=30.0)
    supervisor = ParameterSupervisor(service, policy, clock=clock)

    first = await supervisor.evaluate(
        MetricsSnapshot("tenant-a", "wm", 0.80, 0.08, 90.0)
    )
    assert first is not None

    second = await supervisor.evaluate(
        MetricsSnapshot("tenant-a", "wm", 0.95, 0.15, 90.0)
    )
    assert second is None  # interval not elapsed

    clock.advance(30.0)

    third = await supervisor.evaluate(
        MetricsSnapshot("tenant-a", "wm", 0.94, 0.14, 90.0)
    )
    assert third is None  # metrics meet targets