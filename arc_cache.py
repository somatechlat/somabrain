"""Small ARC-like cache shim used for tests when the real package
is not available. Provides a decorator `arc_cache(max_size)` that
wraps a function with functools.lru_cache(maxsize=max_size).

This is intentionally minimal and conservative: it provides a stable
in-process memoization compatible with the project's use in tests.
"""

from functools import lru_cache, wraps
from typing import Callable


def arc_cache(max_size: int = 128) -> Callable:
    """Return a decorator that caches calls to the wrapped function.

    Args:
        max_size: maximum number of entries to store in the cache.
    """

    def decorator(fn: Callable) -> Callable:
        """TODO: Add docstring."""
        cached = lru_cache(maxsize=max_size)(fn)

        @wraps(fn)
        def wrapper(*args, **kwargs):
            """TODO: Add docstring."""
            return cached(*args, **kwargs)

        wrapper.cache_clear = cached.cache_clear
        return wrapper

    return decorator
