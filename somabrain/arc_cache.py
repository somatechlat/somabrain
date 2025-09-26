"""Arc cache shim for internal use.

Provides the same `arc_cache` decorator as the top-level module, allowing imports
within the `somabrain` package without relying on the repository root being on
`PYTHONPATH`.
"""

from functools import lru_cache, wraps
from typing import Callable


def arc_cache(max_size: int = 128) -> Callable:
    """Return a decorator that caches calls to the wrapped function.

    Args:
        max_size: maximum number of entries to store in the cache.
    """

    def decorator(fn: Callable) -> Callable:
        cached = lru_cache(maxsize=max_size)(fn)

        @wraps(fn)
        def wrapper(*args, **kwargs):
            return cached(*args, **kwargs)

        # expose cache_clear for tests that need to reset
        wrapper.cache_clear = cached.cache_clear
        return wrapper

    return decorator
