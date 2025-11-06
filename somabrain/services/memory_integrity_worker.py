"""REMOVED: Legacy Memory Integrity Worker.

This module has been removed as part of the strict "no fallbacks/no stubs" policy.
It previously contained placeholder checks across Redis/Postgres/vector/sqlite.

Do not import or use this module. Use production monitoring and the HTTP memory
service health endpoints instead.
"""

raise ImportError(
    "somabrain.services.memory_integrity_worker was removed. Use external monitoring and the HTTP memory service."
)
