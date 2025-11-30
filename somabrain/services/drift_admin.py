"""
Removed: Drift introspection HTTP surface.

Reason:
    pass
- Centralized parity mode requires minimal, consistent surfaces.
- Use Prometheus metrics and `scripts/drift_dump.py` for state introspection.

This module is intentionally empty to avoid accidental HTTP exposure.
"""
