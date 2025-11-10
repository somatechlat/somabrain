from __future__ import annotations

import json
import os
from typing import Dict, List

from fastapi import APIRouter, HTTPException

from somabrain.modes import mode_config


router = APIRouter(prefix="/features", tags=["features"])


@router.get("")
async def features_status() -> Dict:
    cfg = mode_config()
    status = cfg.as_dict()
    path = os.getenv("SOMABRAIN_FEATURE_OVERRIDES", "./data/feature_overrides.json")
    overrides: Dict = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            overrides = json.load(f)
    except Exception:
        overrides = {}
    return {"mode": cfg.name, "matrix": status, "overrides": overrides}


def _write_overrides(disabled: List[str]) -> None:
    path = os.getenv("SOMABRAIN_FEATURE_OVERRIDES", "./data/feature_overrides.json")
    try:
        import pathlib

        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump({"disabled": list(disabled)}, f, indent=2)
    except Exception:
        pass


@router.post("/disable")
async def features_disable(body: Dict[str, List[str]]):
    names = body.get("names") or []
    if not isinstance(names, list):
        raise HTTPException(status_code=400, detail="names must be a list")
    # Record conceptual disables only; no env mutation
    _write_overrides(names)
    return {"ok": True, "disabled": names}


@router.post("/enable")
async def features_enable(body: Dict[str, List[str]]):
    names = body.get("names") or []
    if not isinstance(names, list):
        raise HTTPException(status_code=400, detail="names must be a list")
    # Clearing overrides restores mode-derived defaults
    _write_overrides([])
    return {"ok": True, "enabled": names}
