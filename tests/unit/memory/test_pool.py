"""Regression tests for the multi-tenant memory pool."""

from __future__ import annotations


def test_for_namespace_returns_client_with_namespace():
    from django.conf import settings

    from somabrain.memory.pool import MultiTenantMemory

    pool = MultiTenantMemory(cfg=settings)
    client = pool.for_namespace("tenant-xyz")
    assert client.namespace == "tenant-xyz"
    assert pool.for_namespace("tenant-xyz") is client
    assert pool.for_namespace("other-tenant").namespace == "other-tenant"
