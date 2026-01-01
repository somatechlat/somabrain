#!/usr/bin/env python3
"""Milvus integration test for SomaBrain ANN backend.

This script verifies that the Milvus vector database is properly configured
and operational for the TieredMemory cleanup index.

VIBE CODING RULES:
- Real Milvus connection required (no mocks)
- All configuration from settings
- Fails fast on connection issues
"""

from __future__ import annotations

import sys

import numpy as np


def test_milvus_connection() -> bool:
    """Test basic Milvus connectivity."""
    print("[1/4] Testing Milvus connection...")
    try:
        from pymilvus import connections, utility

        from django.conf import settings

        host = getattr(settings, "SOMABRAIN_MILVUS_HOST", "localhost")
        port = getattr(settings, "SOMABRAIN_MILVUS_PORT", 19530)

        connections.connect(alias="test", host=host, port=port)
        version = utility.get_server_version()
        print(f"  ✓ Connected to Milvus {version} at {host}:{port}")
        connections.disconnect("test")
        return True
    except Exception as exc:
        print(f"  ✗ Connection failed: {exc}")
        return False


def test_milvus_ann_index() -> bool:
    """Test MilvusAnnIndex creation and basic operations."""
    print("[2/4] Testing MilvusAnnIndex...")
    try:
        from somabrain.services.milvus_ann import MilvusAnnIndex

        dim = 64
        index = MilvusAnnIndex(
            dim,
            tenant_id="test_integration",
            namespace="test",
            top_k=10,
        )

        # Test upsert
        vec1 = np.random.randn(dim).astype(np.float32)
        vec2 = np.random.randn(dim).astype(np.float32)
        index.upsert("anchor_1", vec1)
        index.upsert("anchor_2", vec2)
        print("  ✓ Upsert operations successful")

        # Test search
        results = index.search(vec1, top_k=5)
        if results and results[0][0] == "anchor_1":
            print(f"  ✓ Search returned correct result: {results[0]}")
        else:
            print(f"  ✗ Search returned unexpected result: {results}")
            return False

        # Test remove
        index.remove("anchor_1")
        results_after = index.search(vec1, top_k=5)
        if not any(r[0] == "anchor_1" for r in results_after):
            print("  ✓ Remove operation successful")
        else:
            print("  ✗ Remove failed - anchor still found")
            return False

        # Cleanup
        index.remove("anchor_2")

        stats = index.stats()
        print(f"  ✓ Index stats: {stats}")
        return True
    except Exception as exc:
        print(f"  ✗ MilvusAnnIndex test failed: {exc}")
        import traceback

        traceback.print_exc()
        return False


def test_create_cleanup_index_factory() -> bool:
    """Test that create_cleanup_index returns MilvusAnnIndex by default."""
    print("[3/4] Testing create_cleanup_index factory...")
    try:
        from somabrain.services.ann import AnnConfig, create_cleanup_index

        # Test default config uses Milvus
        config = AnnConfig.from_settings()
        print(f"  Backend from settings: {config.backend}")

        if config.backend != "milvus":
            print(f"  ✗ Expected 'milvus' backend, got '{config.backend}'")
            return False

        # Create index with factory
        index = create_cleanup_index(
            dim=32,
            tenant_id="factory_test",
            namespace="test",
        )

        # Verify it's a MilvusAnnIndex
        from somabrain.services.milvus_ann import MilvusAnnIndex

        if isinstance(index, MilvusAnnIndex):
            print("  ✓ Factory created MilvusAnnIndex")
        else:
            print(
                f"  ✗ Factory created {type(index).__name__} instead of MilvusAnnIndex"
            )
            return False

        return True
    except Exception as exc:
        print(f"  ✗ Factory test failed: {exc}")
        import traceback

        traceback.print_exc()
        return False


def test_settings_configuration() -> bool:
    """Verify settings are correctly configured for Milvus."""
    print("[4/4] Testing settings configuration...")
    try:
        from django.conf import settings

        print(f"  milvus_host: {getattr(settings, 'SOMABRAIN_MILVUS_HOST', None)}")
        print(f"  milvus_port: {getattr(settings, 'SOMABRAIN_MILVUS_PORT', None)}")
        print(
            f"  tiered_memory_cleanup_backend: {getattr(settings, 'SOMABRAIN_TIERED_MEMORY_CLEANUP_BACKEND', None)}"
        )

        if getattr(settings, "SOMABRAIN_TIERED_MEMORY_CLEANUP_BACKEND", None) != "milvus":
            print(
                f"  ✗ Expected cleanup backend 'milvus', got '{getattr(settings, 'SOMABRAIN_TIERED_MEMORY_CLEANUP_BACKEND', None)}'"
            )
            return False

        print("  ✓ Settings configured correctly for Milvus")
        return True
    except Exception as exc:
        print(f"  ✗ Settings test failed: {exc}")
        return False


def main() -> int:
    """Run all Milvus integration tests."""
    print("=" * 60)
    print("SomaBrain Milvus Integration Test")
    print("=" * 60)
    print()

    results = []

    # Run tests
    results.append(("Settings Configuration", test_settings_configuration()))
    results.append(("Milvus Connection", test_milvus_connection()))
    results.append(("MilvusAnnIndex Operations", test_milvus_ann_index()))
    results.append(("Factory Function", test_create_cleanup_index_factory()))

    print()
    print("=" * 60)
    print("Results Summary")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"  {symbol} {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print()
    print(f"Total: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
