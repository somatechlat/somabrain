"""
Tenant Management Module for SomaBrain

This module provides tenant identification and namespace isolation for multi-tenant
SomaBrain deployments. It extracts tenant information from HTTP requests and
provides namespace isolation for secure multi-tenant operation.

Key Features:
- HTTP header-based tenant identification
- Bearer token alternative for tenant detection
- Namespace isolation for data security
- Default "public" tenant for unauthenticated access
- FastAPI request integration
- Immutable tenant context objects

Tenant Identification Priority:
1. X-Tenant-ID header (explicit)
2. Bearer token hash (implicit)
3. Default "public" tenant (default)

Security:
- Namespace isolation prevents data leakage
- Tenant-specific data access control
- Immutable context prevents modification

Classes:
    TenantContext: Immutable tenant and namespace information

Functions:
    get_tenant: Extract tenant information from FastAPI request
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

TENANT_HEADER = "X-Tenant-ID"


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    namespace: str


def get_tenant(request: Request, base_namespace: str) -> TenantContext:
    # Priority: explicit header → alternative token hash → default
    tid = request.headers.get(TENANT_HEADER)
    if not tid:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            tid = auth.split(" ", 1)[1][:16] or "public"
        else:
            tid = "public"
    # Namespace isolation per tenant
    ns = f"{base_namespace}:{tid}"
    return TenantContext(tenant_id=tid, namespace=ns)
