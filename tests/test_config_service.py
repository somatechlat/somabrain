from __future__ import annotations

import asyncio
import copy

import pytest

from somabrain.config import Config
from somabrain.services.config_service import (
    ConfigEvent,
    ConfigMergeError,
    ConfigService,
)


def _base_config() -> Config:
    cfg = Config()
    cfg.rate_rps = 50.0
    cfg.http.endpoint = "https://base"
    cfg.http.token = None
    return cfg


@pytest.mark.asyncio
async def test_global_patch_merges_and_audits() -> None:
    service = ConfigService(lambda: copy.deepcopy(_base_config()))

    await service.patch_global({"rate_rps": 120.0}, actor="ops")
    effective = service.effective_config("tenant-a", "wm")

    assert effective["rate_rps"] == pytest.approx(120.0)

    audit = service.audit_log()[-1]
    assert audit.scope == "global"
    assert audit.actor == "ops"
    assert audit.after["rate_rps"] == pytest.approx(120.0)


@pytest.mark.asyncio
async def test_namespace_patch_overrides_nested_values_and_emits_event() -> None:
    service = ConfigService(lambda: copy.deepcopy(_base_config()))
    queue = service.subscribe()

    await service.patch_namespace(
        "tenant-a",
        "wm",
        {"http": {"endpoint": "https://tenant-a"}},
        actor="supervisor",
    )

    effective = service.effective_config("tenant-a", "wm")
    assert effective["http"]["endpoint"] == "https://tenant-a"

    event: ConfigEvent = await asyncio.wait_for(queue.get(), timeout=0.1)
    assert event.tenant == "tenant-a"
    assert event.version == effective["version"]
    assert event.payload["http"]["endpoint"] == "https://tenant-a"


@pytest.mark.asyncio
async def test_invalid_patch_rejected() -> None:
    service = ConfigService(lambda: copy.deepcopy(_base_config()))
    with pytest.raises(ConfigMergeError):
        await service.patch_namespace(
            "tenant-a",
            "wm",
            {"rate_rps": float("nan")},
            actor="ops",
        )
