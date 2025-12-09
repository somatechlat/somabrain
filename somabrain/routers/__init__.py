"""SomaBrain API Routers - Modular FastAPI routers extracted from app.py."""

from somabrain.routers.admin import router as admin_router
from somabrain.routers.health import router as health_router
from somabrain.routers.memory import router as memory_router
from somabrain.routers.neuromod import router as neuromod_router

__all__ = ["admin_router", "health_router", "memory_router", "neuromod_router"]

