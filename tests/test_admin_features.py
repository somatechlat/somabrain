from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ.setdefault("SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", "0")
if "somabrain.runtime_module" not in sys.modules:
    sys.modules["somabrain.runtime_module"] = SimpleNamespace(
        embedder=object(),
        mt_wm=object(),
        mc_wm=object(),
        set_singletons=lambda **kwargs: None,
    )

from somabrain.app import admin_features_state, admin_features_update
from config.feature_flags import FeatureFlags
from somabrain import schemas as S


@pytest.mark.asyncio
async def test_admin_features_state(monkeypatch):
    monkeypatch.setattr(FeatureFlags, "get_status", lambda: {"foo": True})
    monkeypatch.setattr(FeatureFlags, "get_overrides", lambda: ["foo"])
    resp = await admin_features_state()
    assert resp.status == {"foo": True}
    assert resp.overrides == ["foo"]


@pytest.mark.asyncio
async def test_admin_features_update_success(monkeypatch):
    monkeypatch.setattr(FeatureFlags, "KEYS", ["hmm_segmentation"])
    monkeypatch.setattr(FeatureFlags, "set_overrides", lambda disabled: True)
    monkeypatch.setattr(FeatureFlags, "get_status", lambda: {"hmm_segmentation": False})
    monkeypatch.setattr(FeatureFlags, "get_overrides", lambda: ["hmm_segmentation"])
    body = S.FeatureFlagsUpdateRequest(disabled=["hmm_segmentation"])
    resp = await admin_features_update(body)
    assert resp.overrides == ["hmm_segmentation"]


@pytest.mark.asyncio
async def test_admin_features_update_unknown(monkeypatch):
    monkeypatch.setattr(FeatureFlags, "KEYS", ["fusion_normalization"])
    body = S.FeatureFlagsUpdateRequest(disabled=["bogus"])
    with pytest.raises(HTTPException) as exc:
        await admin_features_update(body)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_admin_features_update_forbidden(monkeypatch):
    monkeypatch.setattr(FeatureFlags, "KEYS", ["calibration"])
    monkeypatch.setattr(FeatureFlags, "set_overrides", lambda disabled: False)
    body = S.FeatureFlagsUpdateRequest(disabled=["calibration"])
    with pytest.raises(HTTPException) as exc:
        await admin_features_update(body)
    assert exc.value.status_code == 403
