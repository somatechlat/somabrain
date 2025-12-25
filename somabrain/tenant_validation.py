"""Tenant validation utilities for SomaBrain.

Extracted from tenant_registry.py per monolithic-decomposition spec.
Provides tenant ID validation and normalization functions.
"""

from __future__ import annotations

import re
from typing import Set

# Invalid characters for tenant IDs (security-sensitive)
INVALID_TENANT_CHARS: Set[str] = {
    "<",
    ">",
    '"',
    "'",
    "&",
    ";",
    "\\",
    "/",
    "?",
    " ",
    "\t",
    "\n",
    "\r",
}

# Tenant ID constraints
MIN_TENANT_ID_LENGTH = 3
MAX_TENANT_ID_LENGTH = 64

# Valid tenant ID pattern (alphanumeric, underscores, hyphens)
TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def normalize_tenant_id(tenant_id: str) -> str:
    """Normalize tenant ID for consistent comparison.

    Args:
        tenant_id: Raw tenant ID string

    Returns:
        Normalized tenant ID (lowercase, stripped)
    """
    return tenant_id.strip().lower()


def validate_tenant_id(tenant_id: str) -> bool:
    """Validate tenant ID format and security.

    Checks:
    - Length between 3 and 64 characters
    - No invalid/dangerous characters
    - Matches alphanumeric pattern with underscores and hyphens

    Args:
        tenant_id: Tenant ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not tenant_id:
        return False

    if len(tenant_id) < MIN_TENANT_ID_LENGTH or len(tenant_id) > MAX_TENANT_ID_LENGTH:
        return False

    # Check for invalid characters (security)
    if any(char in tenant_id for char in INVALID_TENANT_CHARS):
        return False

    # Validate format (alphanumeric, underscores, hyphens)
    if not TENANT_ID_PATTERN.match(tenant_id):
        return False

    return True


def validate_tenant_id_strict(tenant_id: str) -> tuple[bool, str]:
    """Validate tenant ID with detailed error message.

    Args:
        tenant_id: Tenant ID to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not tenant_id:
        return False, "Tenant ID cannot be empty"

    if len(tenant_id) < MIN_TENANT_ID_LENGTH:
        return False, f"Tenant ID must be at least {MIN_TENANT_ID_LENGTH} characters"

    if len(tenant_id) > MAX_TENANT_ID_LENGTH:
        return False, f"Tenant ID must be at most {MAX_TENANT_ID_LENGTH} characters"

    # Check for invalid characters
    found_invalid = [char for char in tenant_id if char in INVALID_TENANT_CHARS]
    if found_invalid:
        return False, f"Tenant ID contains invalid characters: {found_invalid}"

    # Validate format
    if not TENANT_ID_PATTERN.match(tenant_id):
        return (
            False,
            "Tenant ID must contain only alphanumeric characters, underscores, and hyphens",
        )

    return True, ""


def sanitize_tenant_id(tenant_id: str) -> str:
    """Sanitize tenant ID by removing invalid characters.

    Note: This is a best-effort sanitization. The result should still
    be validated with validate_tenant_id() before use.

    Args:
        tenant_id: Raw tenant ID string

    Returns:
        Sanitized tenant ID
    """
    if not tenant_id:
        return ""

    # Remove invalid characters
    sanitized = "".join(char for char in tenant_id if char not in INVALID_TENANT_CHARS)

    # Replace remaining invalid pattern characters with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", sanitized)

    # Collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized)

    # Strip leading/trailing underscores
    sanitized = sanitized.strip("_")

    return sanitized
