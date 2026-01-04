"""Property test verifying dead code removal.

**Feature: production-readiness-audit, Property 2: Dead Code Elimination**
**Validates: Requirements 4.1, 2.2, 2.3**

This test verifies that dead code modules have been removed from the codebase.
"""

from pathlib import Path

import pytest


# List of modules that were identified as dead code and should be removed
DEAD_CODE_MODULES = [
    "somabrain/somabrain/services/planning_service.py",
    "somabrain/somabrain/cognitive/planning.py",
]


@pytest.mark.parametrize("module_path", DEAD_CODE_MODULES)
def test_dead_code_module_removed(module_path: str) -> None:
    """Verify that identified dead code modules have been removed.

    **Feature: production-readiness-audit, Property 2: Dead Code Elimination**
    **Validates: Requirements 4.1, 2.2, 2.3**
    """
    # Get the workspace root (somabrain is a workspace folder)
    workspace_root = Path(__file__).resolve().parents[2]
    full_path = workspace_root / module_path.replace("somabrain/", "", 1)

    assert not full_path.exists(), (
        f"Dead code module should be removed: {module_path}\nFull path: {full_path}"
    )


def test_planning_service_not_importable() -> None:
    """Verify that planning_service cannot be imported.

    **Feature: production-readiness-audit, Property 2: Dead Code Elimination**
    **Validates: Requirements 2.2**
    """
    with pytest.raises(ImportError):
        from somabrain.services import planning_service  # noqa: F401


def test_cognitive_planning_not_importable() -> None:
    """Verify that cognitive.planning cannot be imported.

    **Feature: production-readiness-audit, Property 2: Dead Code Elimination**
    **Validates: Requirements 2.3**
    """
    with pytest.raises(ImportError):
        from somabrain.cognitive import planning  # noqa: F401
