"""
Provenance Verification Module for SomaBrain

This module implements HMAC-based provenance verification for API requests.
It ensures that write operations (like memory storage) come from authorized
sources by validating cryptographic signatures.

Key Features:
- HMAC-SHA256 signature verification
- Canonical JSON body normalization
- Header-based signature transmission
- Configurable secret key validation
- Secure comparison to prevent timing attacks

Security Features:
- Cryptographic signature validation
- Canonical message formatting
- Timing-attack resistant comparison
- Optional secret key configuration

Provenance Header Format:
    X-Provenance: HMAC-SHA256=<hex_signature>

Applications:
- API request authentication
- Write operation authorization
- Data integrity verification
- Audit trail validation

Functions:
    canonical_body: Normalize request body for consistent signing
    verify_hmac_sha256: Verify HMAC signature against request body

Classes:
    None (utility function-based implementation)
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Optional


def canonical_body(body: bytes) -> bytes:
    """Execute canonical body.

    Args:
        body: The body.
    """

    try:
        obj = json.loads(body.decode("utf-8"))
        return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
    except Exception:
        return body or b""


def verify_hmac_sha256(secret: Optional[str], body: bytes, header: str) -> bool:
    """Execute verify hmac sha256.

    Args:
        secret: The secret.
        body: The body.
        header: The header.
    """

    if not secret:
        return False
    if not header:
        return False
    algo, _, hexsig = header.partition("=")
    if algo.lower() != "hmac-sha256" or not hexsig:
        return False
    mac = hmac.new(secret.encode("utf-8"), canonical_body(body), hashlib.sha256).hexdigest()
    try:
        return hmac.compare_digest(mac, hexsig)
    except Exception:
        return False
