"""D7: no orphan Milvus writes — T-1 says Milvus writes only through SFM.

Oak option vectors used to go straight into a private ``oak_options`` Milvus
collection via ``MilvusClient.upsert_option``, with sha256 pseudo-vectors and
no provenance. The planner never read those vectors — a write-only orphan
store. This suite pins the closed state:

* ``api/endpoints/oak.py`` routes option persistence through SFM
  (``memory_type=semantic``, ``payload.kind=option``) and never touches
  MilvusClient
* ``jobs/milvus_reconciliation.py`` (the orphan-collection twin) is gone
* ``memory/milvus_client.py`` no longer fabricates hash vectors or writes
  options
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "somabrain"


def _read(rel: str) -> str:
    return (PKG / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Oak routes through SFM
# ---------------------------------------------------------------------------


def test_oak_does_not_use_milvus_client() -> None:
    src = _read("api/endpoints/oak.py")
    assert "MilvusClient" not in src
    assert "upsert_option" not in src
    assert "milvus_client" not in src


def test_oak_option_write_is_sfm_semantic_option() -> None:
    src = _read("api/endpoints/oak.py")
    assert "memory_type" in src
    assert "semantic" in src
    assert "option" in src
    # The SFM gateway, not a vector store, is the write path.
    assert "MemoryClient" in src or "store_from_payload" in src or "remember" in src


# ---------------------------------------------------------------------------
# Orphan job + fake vectors deleted
# ---------------------------------------------------------------------------


def test_milvus_reconciliation_job_is_deleted() -> None:
    assert not (PKG / "jobs" / "milvus_reconciliation.py").exists()


def test_milvus_client_has_no_fake_hash_vectors() -> None:
    src = _read("memory/milvus_client.py")
    assert "_vector_from_payload" not in src
    assert "hashlib.sha256" not in src


def test_milvus_client_has_no_option_write_path() -> None:
    src = _read("memory/milvus_client.py")
    assert "def upsert_option" not in src
    assert "def search_similar" not in src


# ---------------------------------------------------------------------------
# No remaining direct Milvus writes on the Oak path
# ---------------------------------------------------------------------------


def test_no_direct_milvus_writes_on_the_oak_path() -> None:
    """T-1 for the D7 seam: Oak never writes Milvus itself.

    In-memory ``.upsert`` on local ANN indexes is out of scope here; this
    guard is the Oak/orphan-collection write surface only.
    """
    offenders: list[str] = []
    for rel in (
        "api/endpoints/oak.py",
        "memory/milvus_client.py",
    ):
        src = _read(rel)
        for lineno, line in enumerate(src.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "upsert_option" in stripped or "collection.insert" in stripped:
                offenders.append(f"{rel}:{lineno}: {stripped!r}")
    assert not offenders, "direct Milvus writes on the Oak path:\n" + "\n".join(
        offenders
    )


def test_jobs_package_has_no_milvus_reconciliation() -> None:
    jobs = PKG / "jobs"
    if jobs.exists():
        assert not any(jobs.glob("*milvus*"))

