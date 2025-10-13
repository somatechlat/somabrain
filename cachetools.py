try:
    from cachetools import TTLCache  # type: ignore
except Exception:  # pragma: no cover - helpful error for developers
    raise ImportError(
        "The 'cachetools' package is required. Install it with: pip install cachetools"
    )
__all__ = ["TTLCache"]
