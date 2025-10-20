from __future__ import annotations

import hashlib
import math
from typing import Dict, List, Set, Tuple


class SDREncoder:
    """Simple sparse high-D binary encoder using random hashing.

    Deterministic: select k active indices via hashing of tokens.
    """

    def __init__(self, dim: int = 16384, density: float = 0.01):
        self.dim = int(dim)
        self.k = max(1, int(self.dim * float(density)))

    @staticmethod
    def _tokens(text: str) -> List[str]:
        import re
        return [t for t in re.findall(r"[A-Za-z0-9_]+", (text or "").lower()) if len(t) >= 2]

    def encode(self, text: str) -> Set[int]:
        toks = self._tokens(text)
        if not toks:
            return set()
        idx: Set[int] = set()
        # hash each token with multiple salts until k bits set
        salt = 0
        h = hashlib.blake2b
        while len(idx) < self.k:
            for t in toks:
                hv = int.from_bytes(h(f"{t}:{salt}".encode(), digest_size=8).digest(), "big")
                idx.add(hv % self.dim)
                if len(idx) >= self.k:
                    break
            salt += 1
        return idx


class LSHIndex:
    """LSH index over SDRs using banding.

    Each vector's bitset is split into bands; band hashes map to coordinates.
    """

    def __init__(self, bands: int = 8, rows: int = 16, dim: int = 16384):
        self.bands = int(bands)
        self.rows = int(rows)
        self.dim = int(dim)
        self.tables: List[Dict[int, Set[Tuple[float, float, float]]]] = [dict() for _ in range(self.bands)]

    def _band_hashes(self, bits: Set[int]) -> List[int]:
        # Represent SDR as sorted indices; compute band hashes by chunking ranges
        band_size = max(1, self.dim // (self.bands * self.rows))
        hashes: List[int] = []
        for b in range(self.bands):
            start = b * band_size * self.rows
            end = min(self.dim, start + band_size * self.rows)
            # select bits in this band window
            acc = 1469598103934665603
            for i in sorted(x for x in bits if start <= x < end):
                acc ^= i + 0x9e3779b97f4a7c15
                acc = (acc * 1099511628211) & ((1 << 64) - 1)
            hashes.append(acc)
        return hashes

    def add(self, coord: Tuple[float, float, float], bits: Set[int]) -> None:
        for b, hv in enumerate(self._band_hashes(bits)):
            bucket = self.tables[b].setdefault(hv, set())
            bucket.add(coord)

    def query(self, bits: Set[int], limit: int = 100) -> List[Tuple[float, float, float]]:
        seen: Set[Tuple[float, float, float]] = set()
        for b, hv in enumerate(self._band_hashes(bits)):
            bucket = self.tables[b].get(hv)
            if not bucket:
                continue
            for c in bucket:
                if c not in seen:
                    seen.add(c)
                    if len(seen) >= max(1, int(limit)):
                        return list(seen)
        return list(seen)

