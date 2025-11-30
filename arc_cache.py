from __future__ import annotations
from functools import lru_cache, wraps
from typing import Any, Callable, TypeVar

"""
Lightweight ARC-like cache facade.

For development and tests, this provides a simple LRU-based memoization
decorator compatible with the expected `arc_cache(max_size=...)` API.

If you need real ARC semantics later, replace the implementation
with an appropriate library transparently.
"""



F = TypeVar("F", bound=Callable[..., Any])


def arc_cache(max_size: int = 128) -> Callable[[F], F]:  # type: ignore[misc]
def _decorate(fn: F) -> F:  # type: ignore[misc]
        cached = lru_cache(maxsize=max_size)(fn) if max_size and max_size > 0 else fn

@wraps(fn)
def wrapper(*args: Any, **kwargs: Any):  # type: ignore[override]
            return cached(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return _decorate
