from __future__ import annotations

from typing import Dict

from fastapi import APIRouter

from config.feature_flags import FeatureFlags


router = APIRouter(prefix="/features", tags=["features"])


@router.get("")
async def features_status() -> Dict:
    # Centralized flags only; overrides removed for enterprise mode.
    status = FeatureFlags.get_status()
    return {"status": status}


@router.post("/disable")
async def features_disable(body: Dict[str, List[str]]):
    # Interface retained, but dynamic disabling removed in centralized mode.
    return {"ok": False, "error": "dynamic disabling removed"}


@router.post("/enable")
async def features_enable(body: Dict[str, List[str]]):
    return {"ok": False, "error": "dynamic enabling removed"}
