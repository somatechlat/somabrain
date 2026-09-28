"""Module constitution."""


from somabrain.constitution import ConstitutionEngine

_engine: ConstitutionEngine | None = None


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
        except Exception as exc:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load constitution engine: {exc}")
    return _engine
