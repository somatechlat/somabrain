"""Property-based tests for Multi-Tenancy & Serialization.

**Feature: production-hardening**
**Properties: 17-19 (Tenant Isolation, Serialization Round-Trip, Timestamp Normalization)**
**Validates: Requirements 8.5, 10.2, 11.1, 11.2, 11.3, 11.4**

These tests verify tenant isolation guarantees and serialization invariants
for the SomaBrain system. All tests use real implementations.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import asdict
from typing import Any, Dict, Optional, Tuple

import pytest
from hypothesis import given, settings as hyp_settings, strategies as st, assume


# ---------------------------------------------------------------------------
# Strategies for generating test data
# ---------------------------------------------------------------------------

# Tenant ID strategy
tenant_id_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_-"),
    min_size=1,
    max_size=32,
)

# Neuromodulator value strategies (within valid ranges)
dopamine_strategy = st.floats(
    min_value=0.2, max_value=0.8, allow_nan=False, allow_infinity=False
)
serotonin_strategy = st.floats(
    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
)
noradrenaline_strategy = st.floats(
    min_value=0.0, max_value=0.1, allow_nan=False, allow_infinity=False
)
acetylcholine_strategy = st.floats(
    min_value=0.0, max_value=0.1, allow_nan=False, allow_infinity=False
)

# Timestamp strategies
epoch_timestamp_strategy = st.floats(
    min_value=0.0,
    max_value=2000000000.0,  # ~2033
    allow_nan=False,
    allow_infinity=False,
)

# Score strategy for RecallHit
score_strategy = st.floats(
    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
)

# Coordinate strategy
coordinate_strategy = st.tuples(
    st.floats(
        min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False
    ),
    st.floats(
        min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False
    ),
    st.floats(
        min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False
    ),
)


# ---------------------------------------------------------------------------
# Import real implementations
# ---------------------------------------------------------------------------

from somabrain.admin.brain.neuromodulators import NeuromodState, PerTenantNeuromodulators
from somabrain.datetime_utils import coerce_to_epoch_seconds
from somabrain.memory.client import RecallHit


class TestTenantIsolation:
    """Property 17: Tenant Isolation.

    For any two distinct tenant IDs, state modifications for one tenant
    SHALL NOT affect the state of another tenant.

    **Feature: production-hardening, Property 17: Tenant Isolation**
    **Validates: Requirements 10.2**
    """

    @given(
        tenant_a=tenant_id_strategy,
        tenant_b=tenant_id_strategy,
        dopamine_a=dopamine_strategy,
        dopamine_b=dopamine_strategy,
        serotonin_a=serotonin_strategy,
        serotonin_b=serotonin_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_tenant_state_isolation(
        self,
        tenant_a: str,
        tenant_b: str,
        dopamine_a: float,
        dopamine_b: float,
        serotonin_a: float,
        serotonin_b: float,
    ) -> None:
        """Verify tenant states are isolated from each other."""
        assume(tenant_a != tenant_b)

        # Create fresh per-tenant store
        store = PerTenantNeuromodulators()

        # Set state for tenant A
        state_a = NeuromodState(
            dopamine=dopamine_a,
            serotonin=serotonin_a,
            noradrenaline=0.05,
            acetylcholine=0.05,
        )
        store.set_state(tenant_a, state_a)

        # Set different state for tenant B
        state_b = NeuromodState(
            dopamine=dopamine_b,
            serotonin=serotonin_b,
            noradrenaline=0.02,
            acetylcholine=0.02,
        )
        store.set_state(tenant_b, state_b)

        # Verify tenant A state unchanged
        retrieved_a = store.get_state(tenant_a)
        assert (
            abs(retrieved_a.dopamine - dopamine_a) < 1e-10
        ), f"Tenant A dopamine changed: {retrieved_a.dopamine} != {dopamine_a}"
        assert (
            abs(retrieved_a.serotonin - serotonin_a) < 1e-10
        ), f"Tenant A serotonin changed: {retrieved_a.serotonin} != {serotonin_a}"

        # Verify tenant B state is different
        retrieved_b = store.get_state(tenant_b)
        assert (
            abs(retrieved_b.dopamine - dopamine_b) < 1e-10
        ), f"Tenant B dopamine wrong: {retrieved_b.dopamine} != {dopamine_b}"
        assert (
            abs(retrieved_b.serotonin - serotonin_b) < 1e-10
        ), f"Tenant B serotonin wrong: {retrieved_b.serotonin} != {serotonin_b}"

    @given(
        tenant_id=tenant_id_strategy,
        dopamine=dopamine_strategy,
        serotonin=serotonin_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_tenant_state_persistence(
        self,
        tenant_id: str,
        dopamine: float,
        serotonin: float,
    ) -> None:
        """Verify tenant state persists across get operations."""
        store = PerTenantNeuromodulators()

        # Set state
        state = NeuromodState(
            dopamine=dopamine,
            serotonin=serotonin,
            noradrenaline=0.05,
            acetylcholine=0.05,
        )
        store.set_state(tenant_id, state)

        # Multiple gets should return same state
        for _ in range(3):
            retrieved = store.get_state(tenant_id)
            assert abs(retrieved.dopamine - dopamine) < 1e-10
            assert abs(retrieved.serotonin - serotonin) < 1e-10

    @given(
        tenant_id=tenant_id_strategy,
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_unknown_tenant_gets_global_default(self, tenant_id: str) -> None:
        """Verify unknown tenant gets global default state."""
        store = PerTenantNeuromodulators()

        # Get state for unknown tenant (should return global default)
        state = store.get_state(tenant_id)

        # Should be a valid NeuromodState
        assert isinstance(state, NeuromodState)
        assert 0.0 <= state.dopamine <= 1.0
        assert 0.0 <= state.serotonin <= 1.0

    @given(
        tenant_ids=st.lists(tenant_id_strategy, min_size=2, max_size=10, unique=True),
    )
    @hyp_settings(max_examples=30, deadline=10000)
    def test_multiple_tenants_isolated(self, tenant_ids: list) -> None:
        """Verify multiple tenants maintain isolated states."""
        store = PerTenantNeuromodulators()

        # Set unique states for each tenant
        states = {}
        for i, tid in enumerate(tenant_ids):
            dopamine = 0.2 + (i * 0.05) % 0.6  # Vary dopamine
            serotonin = 0.1 + (i * 0.1) % 0.9  # Vary serotonin
            state = NeuromodState(
                dopamine=dopamine,
                serotonin=serotonin,
                noradrenaline=0.01 * i,
                acetylcholine=0.01 * i,
            )
            store.set_state(tid, state)
            states[tid] = (dopamine, serotonin)

        # Verify all states are correct
        for tid, (expected_da, expected_ser) in states.items():
            retrieved = store.get_state(tid)
            assert (
                abs(retrieved.dopamine - expected_da) < 1e-10
            ), f"Tenant {tid} dopamine mismatch"
            assert (
                abs(retrieved.serotonin - expected_ser) < 1e-10
            ), f"Tenant {tid} serotonin mismatch"


class TestSerializationRoundTrip:
    """Property 18: Serialization Round-Trip.

    For any valid state object, serializing to JSON and deserializing back
    SHALL produce an equivalent object.

    **Feature: production-hardening, Property 18: Serialization Round-Trip**
    **Validates: Requirements 11.1, 11.2, 11.3, 11.4**
    """

    @given(
        dopamine=dopamine_strategy,
        serotonin=serotonin_strategy,
        noradrenaline=noradrenaline_strategy,
        acetylcholine=acetylcholine_strategy,
        timestamp=epoch_timestamp_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_neuromod_state_round_trip(
        self,
        dopamine: float,
        serotonin: float,
        noradrenaline: float,
        acetylcholine: float,
        timestamp: float,
    ) -> None:
        """Verify NeuromodState survives JSON round-trip."""
        original = NeuromodState(
            dopamine=dopamine,
            serotonin=serotonin,
            noradrenaline=noradrenaline,
            acetylcholine=acetylcholine,
            timestamp=timestamp,
        )

        # Serialize to dict then JSON
        as_dict = asdict(original)
        json_str = json.dumps(as_dict)

        # Deserialize
        loaded_dict = json.loads(json_str)
        restored = NeuromodState(**loaded_dict)

        # Verify equality
        assert abs(restored.dopamine - original.dopamine) < 1e-10
        assert abs(restored.serotonin - original.serotonin) < 1e-10
        assert abs(restored.noradrenaline - original.noradrenaline) < 1e-10
        assert abs(restored.acetylcholine - original.acetylcholine) < 1e-10
        assert abs(restored.timestamp - original.timestamp) < 1e-6

    @given(
        score=st.one_of(score_strategy, st.none()),
        coordinate=st.one_of(coordinate_strategy, st.none()),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_recall_hit_round_trip(
        self,
        score: Optional[float],
        coordinate: Optional[Tuple[float, float, float]],
    ) -> None:
        """Verify RecallHit survives JSON round-trip."""
        payload = {"task": "test", "content": "example data", "importance": 5}

        original = RecallHit(
            payload=payload,
            score=score,
            coordinate=coordinate,
            raw={"original": True},
        )

        # Serialize to dict then JSON
        as_dict = asdict(original)
        json_str = json.dumps(as_dict)

        # Deserialize
        loaded_dict = json.loads(json_str)
        restored = RecallHit(**loaded_dict)

        # Verify equality
        assert restored.payload == original.payload

        if original.score is not None:
            assert restored.score is not None
            assert abs(restored.score - original.score) < 1e-10
        else:
            assert restored.score is None

        if original.coordinate is not None:
            assert restored.coordinate is not None
            # JSON converts tuple to list, so compare as tuples
            restored_coord = tuple(restored.coordinate)
            for i in range(3):
                assert abs(restored_coord[i] - original.coordinate[i]) < 1e-10
        else:
            assert restored.coordinate is None

    @given(
        payload=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(min_value=-1000, max_value=1000),
                st.floats(
                    min_value=-1000,
                    max_value=1000,
                    allow_nan=False,
                    allow_infinity=False,
                ),
                st.booleans(),
            ),
            min_size=1,
            max_size=10,
        ),
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_arbitrary_payload_round_trip(self, payload: Dict[str, Any]) -> None:
        """Verify arbitrary payloads survive JSON round-trip."""
        original = RecallHit(payload=payload, score=0.5, coordinate=None, raw=None)

        as_dict = asdict(original)
        json_str = json.dumps(as_dict)
        loaded_dict = json.loads(json_str)
        restored = RecallHit(**loaded_dict)

        assert restored.payload == original.payload

    @given(
        dopamine=dopamine_strategy,
        serotonin=serotonin_strategy,
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_neuromod_state_json_keys_preserved(
        self, dopamine: float, serotonin: float
    ) -> None:
        """Verify all NeuromodState keys are preserved in JSON."""
        original = NeuromodState(
            dopamine=dopamine,
            serotonin=serotonin,
            noradrenaline=0.05,
            acetylcholine=0.05,
        )

        as_dict = asdict(original)

        # All expected keys should be present
        expected_keys = {
            "dopamine",
            "serotonin",
            "noradrenaline",
            "acetylcholine",
            "timestamp",
        }
        assert set(as_dict.keys()) == expected_keys


class TestTimestampNormalization:
    """Property 19: Timestamp Normalization.

    For any valid timestamp input (ISO-8601 string, numeric string, float, int,
    or datetime), coerce_to_epoch_seconds SHALL return a valid Unix epoch float.

    **Feature: production-hardening, Property 19: Timestamp Normalization**
    **Validates: Requirements 8.5**
    """

    @given(
        timestamp=epoch_timestamp_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_float_timestamp_passthrough(self, timestamp: float) -> None:
        """Verify float timestamps pass through unchanged."""
        result = coerce_to_epoch_seconds(timestamp)
        assert (
            abs(result - timestamp) < 1e-10
        ), f"Float timestamp changed: {result} != {timestamp}"

    @given(
        timestamp=st.integers(min_value=0, max_value=2000000000),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_int_timestamp_converted(self, timestamp: int) -> None:
        """Verify int timestamps are converted to float."""
        result = coerce_to_epoch_seconds(timestamp)
        assert isinstance(result, float)
        assert abs(result - float(timestamp)) < 1e-10

    @given(
        timestamp=epoch_timestamp_strategy,
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_numeric_string_parsed(self, timestamp: float) -> None:
        """Verify numeric string timestamps are parsed correctly."""
        timestamp_str = str(timestamp)
        result = coerce_to_epoch_seconds(timestamp_str)
        assert (
            abs(result - timestamp) < 1e-6
        ), f"Numeric string parsing failed: {result} != {timestamp}"

    @given(
        year=st.integers(min_value=1970, max_value=2030),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=28),  # Safe for all months
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59),
        second=st.integers(min_value=0, max_value=59),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_iso8601_string_parsed(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int,
        second: int,
    ) -> None:
        """Verify ISO-8601 strings are parsed correctly."""
        # Create datetime and ISO string
        dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        iso_str = dt.isoformat()

        result = coerce_to_epoch_seconds(iso_str)
        expected = dt.timestamp()

        assert (
            abs(result - expected) < 1.0
        ), f"ISO-8601 parsing failed: {result} != {expected} for {iso_str}"

    @given(
        year=st.integers(min_value=1970, max_value=2030),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=28),
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59),
        second=st.integers(min_value=0, max_value=59),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_iso8601_z_suffix_parsed(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int,
        second: int,
    ) -> None:
        """Verify ISO-8601 strings with Z suffix are parsed correctly."""
        dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        # Use Z suffix format
        iso_str = (
            f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"
        )

        result = coerce_to_epoch_seconds(iso_str)
        expected = dt.timestamp()

        assert (
            abs(result - expected) < 1.0
        ), f"ISO-8601 Z suffix parsing failed: {result} != {expected} for {iso_str}"

    @given(
        year=st.integers(min_value=1970, max_value=2030),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=28),
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59),
        second=st.integers(min_value=0, max_value=59),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_datetime_object_converted(
        self,
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int,
        second: int,
    ) -> None:
        """Verify datetime objects are converted correctly."""
        dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)

        result = coerce_to_epoch_seconds(dt)
        expected = dt.timestamp()

        assert (
            abs(result - expected) < 1e-6
        ), f"Datetime conversion failed: {result} != {expected}"

    @given(
        year=st.integers(min_value=1970, max_value=2030),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=28),
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_naive_datetime_assumes_utc(self, year: int, month: int, day: int) -> None:
        """Verify naive datetime objects are treated as UTC."""
        dt_naive = datetime(year, month, day, 12, 0, 0)  # Noon, no timezone
        dt_utc = datetime(year, month, day, 12, 0, 0, tzinfo=timezone.utc)

        result = coerce_to_epoch_seconds(dt_naive)
        expected = dt_utc.timestamp()

        assert (
            abs(result - expected) < 1e-6
        ), f"Naive datetime not treated as UTC: {result} != {expected}"

    def test_invalid_timestamp_raises(self) -> None:
        """Verify invalid timestamps raise ValueError."""
        invalid_inputs = [
            None,
            "",
            "   ",
            "not-a-timestamp",
            "2024-13-01",  # Invalid month
            [],
            {},
        ]

        for invalid in invalid_inputs:
            with pytest.raises(ValueError):
                coerce_to_epoch_seconds(invalid)

    @given(
        timestamp=epoch_timestamp_strategy,
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_round_trip_float_to_iso_to_float(self, timestamp: float) -> None:
        """Verify float → ISO → float round-trip preserves value."""
        # Convert float to datetime to ISO string
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        iso_str = dt.isoformat()

        # Convert back
        result = coerce_to_epoch_seconds(iso_str)

        # Should be close (microsecond precision loss acceptable)
        assert (
            abs(result - timestamp) < 1.0
        ), f"Round-trip failed: {result} != {timestamp}"
