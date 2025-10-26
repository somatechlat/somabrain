import pytest

from somabrain.config import Config
from somabrain.services.config_service import ConfigService
from somabrain.services.cutover_controller import CutoverController, CutoverError


@pytest.mark.asyncio
async def test_cutover_open_approve_execute_ready():
    cfg_service = ConfigService(lambda: Config())
    controller = CutoverController(cfg_service)

    plan = await controller.open_plan("tenantA", "ns-blue", "ns-green")
    assert plan.status == "draft"
    assert plan.ready is False

    # Record strong shadow metrics so plan becomes ready
    plan = await controller.record_shadow_metrics(
        "tenantA",
        "ns-green",
        top1_accuracy=0.95,
        margin=0.2,
        latency_p95_ms=50.0,
    )
    assert plan.ready is True

    plan = await controller.approve("tenantA")
    assert plan.status == "approved"

    plan = await controller.execute("tenantA")
    assert plan.status == "executed"


@pytest.mark.asyncio
async def test_cutover_reject_mismatched_namespace():
    cfg_service = ConfigService(lambda: Config())
    controller = CutoverController(cfg_service)

    await controller.open_plan("tenantB", "ns-1", "ns-2")

    with pytest.raises(CutoverError):
        await controller.record_shadow_metrics(
            "tenantB", "ns-wrong", top1_accuracy=0.9, margin=0.2, latency_p95_ms=10.0
        )
