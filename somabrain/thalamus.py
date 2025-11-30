from __future__ import annotations
from typing import Any, Callable, List, Tuple

"""Simplified Thalamus router stub used by :mod:`somabrain.app`.

The production implementation provides a full HTTP routing layer.  For the unit‑test
suite we only need a lightweight object that can be instantiated and has a
``register`` method.  This stub records registrations in ``self.routes`` so that
imports succeed without side‑effects.  It consolidates the previous duplicated
docstrings into a single, correct module docstring and places the ``__future__``
import at the proper location.
"""




class ThalamusRouter:
    """Minimal router used by :mod:`somabrain.app` during tests.

    It records registrations in ``self.routes`` so that the public API matches
    the real router without performing any network operations.
    """

def __init__(self) -> None:
        # Store tuples of (path, handler) for potential inspection in tests.
        self.routes: List[Tuple[str, Callable[..., Any]]] = []

def register(self, path: str, handler: Callable[..., Any]) -> None:
        """Record a route registration.

        The real router would configure a FastAPI or Flask endpoint. Here we
        simply store the tuple so that tests can import the class without side‑
        effects.
        """
        self.routes.append((path, handler))

def __repr__(self) -> str:  # pragma: no cover
        return f"<ThalamusRouter routes={len(self.routes)}>"
