"""
Lightweight *type‑only* stub for the ``pymilvus`` package.

The real ``pymilvus`` SDK is an optional heavyweight dependency
required only when the Milvus vector store is available.
This stub provides just enough symbols for **static analysis** (Pyright)
so the codebase type‑checks without pulling in the actual library.

*No runtime code* is executed – the real package will be imported if it
is installed in the environment, because Python prefers an installed
distribution over a local module of the same name.
"""

from __future__ import annotations

from typing import Any, List

# ----------------------------------------------------------------------
# Public exception type used throughout the code.
# ----------------------------------------------------------------------
class MilvusException(Exception):
    """Base exception raised by the real Milvus SDK."""
    pass


# ----------------------------------------------------------------------
# Connection helper – the real SDK provides a ``connections`` singleton
# with a ``connect`` method.  Here we expose a dummy object with the same
# attribute so the type‑checker can resolve it.
# ----------------------------------------------------------------------
class _Conn:
    @staticmethod
    def connect(*_: Any, **__: Any) -> None:  # pragma: no cover
        """No‑op placeholder for ``pymilvus.connections.connect``."""
        pass

    @staticmethod
    def disconnect(alias: str = "default") -> None:  # pragma: no cover
        """Placeholder matching the real SDK signature."""
        pass

    @staticmethod
    def get_connection_addr(alias: str = "default") -> str | None:  # pragma: no cover
        return None

    @staticmethod
    def get_connection(alias: str = "default") -> Any:  # pragma: no cover
        return None


connections = _Conn()


# ----------------------------------------------------------------------
# Utility helper – the real SDK offers ``has_collection``.
# ----------------------------------------------------------------------
class _Util:
    @staticmethod
    def has_collection(_name: str) -> bool:  # pragma: no cover
        """Always return ``False`` in the stub environment."""
        return False

    @staticmethod
    def create_collection(name: str, schema: CollectionSchema, **_: Any) -> Collection:  # pragma: no cover
        return Collection(name, schema)

    @staticmethod
    def drop_collection(name: str, **_: Any) -> None:  # pragma: no cover
        return None

    @staticmethod
    def get_collection_stats(name: str, **_: Any) -> dict:  # pragma: no cover
        return {}


utility = _Util()


# ----------------------------------------------------------------------
# Schema objects – only the attributes accessed in the code base are
# defined.  They deliberately accept ``**kwargs`` so that any extra
# arguments used by the real SDK are ignored safely.
# ----------------------------------------------------------------------
class FieldSchema:
    def __init__(self, *, name: str, dtype: Any, max_length: int = 0,
                 is_primary: bool = False, dim: int = 0, **_: Any) -> None:
        self.name = name
        self.dtype = dtype
        self.max_length = max_length
        self.is_primary = is_primary
        self.dim = dim


class CollectionSchema:
    def __init__(self, fields: List[FieldSchema], description: str = "", **_: Any) -> None:
        self.fields = fields
        self.description = description


class DataType:
    """Mimic the enum‑like attributes used in the code."""
    VARCHAR = "VARCHAR"
    FLOAT_VECTOR = "FLOAT_VECTOR"
    # The codebase also references ``INT64`` – provide it for type checking.
    INT64 = "INT64"


# ----------------------------------------------------------------------
# Collection class – provides the minimal API used by ``MilvusClient``.
# ----------------------------------------------------------------------
class Collection:
    def __init__(self, name: str, schema: CollectionSchema | None = None, **_: Any) -> None:
        self.name = name
        self.schema = schema
        self._entities: List[tuple] = []

    def search(self, *, data: List[Any], anns_field: str, param: dict,
               limit: int, expr: str, output_fields: List[str]) -> List[List[Any]]:
        """Return an empty result set – the stub never performs a search."""
        return [[]]

    def insert(self, entities: List[Any]) -> None:  # pragma: no cover
        self._entities.append(tuple(entities))

    def flush(self) -> None:  # pragma: no cover
        pass

    def create_index(self, *, field_name: str, index_params: dict) -> None:  # pragma: no cover
        pass

    def load(self) -> None:  # pragma: no cover
        pass

    def release(self) -> None:  # pragma: no cover
        pass

    def delete(self, *_, **__) -> None:  # pragma: no cover
        """Placeholder for the SDK ``delete`` method used in the code base."""
        pass

    def query(self, *_, **__) -> List[Any]:  # pragma: no cover
        """Return an empty list to satisfy type checking for ``query`` calls."""
        return []

    @property
    def indexes(self) -> List[Any]:  # pragma: no cover
        """Expose an ``indexes`` attribute expected by the code (iterable)."""
        return []
