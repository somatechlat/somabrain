"""Lightweight stub for somabrain.services used only for documentation builds.

Provides minimal placeholders for service objects referenced by autosummary.
"""

from typing import Any, List


class RecallService:
    """Stub recall service used for docs."""

    def recall(
        self, query: str, top_k: int = 3, universe: str | None = None
    ) -> List[Any]:
        return []


class MemoryService:
    """Stub memory service used for docs."""

    def store(self, payload: Any) -> bool:
        return True


class PlanningService:
    """Stub planning service used for docs."""

    def suggest(self, task_key: str, max_steps: int = 3) -> List[str]:
        return []


recall_service = RecallService()
memory_service = MemoryService()
planning_service = PlanningService()
