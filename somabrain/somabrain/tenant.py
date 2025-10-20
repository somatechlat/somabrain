from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from fastapi import Request


TENANT_HEADER = "X-Tenant-ID"


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    namespace: str


def get_tenant(request: Request, base_namespace: str) -> TenantContext:
    # Priority: explicit header → fallback to token hash → default
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

