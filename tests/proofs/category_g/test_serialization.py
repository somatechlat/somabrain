"""Category G: Serialization Alignment Tests.

**Feature: deep-memory-integration**
**Validates: Requirements G1.1, G1.2, G1.3, G1.4, G1.5**

Tests that verify serialization utilities correctly convert Python types
to JSON-compatible formats for SFM communication.

Test Coverage:
- Task 9.6: Payload with tuple, ndarray, epoch → serialized correctly for SFM
"""

from __future__ import annotations

import datetime
import time

import pytest


# ---------------------------------------------------------------------------
# Test Class: Serialization for SFM (G1)
# ---------------------------------------------------------------------------


@pytest.mark.memory_proof
class TestSerializationForSFM:
    """Tests for serialize_for_sfm utility.

    **Feature: deep-memory-integration, Category G1: Serialization Alignment**
    **Validates: Requirements G1.1, G1.2, G1.3, G1.4, G1.5**
    """

    def test_tuple_converted_to_list(self) -> None:
        """Task 9.6 (part 1): Tuples are converted to lists.

        **Feature: deep-memory-integration, Property G1.1**
        **Validates: Requirements G1.1**

        WHEN payload contains tuples THEN they SHALL be converted to lists
        because JSON does not support tuple type.
        """
        from somabrain.memory.serialization import serialize_for_sfm

        payload = {
            "coordinate": (1.0, 2.0, 3.0),
            "nested": {"inner_tuple": (4, 5, 6)},
            "list_of_tuples": [(1, 2), (3, 4)],
        }

        result = serialize_for_sfm(payload)

        # Verify tuples converted to lists
        assert result["coordinate"] == [1.0, 2.0, 3.0]
        assert isinstance(result["coordinate"], list)

        assert result["nested"]["inner_tuple"] == [4, 5, 6]
        assert isinstance(result["nested"]["inner_tuple"], list)

        # Nested tuples in list also converted
        assert result["list_of_tuples"] == [[1, 2], [3, 4]]
        assert all(isinstance(item, list) for item in result["list_of_tuples"])

    def test_ndarray_converted_to_list(self) -> None:
        """Task 9.6 (part 2): NumPy arrays are converted to lists.

        **Feature: deep-memory-integration, Property G1.2**
        **Validates: Requirements G1.2**

        WHEN payload contains numpy arrays THEN they SHALL be converted
        to Python lists for JSON serialization.
        """
        from somabrain.memory.serialization import serialize_for_sfm

        try:
            import numpy as np

            payload = {
                "vector": np.array([0.1, 0.2, 0.3]),
                "matrix": np.array([[1, 2], [3, 4]]),
                "scalar_int": np.int64(42),
                "scalar_float": np.float32(3.14),
            }

            result = serialize_for_sfm(payload)

            # Verify arrays converted to lists
            assert result["vector"] == [0.1, 0.2, 0.3]
            assert isinstance(result["vector"], list)

            assert result["matrix"] == [[1, 2], [3, 4]]
            assert isinstance(result["matrix"], list)

            # Verify numpy scalars converted to Python types
            assert result["scalar_int"] == 42
            assert isinstance(result["scalar_int"], int)

            assert abs(result["scalar_float"] - 3.14) < 0.01
            assert isinstance(result["scalar_float"], float)

        except ImportError:
            pytest.skip("NumPy not available")

    def test_epoch_timestamp_converted_to_iso8601(self) -> None:
        """Task 9.6 (part 3): Epoch timestamps are converted to ISO 8601.

        **Feature: deep-memory-integration, Property G1.3**
        **Validates: Requirements G1.3**

        WHEN payload contains epoch timestamps (float > 1e9)
        THEN they SHALL be converted to ISO 8601 strings.
        """
        from somabrain.memory.serialization import serialize_for_sfm

        # Use a known timestamp: 2024-01-15 12:00:00 UTC
        epoch_ts = 1705320000.0

        payload = {
            "created_at": epoch_ts,
            "updated_at": epoch_ts + 3600,  # 1 hour later
            "regular_float": 42.5,  # Should NOT be converted (too small)
            "regular_int": 100,  # Should NOT be converted
        }

        result = serialize_for_sfm(payload)

        # Verify epoch timestamps converted to ISO 8601
        assert isinstance(result["created_at"], str)
        assert "2024-01-15" in result["created_at"]
        assert "T" in result["created_at"]  # ISO 8601 format

        assert isinstance(result["updated_at"], str)
        assert "T" in result["updated_at"]

        # Regular numbers should NOT be converted
        assert result["regular_float"] == 42.5
        assert isinstance(result["regular_float"], (int, float))

        assert result["regular_int"] == 100
        assert isinstance(result["regular_int"], int)

    def test_datetime_converted_to_iso8601(self) -> None:
        """Datetime objects are converted to ISO 8601 strings.

        **Feature: deep-memory-integration**
        **Validates: Requirements G1.3**
        """
        from somabrain.memory.serialization import serialize_for_sfm

        dt = datetime.datetime(2024, 1, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        date_only = datetime.date(2024, 1, 15)

        payload = {
            "datetime_field": dt,
            "date_field": date_only,
        }

        result = serialize_for_sfm(payload)

        # Verify datetime converted to ISO 8601
        assert isinstance(result["datetime_field"], str)
        assert "2024-01-15" in result["datetime_field"]
        assert "T" in result["datetime_field"]

        # Verify date converted to ISO 8601
        assert isinstance(result["date_field"], str)
        assert result["date_field"] == "2024-01-15"

    def test_nested_structures_handled_recursively(self) -> None:
        """Nested structures are handled recursively.

        **Feature: deep-memory-integration, Property G1.4**
        **Validates: Requirements G1.4**
        """
        from somabrain.memory.serialization import serialize_for_sfm

        payload = {
            "level1": {
                "level2": {
                    "tuple_value": (1, 2, 3),
                    "level3": {
                        "deep_tuple": (4, 5),
                    },
                },
            },
            "list_with_dicts": [
                {"tuple_in_list": (6, 7)},
                {"another": (8, 9)},
            ],
        }

        result = serialize_for_sfm(payload)

        # Verify deep nesting handled
        assert result["level1"]["level2"]["tuple_value"] == [1, 2, 3]
        assert result["level1"]["level2"]["level3"]["deep_tuple"] == [4, 5]

        # Verify list of dicts handled
        assert result["list_with_dicts"][0]["tuple_in_list"] == [6, 7]
        assert result["list_with_dicts"][1]["another"] == [8, 9]

    def test_none_values_preserved(self) -> None:
        """None values are preserved.

        **Feature: deep-memory-integration, Property G1.5**
        **Validates: Requirements G1.5**
        """
        from somabrain.memory.serialization import serialize_for_sfm

        payload = {
            "null_field": None,
            "nested": {"also_null": None},
        }

        result = serialize_for_sfm(payload)

        assert result["null_field"] is None
        assert result["nested"]["also_null"] is None

    def test_bytes_decoded_to_string(self) -> None:
        """Bytes are decoded to UTF-8 strings.

        **Feature: deep-memory-integration**
        **Validates: Requirements G1.5**
        """
        from somabrain.memory.serialization import serialize_for_sfm

        payload = {
            "utf8_bytes": b"hello world",
            "binary_bytes": bytes([0xDE, 0xAD, 0xBE, 0xEF]),
        }

        result = serialize_for_sfm(payload)

        # UTF-8 bytes decoded to string
        assert result["utf8_bytes"] == "hello world"

        # Non-UTF-8 bytes converted to hex
        assert result["binary_bytes"] == "deadbeef"

    def test_empty_payload_returns_empty_dict(self) -> None:
        """Empty or None payload returns empty dict.

        **Feature: deep-memory-integration**
        **Validates: Requirements G1.5**
        """
        from somabrain.memory.serialization import serialize_for_sfm

        assert serialize_for_sfm({}) == {}
        assert serialize_for_sfm(None) == {}

    def test_full_payload_serialization(self) -> None:
        """Task 9.6: Complete payload with tuple, ndarray, epoch serialized correctly.

        **Feature: deep-memory-integration**
        **Validates: Requirements G1.1, G1.2, G1.3, G1.4, G1.5**

        This is the comprehensive test for Task 9.6 that verifies
        all serialization requirements together.
        """
        from somabrain.memory.serialization import serialize_for_sfm

        try:
            import numpy as np

            has_numpy = True
        except ImportError:
            has_numpy = False

        # Build payload with all types
        epoch_ts = time.time()
        payload = {
            "coordinate": (1.0, 2.0, 3.0),  # G1.1: tuple
            "created_at": epoch_ts,  # G1.3: epoch timestamp
            "content": "test memory",
            "metadata": {
                "tags": ("tag1", "tag2"),  # G1.1: nested tuple
                "timestamp": epoch_ts,  # G1.3: nested epoch
            },
            "none_field": None,  # G1.5: None preserved
        }

        if has_numpy:
            payload["vector"] = np.array([0.1, 0.2, 0.3])  # G1.2: ndarray
            payload["importance"] = np.float32(0.85)  # G1.2: numpy scalar

        result = serialize_for_sfm(payload)

        # Verify all conversions
        # G1.1: Tuples to lists
        assert isinstance(result["coordinate"], list)
        assert result["coordinate"] == [1.0, 2.0, 3.0]
        assert isinstance(result["metadata"]["tags"], list)
        assert result["metadata"]["tags"] == ["tag1", "tag2"]

        # G1.3: Epoch to ISO 8601
        assert isinstance(result["created_at"], str)
        assert "T" in result["created_at"]
        assert isinstance(result["metadata"]["timestamp"], str)

        # G1.5: None preserved
        assert result["none_field"] is None

        # G1.2: NumPy arrays (if available)
        if has_numpy:
            assert isinstance(result["vector"], list)
            assert result["vector"] == [0.1, 0.2, 0.3]
            assert isinstance(result["importance"], float)

        # Verify result is JSON-serializable
        import json

        json_str = json.dumps(result)
        assert json_str is not None
        assert len(json_str) > 0


# ---------------------------------------------------------------------------
# Test Class: Deserialization from SFM (G1 - Inverse)
# ---------------------------------------------------------------------------


@pytest.mark.memory_proof
class TestDeserializationFromSFM:
    """Tests for deserialize_from_sfm utility.

    **Feature: deep-memory-integration**
    **Validates: Requirements G1.1-G1.5 (inverse operations)**
    """

    def test_iso8601_converted_to_datetime(self) -> None:
        """ISO 8601 strings are converted back to datetime objects.

        **Feature: deep-memory-integration**
        **Validates: Requirements G1.3 (inverse)**
        """
        from somabrain.memory.serialization import deserialize_from_sfm

        payload = {
            "created_at": "2024-01-15T12:00:00+00:00",
            "regular_string": "not a datetime",
        }

        result = deserialize_from_sfm(payload)

        # ISO 8601 converted to datetime
        assert isinstance(result["created_at"], datetime.datetime)
        assert result["created_at"].year == 2024
        assert result["created_at"].month == 1
        assert result["created_at"].day == 15

        # Regular strings unchanged
        assert result["regular_string"] == "not a datetime"

    def test_nested_deserialization(self) -> None:
        """Nested structures are deserialized recursively.

        **Feature: deep-memory-integration**
        **Validates: Requirements G1.4 (inverse)**
        """
        from somabrain.memory.serialization import deserialize_from_sfm

        payload = {
            "metadata": {
                "timestamp": "2024-01-15T12:00:00+00:00",
            },
            "list_of_items": [
                {"created": "2024-01-15T13:00:00+00:00"},
            ],
        }

        result = deserialize_from_sfm(payload)

        assert isinstance(result["metadata"]["timestamp"], datetime.datetime)
        assert isinstance(result["list_of_items"][0]["created"], datetime.datetime)


# ---------------------------------------------------------------------------
# Test Class: Coordinate Serialization (G1 - Helpers)
# ---------------------------------------------------------------------------


@pytest.mark.memory_proof
class TestCoordinateSerialization:
    """Tests for coordinate serialization helpers.

    **Feature: deep-memory-integration**
    **Validates: Requirements G1.1**
    """

    def test_serialize_coordinate(self) -> None:
        """Coordinate tuple serialized to comma-separated string.

        **Feature: deep-memory-integration**
        **Validates: Requirements G1.1**
        """
        from somabrain.memory.serialization import serialize_coordinate

        coord = (1.0, 2.5, 3.14159)
        result = serialize_coordinate(coord)

        assert result == "1.0,2.5,3.14159"
        assert isinstance(result, str)

    def test_deserialize_coordinate(self) -> None:
        """Comma-separated string deserialized to coordinate tuple.

        **Feature: deep-memory-integration**
        **Validates: Requirements G1.1 (inverse)**
        """
        from somabrain.memory.serialization import deserialize_coordinate

        coord_str = "1.0,2.5,3.14159"
        result = deserialize_coordinate(coord_str)

        assert result == (1.0, 2.5, 3.14159)
        assert isinstance(result, tuple)

    def test_coordinate_roundtrip(self) -> None:
        """Coordinate survives serialize/deserialize roundtrip.

        **Feature: deep-memory-integration**
        **Validates: Requirements G1.1**
        """
        from somabrain.memory.serialization import (
            serialize_coordinate,
            deserialize_coordinate,
        )

        original = (1.5, 2.5, 3.5)
        serialized = serialize_coordinate(original)
        deserialized = deserialize_coordinate(serialized)

        assert deserialized == original