#!/usr/bin/env python3
"""T-1 / B29 contract: SomaBrain never writes Milvus.

Milvus is owned by SFM only. Vector memory goes MemoryClient → SFM.
Cleanup indexes are in-process HRR anchors (hnsw/simple), never pymilvus.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

BRAIN_ROOT = Path(__file__).resolve().parents[1]


def test_milvus_ann_module_deleted() -> bool:
    print("[1/3] milvus_ann.py must not exist...")
    path = BRAIN_ROOT / "somabrain" / "services" / "milvus_ann.py"
    if path.exists():
        print(f"  ✗ still present: {path}")
        return False
    print("  ✓ deleted")
    return True


def test_cleanup_index_factory_forbids_milvus() -> bool:
    print("[2/3] create_cleanup_index must reject milvus backend...")
    try:
        from somabrain.services.ann import AnnConfig, create_cleanup_index

        cfg = AnnConfig(backend="milvus")
        try:
            create_cleanup_index(8, cfg)
        except ValueError as exc:
            if "forbidden" in str(exc).lower() or "T-1" in str(exc):
                print("  ✓ milvus backend hard-rejected")
            else:
                print(f"  ✗ wrong error: {exc}")
                return False
        else:
            print("  ✗ milvus backend was accepted")
            return False

        index = create_cleanup_index(8, AnnConfig(backend="simple"))
        vec = np.ones(8, dtype=np.float32)
        index.upsert("a", vec)
        hits = index.search(vec, top_k=1)
        if hits and hits[0][0] == "a":
            print("  ✓ in-process simple index works")
            return True
        print(f"  ✗ simple index broken: {hits}")
        return False
    except Exception as exc:
        print(f"  ✗ factory test failed: {exc}")
        import traceback

        traceback.print_exc()
        return False


def test_no_pymilvus_import_in_ann() -> bool:
    print("[3/3] ann.py must not import pymilvus...")
    src = (BRAIN_ROOT / "somabrain" / "services" / "ann.py").read_text(
        encoding="utf-8"
    )
    if "pymilvus" in src or "milvus_ann" in src:
        print("  ✗ pymilvus/milvus_ann still referenced")
        return False
    print("  ✓ clean")
    return True


def main() -> int:
    print("=" * 60)
    print("SomaBrain T-1 / B29: no direct Milvus write lane")
    print("=" * 60)
    results = [
        ("milvus_ann deleted", test_milvus_ann_module_deleted()),
        ("factory forbids milvus", test_cleanup_index_factory_forbids_milvus()),
        ("ann.py clean", test_no_pymilvus_import_in_ann()),
    ]
    passed = sum(1 for _, ok in results if ok)
    failed = len(results) - passed
    for name, ok in results:
        print(f"  {'✓' if ok else '✗'} {name}: {'PASS' if ok else 'FAIL'}")
    print(f"Total: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
