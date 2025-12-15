"""
API Schemas Module for SomaBrain - Re-export Layer.

This file re-exports all schemas from the decomposed schemas/ package
for backward compatibility. All existing imports will continue to work.

The actual schema definitions are now in:
- somabrain/schemas/memory.py - Memory operation schemas
- somabrain/schemas/cognitive.py - Cognitive/planning schemas
- somabrain/schemas/health.py - Health, admin, and operational schemas

For new code, prefer importing from the specific submodules:
    from somabrain.schemas.memory import RecallRequest
    from somabrain.schemas.cognitive import ActRequest
    from somabrain.schemas.health import HealthResponse
"""

# Re-export everything from the schemas package for backward compatibility
# This allows `from somabrain.schemas import X` to work for any schema X
from somabrain.schemas import *  # noqa: F401, F403
