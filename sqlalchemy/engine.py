"""Stub ``sqlalchemy.engine`` submodule.

The production code imports ``Engine`` from ``sqlalchemy.engine`` for type
annotations.  In the test environment the real SQLAlchemy library is not
installed, so we provide a minimal placeholder that satisfies the import
without adding any runtime behaviour.
"""

class Engine:  # pragma: no cover
    """Placeholder class representing ``sqlalchemy.engine.Engine``.

    Instances of this class are never created in the test suite; the class
    exists solely to allow ``from sqlalchemy.engine import Engine`` to succeed.
    """

    def __init__(self, *_, **__) -> None:
        pass
