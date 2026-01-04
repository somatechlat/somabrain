"""
Reality Monitor Module for SomaBrain

This module implements reality checking and truthfulness assessment for memory
operations. It evaluates the reliability and grounding of information based on
the number of corroborating sources and provides confidence scores.

Key Features:
- Source counting for truthfulness assessment
- Confidence scoring based on evidence strength
- Configurable minimum source requirements
- Metrics collection for reality check outcomes
- Integration with memory retrieval operations

Reality Assessment:
- OK: Sufficient sources meet minimum requirements
- Low: Insufficient sources for reliable assessment
- Confidence: Normalized score based on source count vs requirements

Applications:
- Memory recall validation
- Information reliability assessment
- Confidence-based decision making
- Quality control for retrieved memories

Functions:
    assess_reality: Main reality assessment function

Classes:
    None (utility function-based implementation)
"""

from __future__ import annotations

from typing import Any, Dict, List

from .metrics import REALITY_LOW, REALITY_OK


def assess_reality(
    mem_payloads: List[Dict[str, Any]], min_sources: int = 1
) -> Dict[str, Any]:
    """Simple truthfulness check: count sources and emit a confidence heuristic.

    - ok: True if len(mem_payloads) >= min_sources
    - sources: number of memory payloads considered
    - confidence: min(1, sources / max(1, min_sources*2))
    """
    sources = len(mem_payloads or [])
    ok = bool(sources >= max(0, int(min_sources)))
    conf = min(1.0, float(sources) / float(max(1, min_sources * 2)))
    try:
        (REALITY_OK if ok else REALITY_LOW).inc()
    except Exception:
        pass
    return {"ok": ok, "sources": sources, "confidence": conf}