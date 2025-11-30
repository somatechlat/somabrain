from __future__ import annotations
from fastapi import APIRouter, HTTPException
from somabrain.services.calibration_service import calibration_service
from common.logging import logger




router = APIRouter(prefix="/calibration", tags=["calibration"])


@router.get("/status")
async def calibration_status():
    if not calibration_service.enabled:
        return {"enabled": False}
    return calibration_service.get_all_calibration_status()


@router.get("/{domain}/{tenant}")
async def calibration_get(domain: str, tenant: str):
    if not calibration_service.enabled:
        return {"enabled": False}
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return calibration_service.get_calibration_status(domain, tenant)
    except Exception as e:
        logger.exception("Exception caught: %s", e)
        raise
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/reliability/{domain}/{tenant}")
async def calibration_reliability(domain: str, tenant: str):
    if not calibration_service.enabled:
        return {"enabled": False}
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return calibration_service.export_reliability_data(domain, tenant)
    except Exception as e:
        logger.exception("Exception caught: %s", e)
        raise
    raise HTTPException(status_code=500, detail=str(e))
