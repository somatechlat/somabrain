from fastapi import APIRouter, Depends

from somabrain.api.dependencies.utility_guard import utility_guard

router = APIRouter()


@router.get("/demo")
async def demo_endpoint(_guard: None = Depends(utility_guard)):
    """Simple demo endpoint that is protected by the utility guard.

    Returns a JSON payload confirming access. The utility guard will compute the
    utility value and reject the request with a 403 if the value is negative.
    """
    return {"detail": "demo endpoint accessed"}
