from __future__ import annotations

import pytest

from somabrain.config import Config
from somabrain.services.config_service import ConfigService
from somabrain.services.cutover_controller import CutoverController, CutoverError


def _service() -> ConfigService:
    return ConfigService(lambda: Config())


async def _seed(service: ConfigService, tenant: str, namespace: str, top1: float, margin: float) -> None:
    await service.patch_namespace(
        tenant,
        namespace,
        {
            "targets": {"top1": top1, "margin": margin},
            "latency_p95_ms": 90.0,
        },
        actor="bootstrap",
    )


@pytest.mark.asyncio
async def test_cutover_flow_success() -> None:
    service = _service()
    await _seed(service, "tenant-a", "wm@v1", 0.9, 0.12)
    await _seed(service, "tenant-a", "wm@v2", 0.9, 0.12)

    controller = CutoverController(service, readiness_margin=0.0, latency_budget_factor=1.10)

    plan = await controller.open_plan("tenant-a", "wm@v1", "wm@v2")
    assert plan.status == "draft"

    plan = await controller.record_shadow_metrics(
        "tenant-a",
        "wm@v2",
        top1_accuracy=0.88,
        margin=0.10,
        latency_p95_ms=80.0,
    )
    assert plan.ready is False

    plan = await controller.record_shadow_metrics(
        "tenant-a",
        "wm@v2",
        top1_accuracy=0.91,
        margin=0.13,
        latency_p95_ms=85.0,
    )
    assert plan.ready is True

    plan = await controller.approve("tenant-a")
    assert plan.status == "approved"

    plan = await controller.execute("tenant-a")
    assert plan.status == "executed"


@pytest.mark.asyncio
async def test_cutover_guards() -> None:
    service = _service()
    await _seed(service, "tenant-a", "wm@v1", 0.9, 0.12)
    await _seed(service, "tenant-a", "wm@v2", 0.9, 0.12)

    controller = CutoverController(service)
    await controller.open_plan("tenant-a", "wm@v1", "wm@v2")

    with pytest.raises(CutoverError):
        await controller.open_plan("tenant-a", "wm@v1", "wm@v3")

    with pytest.raises(CutoverError):
        await controller.approve("tenant-a")

    with pytest.raises(CutoverError):
        await controller.execute("tenant-a")

    await controller.record_shadow_metrics(
        "tenant-a",
        "wm@v2",
        top1_accuracy=0.92,
        margin=0.12,
        latency_p95_ms=80.0,
    )
    await controller.approve("tenant-a")
    plan = await controller.execute("tenant-a")
    assert plan.status == "executed"