"""Module constitution."""

from typing import Optional
from somabrain.constitution import ConstitutionEngine

_engine: Optional[ConstitutionEngine] = None


def get_constitution_engine() -> ConstitutionEngine:
    """Retrieve constitution engine."""

    global _engine
    if _engine is None:
        # Initialize with settings, allowing env vars or defaults
        # We can pass specific args if needed, but defaults in __init__ cover most cases
        # relying on settings module
        _engine = ConstitutionEngine()
        # Optionally load initial state
        try:
            _engine.load()
        except Exception:
            pass  # Fail silent on load as per original pattern or log warning
    return _engine
