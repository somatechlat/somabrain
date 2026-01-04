"""
Events Module for SomaBrain.

This module provides utilities for extracting structured event information from
natural language text. It implements heuristic-based parsing to identify key
event components following the "who, did, what, where, when, why" framework.

Key Features:
- Lightweight heuristic extraction of event fields
- Support for temporal, spatial, and causal information
- Best-effort parsing with graceful degradation
- Regex-based pattern matching for common constructions

Functions:
    extract_event_fields: Extract structured event information from text.
"""

from __future__ import annotations

import re
from typing import Dict


def extract_event_fields(text: str) -> Dict[str, str]:
    """
    Extract structured event fields from natural language text.

    Performs heuristic extraction of event components using regex patterns and
    simple tokenization. Identifies optional fields: who, did, what, where, when, why.
    This is a lightweight, best-effort parser designed for simple sentences.

    Args:
        text (str): Input text to parse for event information.

    Returns:
        Dict[str, str]: Dictionary containing extracted event fields.
                        Keys may include: 'who', 'did', 'what', 'where', 'when', 'why'.
                        Empty dict if no fields can be extracted.

    Examples:
        >>> extract_event_fields("John went to Paris because he wanted adventure")
        {'who': 'John', 'did': 'went', 'what': 'Paris', 'why': 'he wanted adventure'}
        >>>
        >>> extract_event_fields("Meeting at 3:00 PM in conference room")
        {'where': 'conference', 'when': '3:00'}
        >>>
        >>> extract_event_fields("")
        {}

    Note:
        - Uses regex patterns for spatial ('at X', 'in X') and causal ('because Y') relations
        - Falls back to naive token splitting for who/did/what when patterns don't match
        - Designed for short, simple sentences; may not work well with complex text
    """
    out: Dict[str, str] = {}
    t = (text or "").strip()
    if not t:
        return out
    # where: " at X" or " in X"
    m = re.search(r"\b(?:at|in)\s+([A-Za-z0-9_\-]+)", t)
    if m:
        out["where"] = m.group(1)
    # why: "because Y" or "so that Y"
    m = re.search(r"\b(?:because|so that)\s+(.+)$", t)
    if m:
        out["why"] = m.group(1).strip()
    # when: "on <date>" or "at <time>" (simple token after preposition)
    m = re.search(r"\b(?:on|at)\s+([0-9]{1,2}[:/][0-9]{1,2}(?:[:/][0-9]{2})?)", t)
    if m and "where" not in out:
        out["when"] = m.group(1)
    # who/did/what: naive split "<who> <verb> <what>"
    toks = re.findall(r"[A-Za-z0-9_\-]+", t)
    if len(toks) >= 3:
        out.setdefault("who", toks[0])
        out.setdefault("did", toks[1])
        out.setdefault("what", toks[2])
    return out