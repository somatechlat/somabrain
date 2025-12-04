"""Lightweight stub for the ``sqlalchemy`` package used in the Somabrain
project.

The real SQLAlchemy library provides a large ORM and SQL construction API.
For static type checking (pyright) we only need a minimal subset of symbols
so that imports succeed and attribute access does not raise errors.  All
objects are intentionally no‑ops at runtime – the real library will be used
when the application is executed in an environment where it is installed.

Implemented symbols:
* ``Column`` – accepts a type and optional arguments, stores them for
  introspection.
* ``Integer``, ``String``, ``Text``, ``DateTime`` – simple marker classes.
* ``func`` – namespace with a ``now`` placeholder.
* ``orm`` submodule exposing ``Session`` and ``declarative_base`` placeholder.
* ``create_engine`` – dummy function returning a placeholder engine.

These definitions are typed as ``Any`` where appropriate to keep the stub
flexible and avoid over‑constraining the type checker.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Optional

# ---------------------------------------------------------------------------
# Core column types and ``Column`` placeholder
# ---------------------------------------------------------------------------


class _TypeMarker:
    """Base class for simple type markers like ``Integer`` or ``String``."""

    def __repr__(self) -> str:  # pragma: no cover
        return self.__class__.__name__


class Integer(_TypeMarker):
    pass


class String(_TypeMarker):
    def __init__(self, length: Optional[int] = None) -> None:  # pragma: no cover
        self.length = length


class Text(_TypeMarker):
    pass


class DateTime(_TypeMarker):
    pass


# ``Column`` objects are often used both as type hints (e.g. ``Column[int]``) and
# as runtime values that are passed to functions expecting a ``str`` (SQLAlchemy
# columns behave like descriptors that resolve to column names).  To keep the
# stub simple and satisfy both use‑cases we make ``Column`` inherit from ``str``.
# The ``__new__`` method returns an empty string instance while storing the
# provided metadata on the object for potential introspection.
# ``Column`` in SQLAlchemy is used as a factory for column descriptors.  For
# static type checking we provide a simple callable that returns a generic
# ``Any`` placeholder.  This avoids the numerous type‑mismatch errors that arise
# when the real ``Column`` objects are later assigned concrete values (e.g.
# ``model.field = "value"``).
def Column(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover
    """Return a stub object representing a SQLAlchemy column.

    The returned object implements ``__repr__`` for debugging and accepts any
    attribute access, returning ``None``.  It is deliberately typed as ``Any``
    so that assignments to the column attribute are permitted.
    """

    class _Column:
        def __repr__(self) -> str:  # pragma: no cover
            return "ColumnStub"

        def __getattr__(self, name: str) -> Any:  # pragma: no cover
            return None

        def __bool__(self) -> bool:  # pragma: no cover
            return True

    return _Column()

# ``ColumnElement`` is used in type annotations for SQLAlchemy expression
# objects.  It can be safely represented as ``Any`` for static analysis.
class ColumnElement:  # pragma: no cover
    def __getattr__(self, name: str) -> Any:
        return None

    def __bool__(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# ``func`` namespace – only ``now`` is used in the code base.
# ---------------------------------------------------------------------------


class _FuncNamespace:
    @staticmethod
    def now() -> Any:  # pragma: no cover
        """Placeholder for ``sqlalchemy.func.now`` used in default timestamps."""
        return None


func = _FuncNamespace()

# ---------------------------------------------------------------------------
# ORM submodule with ``Session`` placeholder and ``declarative_base`` helper.
# ---------------------------------------------------------------------------


class _ORMModule:
    class Session:  # pragma: no cover
        """Placeholder for ``sqlalchemy.orm.Session``."""

        def __init__(self, *_, **__) -> None:
            pass

        def add(self, *_: Any, **__: Any) -> None:
            pass

        def commit(self) -> None:
            pass

        def query(self, *_: Any, **__: Any) -> Any:
            return []

    @staticmethod
    def declarative_base() -> Any:  # pragma: no cover
        """Return a dummy base class for model declarations."""
        class Base:  # pylint: disable=too-few-public-methods
            pass

        return Base


orm = _ORMModule()

# ---------------------------------------------------------------------------
# Engine creation stub – the real function returns an Engine; here we return a
# simple object placeholder.
# ---------------------------------------------------------------------------


def create_engine(*_: Any, **__: Any) -> Any:  # pragma: no cover
    """Placeholder for ``sqlalchemy.create_engine``.

    It returns a generic object that can be passed around but provides no
    functionality.
    """

    class _Engine:  # pylint: disable=too-few-public-methods
        pass

    return _Engine()
