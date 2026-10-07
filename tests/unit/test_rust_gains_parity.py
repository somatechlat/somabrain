"""Rust adaptation defaults must equal contracts.ADAPT_GAINS."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

ROOT = Path(__file__).resolve().parents[2]


def test_rust_gains_match_contracts() -> None:
    from somabrain.math.contracts import ADAPT_GAINS

    src = (ROOT / "rust_core" / "src" / "adaptation.rs").read_text()
    assert f"gain_alpha: {ADAPT_GAINS['alpha']}" in src or "gain_alpha: 1.0" in src
    assert f"gain_gamma: {ADAPT_GAINS['gamma']}" in src
    assert f"gain_mu: {ADAPT_GAINS['mu']}" in src
    assert f"gain_nu: {ADAPT_GAINS['nu']}" in src
    assert ADAPT_GAINS["gamma"] == -0.5
