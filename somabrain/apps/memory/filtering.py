"""Payload filtering utilities for SomaBrain Memory.

This module provides functions for filtering memory payloads based on
keywords and other criteria.
"""

from __future__ import annotations

from typing import Any, Iterable, List


def _filter_payloads_by_keyword(payloads: Iterable[Any], keyword: str) -> List[dict]:
    """Return payloads that include *keyword* in common string fields.

    The filter is intentionally lightweight so it can run on every recall even
    when the backend service does not support lexical search. If no payloads
    match, the original list is returned to preserve behaviour.

    Args:
        payloads: An iterable of payload dictionaries to filter.
        keyword: The keyword to search for (case-insensitive).

    Returns:
        A list of matching payloads, or the original list if no matches found.
    """
    items: List[dict] = [p for p in payloads if isinstance(p, dict)]
    key = str(keyword or "").strip().lower()
    if not key:
        return items

    filtered: List[dict] = []
    fields = ("what", "headline", "text", "content", "who", "task", "session")
    for entry in items:
        for field in fields:
            value = entry.get(field)
            if isinstance(value, str) and key in value.lower():
                filtered.append(entry)
                break
    return filtered or items
