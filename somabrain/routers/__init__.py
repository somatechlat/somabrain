"""SomaBrain API Routers - Modular FastAPI routers extracted from app.py."""

from somabrain.routers.admin import router as admin_router
from somabrain.routers.cognitive import router as cognitive_router
from somabrain.routers.health import router as health_router
from somabrain.routers.neuromod import router as neuromod_router
from somabrain.routers.proxy import router as proxy_router
from somabrain.routers.sleep import router as sleep_router

__all__ = [
    "admin_router",
    "cognitive_router",
    "health_router",
    "neuromod_router",
    "proxy_router",
    "sleep_router",
]

