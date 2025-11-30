from __future__ import annotations
import hashlib
import hmac
import json
from typing import Optional
from common.logging import logger

"""
Provenance Verification Module for SomaBrain

This module implements HMAC-based provenance verification for API requests.
It ensures that write operations (like memory storage) come from authorized
sources by validating cryptographic signatures.

Key Features:
    pass
- HMAC-SHA256 signature verification
- Canonical JSON body normalization
- Header-based signature transmission
- Configurable secret key validation
- Secure comparison to prevent timing attacks

Security Features:
    pass
- Cryptographic signature validation
- Canonical message formatting
- Timing-attack resistant comparison
- Optional secret key configuration

Provenance Header Format:
    X-Provenance: HMAC-SHA256=<hex_signature>

Applications:
    pass
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




def canonical_body(body: bytes) -> bytes:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        obj = json.loads(body.decode("utf-8"))
        return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return body or b""


def verify_hmac_sha256(secret: Optional[str], body: bytes, header: str) -> bool:
    if not secret:
        return False
    if not header:
        return False
    algo, _, hexsig = header.partition("=")
    if algo.lower() != "hmac-sha256" or not hexsig:
        return False
    mac = hmac.new(
        secret.encode("utf-8"), canonical_body(body), hashlib.sha256
    ).hexdigest()
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return hmac.compare_digest(mac, hexsig)
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return False
