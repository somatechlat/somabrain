"""Input Validation - Cognitive input validation for safe processing."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("somabrain.cognitive")


class CognitiveInputValidator:
    """Advanced input validation for brain-like cognitive processing."""

    SAFE_TEXT_PATTERN = re.compile(r"^[a-zA-Z0-9\s\.,!?'\"()/:_@-]+$")
    MAX_TEXT_LENGTH = 10000
    MAX_EMBEDDING_DIM = 4096
    MIN_EMBEDDING_DIM = 64

    @staticmethod
    def validate_text_input(text: str, field_name: str = "text") -> str:
        """Validate text input for cognitive processing."""
        if not text:
            raise ValueError(f"{field_name} cannot be empty")

        if len(text) > CognitiveInputValidator.MAX_TEXT_LENGTH:
            raise ValueError(
                f"{field_name} exceeds maximum length of {CognitiveInputValidator.MAX_TEXT_LENGTH}"
            )

        if not CognitiveInputValidator.SAFE_TEXT_PATTERN.match(text):
            logger.warning(
                f"Potentially unsafe input detected in {field_name}: {text[:100]}..."
            )
            raise ValueError(f"{field_name} contains unsafe characters")

        return text.strip()

    @staticmethod
    def validate_embedding_dim(dim: int) -> int:
        """Validate embedding dimensions for brain safety."""
        if not isinstance(dim, int) or dim < CognitiveInputValidator.MIN_EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dimension must be at least {CognitiveInputValidator.MIN_EMBEDDING_DIM}"
            )

        if dim > CognitiveInputValidator.MAX_EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dimension cannot exceed {CognitiveInputValidator.MAX_EMBEDDING_DIM}"
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
                if abs(coord_float) > 1e6:
                    raise ValueError(f"Coordinate {i} value too extreme: {coord_float}")
                validated_coords.append(coord_float)
            except (ValueError, TypeError):
                raise ValueError(f"Coordinate {i} must be a valid number")

        return tuple(validated_coords)

    @staticmethod
    def sanitize_query(query: str) -> str:
        """Sanitize and prepare query for cognitive processing."""
        query = re.sub(r"[<>]", "", query)
        query = re.sub(r"javascript:", "", query, flags=re.IGNORECASE)
        query = re.sub(r"data:", "", query, flags=re.IGNORECASE)
        return CognitiveInputValidator.validate_text_input(query, "query")