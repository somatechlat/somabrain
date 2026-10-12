"""Rust is the sole adaptation-math authority (DEBT-008).

Python orchestration (history, persistence, tenant, metrics) stays in
``AdaptationEngine``. Every numeric weight update MUST go through
``somabrain_rs``. There is no Python twin of the gain law — if the Rust
module is missing, we refuse (Rule 2). Do not reimplement weight_delta here.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from somabrain_rs import AdaptationEngine as _RustAdaptationEngine

    RUST_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - build gate
    RUST_AVAILABLE = False
    _RustAdaptationEngine = None  # type: ignore[assignment,misc]
    logger.error("somabrain_rs not available for adaptation math", exc_info=True)
    raise RuntimeError(
        "Rust AdaptationEngine (somabrain_rs) is required for adaptation math. "
        "Build rust_core before running the learning loop."
    ) from exc


def require_rust_engine(learning_rate: float) -> Any:
    """Return a Rust AdaptationEngine. Refuses if the module is absent."""
    if not RUST_AVAILABLE or _RustAdaptationEngine is None:
        raise RuntimeError(
            "Rust AdaptationEngine (somabrain_rs) is required for adaptation math."
        )
    return _RustAdaptationEngine(learning_rate)


def apply_weight_updates_rust(
    *,
    learning_rate: float,
    retrieval: tuple[float, float, float, float],
    utility: tuple[float, float, float],
    gains: tuple[float, float, float, float, float],
    bounds: tuple[tuple[float, float], ...],
    semantic_signal: float,
    utility_signal: float,
) -> tuple[tuple[float, float, float, float], tuple[float, float, float]]:
    """Apply one adaptation step in Rust. Returns updated (retrieval, utility).

    Retrieval is ``(alpha, beta, gamma, tau)``; utility is ``(lambda_, mu, nu)``.
    Gains are ``(alpha, gamma, lambda_, mu, nu)``.
    Bounds order: alpha, gamma, lambda_, mu, nu.
    """
    eng = require_rust_engine(learning_rate)
    a, b, g, t = retrieval
    lam, mu, nu = utility
    eng.set_retrieval(float(a), float(b), float(g), float(t))
    eng.set_utility(float(lam), float(mu), float(nu))
    eng.set_gains(*(float(x) for x in gains))
    flat = tuple(float(x) for pair in bounds for x in pair)
    if len(flat) != 10:
        raise ValueError("bounds must be 5 (min,max) pairs")
    eng.set_constraints(*flat)
    eng.learning_rate = float(learning_rate)
    # Rust: apply_feedback(utility_signal, reward=semantic_signal)
    eng.apply_feedback(float(utility_signal), float(semantic_signal))
    return eng.get_retrieval(), eng.get_utility()
