"""Stub ``sqlalchemy.orm`` submodule.

Only the symbols used in the project are provided: ``declarative_base`` and
``sessionmaker``.  They return simple placeholder objects sufficient for import
time type checking and unit tests where the actual ORM functionality is not
required.
"""

from typing import Any


def declarative_base() -> Any:  # pragma: no cover
    class Base:  # pylint: disable=too-few-public-methods
        pass

    return Base


def sessionmaker(*_, **__) -> Any:  # pragma: no cover
    """Return a callable that mimics ``sqlalchemy.orm.sessionmaker``.

    The returned object can be called to obtain a dummy session with ``add``,
    ``commit`` and ``query`` methods that do nothing.
    """

    class _Session:
        def add(self, *_: Any, **__: Any) -> None:
            pass

        def commit(self) -> None:
            pass

        def query(self, *_: Any, **__: Any) -> Any:
            return []

    return _Session
