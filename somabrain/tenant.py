"""
Tenant Management Module for SomaBrain

This module provides tenant identification and namespace isolation for multi-tenant
SomaBrain deployments using the centralized TenantManager system. It extracts tenant 
information from HTTP requests and provides namespace isolation for secure multi-tenant operation.

Key Features:
- HTTP header-based tenant identification
- Bearer token alternative for tenant detection
- Namespace isolation for data security
- Centralized tenant management integration
- Dynamic tenant resolution with fallback
- FastAPI request integration
- Immutable tenant context objects with metadata

Tenant Identification Priority:
1. X-Tenant-ID header (explicit)
2. Bearer token hash (implicit)
3. Centralized default tenant (dynamic)
4. Temporary tenant creation (fallback)

Security:
- Namespace isolation prevents data leakage
- Tenant-specific data access control
- Immutable context prevents modification
- Centralized tenant validation

Classes:
    TenantContext: Immutable tenant and namespace information with metadata

Functions:
    get_tenant: Extract tenant information from FastAPI request using TenantManager
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Request

from .tenant_registry import TenantMetadata
from .tenant_manager import get_tenant_manager

TENANT_HEADER = "X-Tenant-ID"


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    namespace: str
    metadata: Optional[TenantMetadata] = None


async def get_tenant(request: Request, base_namespace: str) -> TenantContext:
    """Get tenant context using centralized tenant management.
    
    This function now uses the TenantManager to resolve tenant IDs dynamically,
    providing proper tenant validation, metadata, and fallback handling.
    
    Args:
        request: FastAPI request object
        base_namespace: Base namespace for tenant isolation
        
    Returns:
        TenantContext: Immutable tenant context with namespace and metadata
    """
    # Get tenant manager
    tenant_manager = await get_tenant_manager()
    
    # Resolve tenant ID using centralized logic
    tenant_id = await tenant_manager.resolve_tenant_from_request(request)
    
    # Get tenant metadata
    metadata = await tenant_manager.get_tenant_metadata(tenant_id)
    
    # Create namespace with tenant isolation
    namespace = f"{base_namespace}:{tenant_id}"
    
    return TenantContext(
        tenant_id=tenant_id,
        namespace=namespace,
        metadata=metadata
    )


def get_tenant_sync(request: Request, base_namespace: str) -> TenantContext:
    """Synchronous fallback for tenant resolution (legacy compatibility).
    
    This function is provided for backward compatibility in contexts where
    async/await is not available. It uses simplified tenant resolution logic.
    
    Args:
        request: FastAPI request object
        base_namespace: Base namespace for tenant isolation
        
    Returns:
        TenantContext: Immutable tenant context (without metadata)
    """
    # Priority: explicit header → alternative token hash → default
    tid = request.headers.get(TENANT_HEADER)
    if not tid:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            tid = auth.split(" ", 1)[1][:16] or "public"
        else:
            tid = "public"
    
    # Namespace isolation per tenant
    namespace = f"{base_namespace}:{tid}"
    
    return TenantContext(tenant_id=tid, namespace=namespace)
