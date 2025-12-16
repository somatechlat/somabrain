"""Input validation for cognitive processing.

This module provides validation utilities for text, embedding dimensions,
and coordinates to ensure safe cognitive operations.

All validation limits are centralized in Settings for consistent configuration.
"""

from __future__ import annotations

import logging
import re

from common.config.settings import settings

_log = logging.getLogger(__name__)
_cognitive_log = logging.getLogger("somabrain.cognitive")


class CognitiveInputValidator:
    """Advanced input validation for brain-like cognitive processing.

    Validates text, embedding dimensions, and coordinates for safe cognitive operations.
    All limits are configurable via Settings (environment variables).
    """

    # Brain-safe input patterns
    SAFE_TEXT_PATTERN = re.compile(r"^[a-zA-Z0-9\s\.,!?\'\"()/:_@-]+$")

    @property
    def MAX_TEXT_LENGTH(self) -> int:
        """Maximum text length from Settings."""
        return int(settings.validation_max_text_length)

    @property
    def MAX_EMBEDDING_DIM(self) -> int:
        """Maximum embedding dimension from Settings."""
        return int(settings.validation_max_embedding_dim)

    @property
    def MIN_EMBEDDING_DIM(self) -> int:
        """Minimum embedding dimension from Settings."""
        return int(settings.validation_min_embedding_dim)

    @classmethod
    def validate_text_input(cls, text: str, field_name: str = "text") -> str:
        """Validate text input for cognitive processing."""
        if not text:
            raise ValueError(f"{field_name} cannot be empty")

        max_length = int(settings.validation_max_text_length)
        if len(text) > max_length:
            raise ValueError(
                f"{field_name} exceeds maximum length of {max_length}"
            )

        if not cls.SAFE_TEXT_PATTERN.match(text):
            # Log potential security issue
            _cognitive_log.warning(
                "Potentially unsafe input detected in %s: %s...",
                field_name,
                text[:100],
            )
            raise ValueError(f"{field_name} contains unsafe characters")

        return text.strip()

    @classmethod
    def validate_embedding_dim(cls, dim: int) -> int:
        """Validate embedding dimensions for brain safety."""
        min_dim = int(settings.validation_min_embedding_dim)
        max_dim = int(settings.validation_max_embedding_dim)

        if not isinstance(dim, int) or dim < min_dim:
            raise ValueError(
                f"Embedding dimension must be at least {min_dim}"
            )

        if dim > max_dim:
            raise ValueError(
                f"Embedding dimension cannot exceed {max_dim}"
            )

        return dim

    @staticmethod
    def validate_coordinates(coords: tuple) -> tuple:
        """Validate coordinate tuples for brain processing."""
        if not isinstance(coords, (list, tuple)) or len(coords) != 3:
            raise ValueError("Coordinates must be a tuple/list of exactly 3 floats")

        validated_coords = []
        for i, coord in enumerate(coords):
            try:
                coord_float = float(coord)
                # Prevent extreme values that could cause numerical instability
                if abs(coord_float) > 1e6:
                    raise ValueError(f"Coordinate {i} value too extreme: {coord_float}")
                validated_coords.append(coord_float)
            except (ValueError, TypeError):
                raise ValueError(f"Coordinate {i} must be a valid number")

        return tuple(validated_coords)

    @staticmethod
    def sanitize_query(query: str) -> str:
        """Sanitize and prepare query for cognitive processing."""
        # Remove potentially harmful patterns
        query = re.sub(r"[<>]", "", query)  # Remove angle brackets
        query = re.sub(r"javascript:", "", query, flags=re.IGNORECASE)
        query = re.sub(r"data:", "", query, flags=re.IGNORECASE)

        return CognitiveInputValidator.validate_text_input(query, "query")
