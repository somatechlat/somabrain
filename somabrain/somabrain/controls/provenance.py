from __future__ import annotations

import hashlib
import hmac
import json
from typing import Optional


def canonical_body(body: bytes) -> bytes:
    try:
        obj = json.loads(body.decode("utf-8"))
        return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
    except Exception:
        return body or b""


def verify_hmac_sha256(secret: Optional[str], body: bytes, header: str) -> bool:
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

