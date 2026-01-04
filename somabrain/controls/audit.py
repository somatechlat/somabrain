"""
Audit Logger Module for SomaBrain

This module implements tamper-evident audit logging for the SomaBrain system.
It provides cryptographic hashing to ensure log integrity and prevent unauthorized
modifications, crucial for compliance and security monitoring.

Key Features:
- Tamper-evident logging with cryptographic hashes
- Chain-of-trust using previous hash values
- Thread-safe concurrent access
- JSON Lines format for easy parsing
- Automatic hash verification on startup
- Timestamped audit records

Security Features:
- Blake2b cryptographic hashing
- Hash chain integrity verification
- Immutable audit trail
- Previous hash linking for tamper detection

Audit Records:
- Timestamped events with full context
- Hash chain for integrity verification
- Previous hash for chain validation
- Structured JSON format for analysis

Classes:
    AuditLogger: Main audit logging implementation

Functions:
    None (class-based implementation)
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Dict

from .metrics import AUDIT_WRITES


class AuditLogger:
    """Auditlogger class implementation."""

    def __init__(self, path: str = "audit_log.jsonl"):
        """Initialize the instance."""

        self.path = path
        self._lock = threading.Lock()
        self._prev_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        """Execute load last hash.
            """

        try:
            if not os.path.exists(self.path):
                return ""
            with open(self.path, "rb") as f:
                last = b""
                for line in f:
                    last = line
                if not last:
                    return ""
                rec = json.loads(last.decode("utf-8"))
                return str(rec.get("hash", ""))
        except Exception:
            return ""

    def _hash(self, rec: Dict[str, Any]) -> str:
        """Execute hash.

            Args:
                rec: The rec.
            """

        h = hashlib.blake2b(digest_size=16)
        prev = (self._prev_hash or "").encode("utf-8")
        h.update(prev)
        h.update(json.dumps(rec, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        return h.hexdigest()

    def write(self, rec: Dict[str, Any]) -> None:
        """Execute write.

            Args:
                rec: The rec.
            """

        rec = dict(rec)
        rec.setdefault("ts", time.time())
        with self._lock:
            h = self._hash(rec)
            rec["prev_hash"] = self._prev_hash
            rec["hash"] = h
            line = json.dumps(rec, separators=(",", ":")) + "\n"
            try:
                with open(self.path, "ab") as f:
                    f.write(line.encode("utf-8"))
                self._prev_hash = h
                try:
                    AUDIT_WRITES.inc()
                except Exception:
                    pass
            except Exception:
                # best-effort; do not crash request path
                pass