"""W5b acceptance: one recency kernel, one lexical bonus, FD-off ceiling 1.0.

Every assertion imports the production symbol. No local formula copies.
"""

from __future__ import annotations

import math

import pytest

pytestmark = pytest.mark.no_django

import numpy as np

from somabrain.admin.cognitive.personality import PersonalityStore
from somabrain.admin.core.learning.scoring import UnifiedScorer
from somabrain.math.graph_heat import SPECTRAL_INTERVAL_EPSILON, expand_spectral_interval
from somabrain.math.recency import (
    recency_features,
    stretched_exponential_recency,
)
from somabrain.memory.client.ranking import lexical_bonus

# One test vector for the single recency kernel (DEBT-020).
_SCALE = 60.0
_SHARPNESS = 1.2
_FLOOR = 0.05
_CAP = 1000.0
_AGE = 60.0
_EXPECTED = math.exp(-((_AGE / _SCALE) ** _SHARPNESS))


class TestOneRecencyKernel:
    """Every live call site must produce the same recency for one vector."""

    def test_kernel_matches_closed_form(self) -> None:
        got = stretched_exponential_recency(
            _AGE, scale=_SCALE, sharpness=_SHARPNESS, floor=_FLOOR
        )
        assert abs(got - _EXPECTED) < 1e-12

    def test_features_boost_matches_kernel(self) -> None:
        steps, boost = recency_features(
            _AGE, scale=_SCALE, sharpness=_SHARPNESS, floor=_FLOOR, cap=_CAP
        )
        assert abs(boost - _EXPECTED) < 1e-12
        assert steps == pytest.approx(
            math.log1p(_AGE / _SCALE) * _SHARPNESS, rel=1e-12
        )

    def test_age_zero_is_one(self) -> None:
        assert (
            stretched_exponential_recency(
                0.0, scale=_SCALE, sharpness=_SHARPNESS, floor=_FLOOR
            )
            == 1.0
        )

    def test_floor_holds(self) -> None:
        got = stretched_exponential_recency(
            1e9, scale=_SCALE, sharpness=_SHARPNESS, floor=_FLOOR
        )
        assert got == pytest.approx(_FLOOR)

    def test_unified_scorer_uses_same_kernel(self) -> None:
        scorer = UnifiedScorer(
            w_cosine=0.6,
            w_fd=0.25,
            w_recency=0.15,
            weight_min=0.0,
            weight_max=1.0,
            recency_scale=_SCALE,
            recency_sharpness=_SHARPNESS,
            recency_floor=_FLOOR,
            fd_backend=None,
        )
        got = scorer._recency_component(_AGE)
        assert abs(got - _EXPECTED) < 1e-12


class TestOneLexicalBonus:
    """DEBT-021: a single lexical_bonus implementation."""

    def test_three_token_matches_bonus(self) -> None:
        payload = {
            "task": "alpha beta gamma",
            "text": "alpha beta gamma",
        }
        query = "alpha beta gamma"
        bonus = lexical_bonus(payload, query)
        # exact field match -> 1.5, plus token term min(0.25*3, 1.0) = 0.75
        assert bonus == pytest.approx(1.5 + 0.75)

    def test_token_only_bonus(self) -> None:
        payload = {"text": "alpha zzz qqq"}
        query = "alpha beta gamma"
        # 1 token match (beta/gamma absent) -> 0.25
        assert lexical_bonus(payload, query) == pytest.approx(0.25)

    def test_hit_processing_defines_no_second_formula(self) -> None:
        import somabrain.memory.hit_processing as hp

        assert not hasattr(hp, "lexical_bonus")
        src = open(hp.__file__, encoding="utf-8").read()
        assert "0.3 + 0.1" not in src
        assert "token_matches" not in src


class TestFdOffCeiling:
    """DEBT-022/023: constructor weights honored; FD-off max score is 1.0."""

    def _scorer(self, w_cos, w_fd, w_rec, fd=None) -> UnifiedScorer:
        return UnifiedScorer(
            w_cosine=w_cos,
            w_fd=w_fd,
            w_recency=w_rec,
            weight_min=0.0,
            weight_max=1.0,
            recency_scale=1.0,
            fd_backend=fd,
        )

    def test_constructor_weights_are_honored(self) -> None:
        scorer = self._scorer(0.9, 0.0, 0.1)
        assert scorer._weights.w_cosine == pytest.approx(0.9)
        assert scorer._weights.w_fd == pytest.approx(0.0)
        assert scorer._weights.w_recency == pytest.approx(0.1)

    def test_fd_off_perfect_match_is_one(self) -> None:
        scorer = self._scorer(0.6, 0.25, 0.15)
        v = np.ones(8)
        score = scorer.score(v, v, age_seconds=0.0)
        assert score == pytest.approx(1.0, abs=1e-9)

    def test_fd_off_custom_weights_reach_one(self) -> None:
        scorer = self._scorer(0.9, 0.0, 0.1)
        v = np.ones(8)
        assert scorer.score(v, v, age_seconds=0.0) == pytest.approx(1.0, abs=1e-9)

    def test_fd_off_without_age_also_reaches_one(self) -> None:
        scorer = self._scorer(0.6, 0.25, 0.15)
        v = np.ones(8)
        assert scorer.score(v, v) == pytest.approx(1.0, abs=1e-9)


class TestPersonalityGet:
    """DEBT-026: PersonalityStore.get must not raise NameError."""

    def test_get_returns_stable_state(self) -> None:
        store = PersonalityStore()
        first = store.get("acme")
        second = store.get("acme")
        assert first is second

    def test_get_requires_tenant(self) -> None:
        store = PersonalityStore()
        with pytest.raises(ValueError):
            store.get("")

    def test_get_is_isolated_per_tenant(self) -> None:
        store = PersonalityStore()
        a = store.get("a")
        b = store.get("b")
        assert a is not b


class TestChebyshevBoundsExpanded:
    """DEBT-017: Lanczos Ritz bounds expand by exactly ε."""

    def test_expand_is_a_minus_eps_b_plus_eps(self) -> None:
        a, b = 1.0, 2.0
        ea, eb = expand_spectral_interval(a, b)
        assert ea == pytest.approx(a - SPECTRAL_INTERVAL_EPSILON)
        assert eb == pytest.approx(b + SPECTRAL_INTERVAL_EPSILON)

    def test_lower_bound_not_negative(self) -> None:
        ea, _ = expand_spectral_interval(0.01, 0.5)
        assert ea >= 0.0

    def test_bounds_widen(self) -> None:
        a, b = 0.5, 1.5
        ea, eb = expand_spectral_interval(a, b)
        assert ea < a and eb > b
