from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Dict

from .metrics import AUDIT_WRITES


class AuditLogger:
    def __init__(self, path: str = "audit_log.jsonl"):
        self.path = path
        self._lock = threading.Lock()
        self._prev_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
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
        h = hashlib.blake2b(digest_size=16)
        prev = (self._prev_hash or "").encode("utf-8")
        h.update(prev)
        h.update(json.dumps(rec, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        return h.hexdigest()

    def write(self, rec: Dict[str, Any]) -> None:
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
