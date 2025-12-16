"""Property-based tests for Settings parsing.

**Feature: production-hardening**
**Properties: 9 (Comment Stripping), 10 (Boolean Parsing)**
**Validates: Requirements 3.2, 3.5**
"""

from __future__ import annotations

import os
from unittest import mock

import pytest
from hypothesis import given, settings as hyp_settings, strategies as st

from common.config.settings.base import _bool_env, _float_env, _int_env, _str_env


class TestSettingsCommentStripping:
    """Property 9: Settings Comment Stripping.

    For any environment variable value containing '#', the Settings parser
    SHALL strip the comment portion before parsing.
    **Validates: Requirements 3.2**
    """

    @given(
        value=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_-"),
            min_size=1,
            max_size=50,
        ),
        comment=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789 "),
            min_size=0,
            max_size=20,
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_str_env_strips_comments(self, value: str, comment: str) -> None:
        """String env values with comments are stripped correctly."""
        # Skip if value contains # (would be ambiguous) or is whitespace-only
        if "#" in value or not value.strip():
            return

        env_value = f"{value} # {comment}" if comment else value
        with mock.patch.dict(os.environ, {"TEST_VAR": env_value}):
            result = _str_env("TEST_VAR")
            assert (
                result == value.strip()
            ), f"Expected '{value.strip()}', got '{result}'"

    @given(
        value=st.integers(min_value=-1000000, max_value=1000000),
        comment=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789 "),
            min_size=0,
            max_size=20,
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_int_env_strips_comments(self, value: int, comment: str) -> None:
        """Integer env values with comments are stripped correctly."""
        env_value = f"{value} # {comment}" if comment else str(value)
        with mock.patch.dict(os.environ, {"TEST_INT": env_value}):
            result = _int_env("TEST_INT", 0)
            assert result == value, f"Expected {value}, got {result}"

    @given(
        value=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        comment=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789 "),
            min_size=0,
            max_size=20,
        ),
    )
    @hyp_settings(max_examples=100, deadline=5000)
    def test_float_env_strips_comments(self, value: float, comment: str) -> None:
        """Float env values with comments are stripped correctly."""
        env_value = f"{value} # {comment}" if comment else str(value)
        with mock.patch.dict(os.environ, {"TEST_FLOAT": env_value}):
            result = _float_env("TEST_FLOAT", 0.0)
            # Use relative tolerance for float comparison
            if abs(value) < 1e-9:
                assert abs(result) < 1e-6, f"Expected ~{value}, got {result}"
            else:
                assert (
                    abs(result - value) / abs(value) < 1e-6
                ), f"Expected {value}, got {result}"


class TestSettingsBooleanParsing:
    """Property 10: Settings Boolean Parsing.

    For any boolean setting, the values '1', 'true', 'yes', 'on' (case-insensitive)
    SHALL parse as True, and all other values SHALL parse as False.
    **Validates: Requirements 3.5**
    """

    @pytest.mark.parametrize(
        "truthy_value",
        ["1", "true", "yes", "on", "TRUE", "True", "YES", "Yes", "ON", "On"],
    )
    def test_truthy_values_parse_as_true(self, truthy_value: str) -> None:
        """Known truthy values parse as True."""
        with mock.patch.dict(os.environ, {"TEST_BOOL": truthy_value}):
            result = _bool_env("TEST_BOOL", False)
            assert result is True, f"Expected True for '{truthy_value}', got {result}"

    @pytest.mark.parametrize(
        "falsy_value",
        [
            "0",
            "false",
            "no",
            "off",
            "FALSE",
            "False",
            "NO",
            "No",
            "OFF",
            "Off",
            "",
            "random",
        ],
    )
    def test_falsy_values_parse_as_false(self, falsy_value: str) -> None:
        """Non-truthy values parse as False."""
        with mock.patch.dict(os.environ, {"TEST_BOOL": falsy_value}):
            result = _bool_env("TEST_BOOL", True)  # Default True to verify override
            assert result is False, f"Expected False for '{falsy_value}', got {result}"

    @given(
        case_variant=st.sampled_from(["1", "true", "yes", "on"]),
        upper=st.booleans(),
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_case_insensitive_truthy(self, case_variant: str, upper: bool) -> None:
        """Truthy values are case-insensitive."""
        test_value = case_variant.upper() if upper else case_variant.lower()
        with mock.patch.dict(os.environ, {"TEST_BOOL": test_value}):
            result = _bool_env("TEST_BOOL", False)
            assert result is True, f"Expected True for '{test_value}'"

    def test_missing_env_returns_default(self) -> None:
        """Missing env var returns the default value."""
        # Ensure the var doesn't exist
        env_copy = os.environ.copy()
        if "NONEXISTENT_VAR" in env_copy:
            del env_copy["NONEXISTENT_VAR"]
        with mock.patch.dict(os.environ, env_copy, clear=True):
            assert _bool_env("NONEXISTENT_VAR", True) is True
            assert _bool_env("NONEXISTENT_VAR", False) is False

    @given(
        truthy=st.sampled_from(["1", "true", "yes", "on"]),
        comment=st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789 "),
            min_size=1,
            max_size=20,
        ),
    )
    @hyp_settings(max_examples=50, deadline=5000)
    def test_bool_with_comment_strips_correctly(
        self, truthy: str, comment: str
    ) -> None:
        """Boolean values with comments are stripped before parsing."""
        env_value = f"{truthy} # {comment}"
        with mock.patch.dict(os.environ, {"TEST_BOOL": env_value}):
            result = _bool_env("TEST_BOOL", False)
            assert result is True, f"Expected True for '{env_value}', got {result}"


class TestSettingsDefaultBehavior:
    """Additional property tests for Settings default behavior."""

    def test_str_env_returns_none_for_missing(self) -> None:
        """_str_env returns None when env var is missing and no default."""
        env_copy = os.environ.copy()
        if "NONEXISTENT_VAR" in env_copy:
            del env_copy["NONEXISTENT_VAR"]
        with mock.patch.dict(os.environ, env_copy, clear=True):
            result = _str_env("NONEXISTENT_VAR")
            assert result is None

    def test_str_env_returns_default_for_missing(self) -> None:
        """_str_env returns default when env var is missing."""
        env_copy = os.environ.copy()
        if "NONEXISTENT_VAR" in env_copy:
            del env_copy["NONEXISTENT_VAR"]
        with mock.patch.dict(os.environ, env_copy, clear=True):
            result = _str_env("NONEXISTENT_VAR", "default_value")
            assert result == "default_value"

    def test_int_env_returns_default_for_invalid(self) -> None:
        """_int_env returns default for non-integer values."""
        with mock.patch.dict(os.environ, {"TEST_INT": "not_an_int"}):
            result = _int_env("TEST_INT", 42)
            assert result == 42

    def test_float_env_returns_default_for_invalid(self) -> None:
        """_float_env returns default for non-float values."""
        with mock.patch.dict(os.environ, {"TEST_FLOAT": "not_a_float"}):
            result = _float_env("TEST_FLOAT", 3.14)
            assert result == 3.14
