"""
Sparse Distributed Representations (SDR) Module for SomaBrain.

This module implements sparse distributed representations and locality-sensitive hashing
for efficient similarity search and encoding of high-dimensional data. SDRs provide
a biologically-inspired approach to representing information with controlled sparsity.

Key Features:
- Deterministic SDR encoding using random hashing
- Configurable sparsity and dimensionality via Settings
- Locality-sensitive hashing (LSH) for approximate nearest neighbor search
- Banding technique for efficient similarity detection
- Memory-efficient storage of sparse binary vectors

Configuration:
- SOMABRAIN_SDR_DIM: SDR dimensionality (default 16384)
- SOMABRAIN_SDR_SPARSITY: Sparsity density (default 0.01)

Classes:
    SDREncoder: Encoder for converting text into sparse distributed representations.
    LSHIndex: Locality-sensitive hashing index for SDR similarity search.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Set, Tuple

from django.conf import settings


class SDREncoder:
    """
    Simple sparse high-dimensional binary encoder using random hashing.

    This encoder converts text into sparse distributed representations (SDRs) by
    deterministically selecting a fixed number of active bits through hashing.
    The encoding is deterministic for the same input and provides efficient
    similarity computation through bitwise operations.

    Attributes:
        dim (int): Dimensionality of the SDR vector space.
        k (int): Number of active bits (sparsity level).

    Example:
        >>> encoder = SDREncoder(dim=8192, density=0.02)
        >>> sdr = encoder.encode("machine learning")
        >>> print(f"Active bits: {len(sdr)} out of {encoder.dim}")
    """

    def __init__(self, dim: int | None = None, density: float | None = None):
        """
        Initialize the SDR encoder with specified parameters.

        Args:
            dim (int, optional): Dimensionality of the SDR space. Defaults to settings.SOMABRAIN_SDR_DIM.
            density (float, optional): Sparsity density (fraction of active bits). Defaults to settings.SOMABRAIN_SDR_SPARSITY.
        """
        self.dim = int(dim if dim is not None else settings.SOMABRAIN_SDR_DIM)
        self.k = max(
            1,
            int(
                self.dim
                * float(density if density is not None else settings.SOMABRAIN_SDR_SPARSITY)
            ),
        )

    @staticmethod
    def _tokens(text: str) -> List[str]:
        """
        Tokenize text into alphanumeric tokens for encoding.

        Extracts tokens consisting of letters, numbers, and underscores with
        minimum length of 2 characters. Converts to lowercase for normalization.

        Args:
            text (str): Input text to tokenize.

        Returns:
            List[str]: List of extracted tokens.

        Note:
            Uses regex pattern [A-Za-z0-9_]+ to match tokens.
        """
        import re

        return [t for t in re.findall(r"[A-Za-z0-9_]+", (text or "").lower()) if len(t) >= 2]

    def encode(self, text: str) -> Set[int]:
        """
        Encode text into a sparse distributed representation.

        Converts input text into an SDR by hashing tokens and selecting k active
        indices deterministically. Uses multiple hash salts if needed to reach
        the target sparsity level.

        Args:
            text (str): Text to encode into SDR.

        Returns:
            Set[int]: Set of active indices representing the SDR.
                       Empty set if no valid tokens found.

        Note:
            Uses BLAKE2b hash function with 8-byte digest for efficiency.
            Multiple salts are used iteratively until k bits are activated.
        """
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
    """
    Locality-sensitive hashing index over SDRs using banding technique.

    This index enables efficient approximate nearest neighbor search for SDRs by
    using locality-sensitive hashing with banding. SDRs are divided into bands,
    and each band is hashed to enable fast candidate retrieval.

    The banding approach reduces the probability of false negatives while maintaining
    efficiency. It's particularly effective for high-dimensional sparse data.

    Attributes:
        bands (int): Number of bands for hashing.
        rows (int): Number of rows per band.
        dim (int): Dimensionality of the SDR space.
        tables (List[Dict[int, Set[Tuple[float, float, float]]]]): Hash tables for each band.

    Example:
        >>> index = LSHIndex(bands=8, rows=16, dim=16384)
        >>> coord = (1.0, 2.0, 3.0)
        >>> sdr = {1, 100, 500, 1000}  # example SDR
        >>> index.add(coord, sdr)
        >>> candidates = index.query(sdr, limit=10)
    """

    def __init__(self, bands: int = 8, rows: int = 16, dim: int | None = None):
        """
        Initialize the LSH index with banding parameters.

        Args:
            bands (int, optional): Number of bands for hashing. Defaults to 8.
            rows (int, optional): Number of rows per band. Defaults to 16.
            dim (int, optional): Dimensionality of SDR space. Defaults to settings.SOMABRAIN_SDR_DIM.
        """
        self.bands = int(bands)
        self.rows = int(rows)
        self.dim = int(dim if dim is not None else settings.SOMABRAIN_SDR_DIM)
        self.tables: List[Dict[int, Set[Tuple[float, float, float]]]] = [
            dict() for _ in range(self.bands)
        ]

    def _band_hashes(self, bits: Set[int]) -> List[int]:
        """
        Compute band hashes for an SDR using the banding technique.

        Divides the SDR into bands and computes a hash for each band based on
        the active bits within that band's range. Uses a simple hash function
        with XOR and multiplication for efficiency.

        Args:
            bits (Set[int]): Active indices of the SDR.

        Returns:
            List[int]: List of hash values, one per band.

        Note:
            Uses FNV-style hash with XOR accumulation and multiplication.
            Band size is calculated as dim / (bands * rows).
        """
        # Represent SDR as sorted indices; compute band hashes by chunking ranges
        band_size = max(1, self.dim // (self.bands * self.rows))
        hashes: List[int] = []
        for b in range(self.bands):
            start = b * band_size * self.rows
            end = min(self.dim, start + band_size * self.rows)
            # select bits in this band window
            acc = 1469598103934665603
            for i in sorted(x for x in bits if start <= x < end):
                acc ^= i + 0x9E3779B97F4A7C15
                acc = (acc * 1099511628211) & ((1 << 64) - 1)
            hashes.append(acc)
        return hashes

    def add(self, coord: Tuple[float, float, float], bits: Set[int]) -> None:
        """
        Add a coordinate-SDR pair to the LSH index.

        Inserts the coordinate into all relevant hash buckets based on the
        SDR's band hashes. This enables efficient retrieval of similar SDRs.

        Args:
            coord (Tuple[float, float, float]): Coordinate associated with the SDR.
            bits (Set[int]): Active indices of the SDR to index.

        Note:
            The same coordinate may be stored in multiple buckets across bands.
        """
        for b, hv in enumerate(self._band_hashes(bits)):
            bucket = self.tables[b].setdefault(hv, set())
            bucket.add(coord)

    def query(self, bits: Set[int], limit: int = 100) -> List[Tuple[float, float, float]]:
        """
        Query the index for coordinates with similar SDRs.

        Retrieves candidate coordinates that have SDRs hashing to the same
        buckets as the query SDR. Returns unique coordinates up to the limit.

        Args:
            bits (Set[int]): Active indices of the query SDR.
            limit (int, optional): Maximum number of candidates to return. Defaults to 100.

        Returns:
            List[Tuple[float, float, float]]: List of candidate coordinates.
                                               May be fewer than limit if fewer matches exist.

        Note:
            Results are deduplicated across bands to avoid duplicate coordinates.
            Early termination occurs when the limit is reached.
        """
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
