"""T-2 golden-vector parity — one coordinate hash, frozen outputs.

Guards the cross-repo shared module ``soma_memory_contract``. SomaBrain's
``serialization._stable_coord`` must be the shared symbol (not a copy), and
every derivation must match the frozen vectors below.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

from soma_memory_contract import _stable_coord as shared_stable_coord
from soma_memory_contract import make_coord as shared_make_coord
from somabrain.memory.client.serialization import _stable_coord

# Frozen outputs of blake2b digest_size=12 → [-1,1]^3. Do not regenerate to
# "fix" a failure — a mismatch means the hash math changed and must be reverted.
STABLE_COORD_GOLDEN = [
    (
        "real::tenant-a|episodic|2026-10-03T00:00:00Z|hello seam",
        0.24714936409145594,
        0.09493384370580316,
        -0.9746199166402221,
    ),
    (
        "real::tenant-b|semantic|2026-10-03T00:01:00Z|shared text",
        -0.6081309374421835,
        -0.8184258714318275,
        0.9730786420404911,
    ),
    ("", 0.44439287623390555, 0.3440746674314141, -0.9154480644501746),
    ("x", -0.6184049095027149, -0.82011533761397, -0.012718055862933397),
    (
        "idempotency:mem:0.41,0.42,0.43",
        -0.9963827859610319,
        0.32875058613717556,
        0.37231292948126793,
    ),
    (
        "real::a|b|c|d",
        0.568278412334621,
        -0.906532492954284,
        0.34637327026575804,
    ),
]

SEEDS_32 = [
    (f"tenant{i}", "episodic", f"2026-10-03T00:{i:02d}:00Z", f"text {i}")
    for i in range(32)
]


class TestGoldenVectors:
    """Frozen hash outputs — the contract cannot drift."""

    @pytest.mark.parametrize(
        "seed,x,y,z", STABLE_COORD_GOLDEN, ids=[s for s, *_ in STABLE_COORD_GOLDEN]
    )
    def test_stable_coord_matches_golden(self, seed, x, y, z):
        assert _stable_coord(seed) == (x, y, z)

    def test_serialization_reexports_shared_symbol(self):
        assert _stable_coord is shared_stable_coord


class TestCrossRepoParity:
    """Brain serialization and shared module must be one authority."""

    @pytest.mark.parametrize(
        "tenant,kind,ts,text", SEEDS_32, ids=[t for t, *_ in SEEDS_32]
    )
    def test_make_coord_matches_stable_coord_path(self, tenant, kind, ts, text):
        from soma_memory_contract import coord_from_key_material, coord_key_material

        material = coord_key_material(tenant, kind, ts, text)
        assert shared_make_coord(tenant, kind, ts, text) == coord_from_key_material(
            material
        )
        x, y, z = _stable_coord(f"real::{material}")
        assert shared_make_coord(tenant, kind, ts, text) == f"{x},{y},{z}"


class TestOneDefinition:
    """T-2 exit criterion: one definition of the coord hash across the triad."""

    def test_exactly_one_stable_coord_definition_in_triad(self):
        roots = [
            Path(__file__).resolve().parents[2],  # somabrain
            Path(__file__).resolve().parents[2].parent / "somaAgent01",
            Path(__file__).resolve().parents[2].parent / "somafractalmemory",
            Path(__file__).resolve().parents[2].parent / "soma-memory-contract",
        ]
        pattern = "def " + "_stable_coord"
        hits: list[str] = []
        for root in roots:
            if not root.is_dir():
                continue
            proc = subprocess.run(
                ["grep", "-rn", "--include=*.py", pattern, str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            for line in proc.stdout.splitlines():
                if ".venv" in line or "__pycache__" in line:
                    continue
                hits.append(line)
        assert len(hits) == 1, f"expected 1 definition, found {len(hits)}:\n" + "\n".join(
            hits
        )
