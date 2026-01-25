"""
Unified Search and Filtering API for SomaBrain.

Search across tenants, users, memories, and resources.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Tenant-scoped search, no data leakage
- 🏛️ Architect: Clean search patterns with filters
- 💾 DBA: Django ORM with indexed queries
- 🐍 Django Expert: Native Django Q objects
- 📚 Technical Writer: Comprehensive docstrings
- 🧪 QA Engineer: Testable search results
- 🚨 SRE: Search performance monitoring
- 📊 Performance: Paginated results, efficient queries
- 🎨 UX: Faceted search, relevance ranking
- 🛠️ DevOps: Search configuration
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from django.db.models import Count, Q
from ninja import Router, Schema

from somabrain.aaas.auth import AuthenticatedRequest, require_auth
from somabrain.aaas.granular import Permission, require_permission
from somabrain.aaas.models import (
    APIKey,
    AuditLog,
    Tenant,
    TenantUser,
    Webhook,
)

router = Router(tags=["Search"])


# =============================================================================
# SCHEMAS - ALL 10 PERSONAS
# =============================================================================


class SearchRequest(Schema):
    """Unified search request."""

    query: str
    types: Optional[List[str]] = None  # users, api_keys, webhooks, audit_logs
    limit: int = 20
    offset: int = 0


class SearchResultItem(Schema):
    """Individual search result."""

    type: str
    id: str
    title: str
    subtitle: Optional[str]
    relevance: float
    created_at: Optional[str]
    metadata: Optional[Dict[str, Any]]


class SearchResponse(Schema):
    """Unified search response."""

    query: str
    total_results: int
    results: List[SearchResultItem]
    facets: Dict[str, int]
    search_time_ms: int


class FilterRequest(Schema):
    """Filter request."""

    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, contains, in
    value: Any


class AdvancedSearchRequest(Schema):
    """Advanced search with filters."""

    query: Optional[str] = None
    filters: Optional[List[Dict[str, Any]]] = None
    sort_by: Optional[str] = None
    sort_order: str = "desc"
    limit: int = 50
    offset: int = 0


# =============================================================================
# SEARCH FUNCTIONS - ALL 10 PERSONAS
# =============================================================================


def search_users(tenant_id: str, query: str, limit: int = 20) -> List[dict]:
    """Search users within a tenant."""
    users = (
        TenantUser.objects.filter(tenant_id=tenant_id)
        .filter(Q(email__icontains=query) | Q(display_name__icontains=query))
        .order_by("-created_at")[:limit]
    )

    return [
        {
            "type": "user",
            "id": str(u.id),
            "title": u.email,
            "subtitle": u.display_name,
            "relevance": 1.0 if query.lower() in u.email.lower() else 0.5,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "metadata": {"role": u.role, "is_active": u.is_active},
        }
        for u in users
    ]


def search_api_keys(tenant_id: str, query: str, limit: int = 20) -> List[dict]:
    """Search API keys within a tenant."""
    keys = (
        APIKey.objects.filter(tenant_id=tenant_id)
        .filter(Q(name__icontains=query) | Q(key_prefix__icontains=query))
        .order_by("-created_at")[:limit]
    )

    return [
        {
            "type": "api_key",
            "id": str(k.id),
            "title": k.name,
            "subtitle": f"{k.key_prefix}...",
            "relevance": 1.0 if query.lower() in k.name.lower() else 0.5,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "metadata": {"is_active": k.is_active, "usage_count": k.usage_count},
        }
        for k in keys
    ]


def search_webhooks(tenant_id: str, query: str, limit: int = 20) -> List[dict]:
    """Search webhooks within a tenant."""
    webhooks = (
        Webhook.objects.filter(tenant_id=tenant_id)
        .filter(Q(name__icontains=query) | Q(url__icontains=query))
        .order_by("-created_at")[:limit]
    )

    return [
        {
            "type": "webhook",
            "id": str(w.id),
            "title": w.name,
            "subtitle": w.url[:50] + "..." if len(w.url) > 50 else w.url,
            "relevance": 1.0 if query.lower() in w.name.lower() else 0.5,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "metadata": {"is_active": w.is_active, "failure_count": w.failure_count},
        }
        for w in webhooks
    ]


def search_audit_logs(tenant_id: str, query: str, limit: int = 20) -> List[dict]:
    """Search audit logs within a tenant."""
    logs = (
        AuditLog.objects.filter(tenant_id=tenant_id)
        .filter(
            Q(action__icontains=query)
            | Q(resource_type__icontains=query)
            | Q(resource_id__icontains=query)
        )
        .order_by("-timestamp")[:limit]
    )

    return [
        {
            "type": "audit_log",
            "id": str(log.id),
            "title": log.action,
            "subtitle": f"{log.resource_type}: {log.resource_id}",
            "relevance": 1.0 if query.lower() in log.action.lower() else 0.5,
            "created_at": log.timestamp.isoformat() if log.timestamp else None,
            "metadata": {"actor_type": log.actor_type},
        }
        for log in logs
    ]


# =============================================================================
# SEARCH ENDPOINTS - ALL 10 PERSONAS
# =============================================================================


@router.post("/{tenant_id}/search", response=SearchResponse)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def unified_search(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: SearchRequest,
):
    """
    Unified search across all tenant resources.

    🔒 Security: Tenant isolation
    📊 Performance: Parallel search with facets
    """
    import time

    start_time = time.time()

    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    results = []
    facets = {}

    # Determine which types to search
    types = data.types or ["users", "api_keys", "webhooks", "audit_logs"]

    if "users" in types:
        user_results = search_users(str(tenant_id), data.query, data.limit)
        results.extend(user_results)
        facets["users"] = len(user_results)

    if "api_keys" in types:
        key_results = search_api_keys(str(tenant_id), data.query, data.limit)
        results.extend(key_results)
        facets["api_keys"] = len(key_results)

    if "webhooks" in types:
        webhook_results = search_webhooks(str(tenant_id), data.query, data.limit)
        results.extend(webhook_results)
        facets["webhooks"] = len(webhook_results)

    if "audit_logs" in types:
        log_results = search_audit_logs(str(tenant_id), data.query, data.limit)
        results.extend(log_results)
        facets["audit_logs"] = len(log_results)

    # Sort by relevance
    results.sort(key=lambda x: x["relevance"], reverse=True)

    # Apply pagination
    paginated = results[data.offset : data.offset + data.limit]

    search_time = int((time.time() - start_time) * 1000)

    return SearchResponse(
        query=data.query,
        total_results=len(results),
        results=[SearchResultItem(**r) for r in paginated],
        facets=facets,
        search_time_ms=search_time,
    )


@router.get("/{tenant_id}/search/users")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def search_tenant_users(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    q: str,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 20,
):
    """
    Search users with filters.

    🎨 UX: Faceted filtering
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    queryset = TenantUser.objects.filter(tenant_id=tenant_id)

    if q:
        queryset = queryset.filter(Q(email__icontains=q) | Q(display_name__icontains=q))

    if role:
        queryset = queryset.filter(role=role)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    users = queryset.order_by("-created_at")[:limit]

    return {
        "query": q,
        "filters": {"role": role, "is_active": is_active},
        "results": [
            {
                "id": str(u.id),
                "email": u.email,
                "display_name": u.display_name,
                "role": u.role,
                "is_active": u.is_active,
            }
            for u in users
        ],
        "total": queryset.count(),
    }


@router.get("/{tenant_id}/search/audit")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def search_audit_trail(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    q: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
):
    """
    Search audit logs with advanced filters.

    🚨 SRE: Audit trail analysis
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    queryset = AuditLog.objects.filter(tenant_id=tenant_id)

    if q:
        queryset = queryset.filter(
            Q(action__icontains=q)
            | Q(resource_type__icontains=q)
            | Q(resource_id__icontains=q)
        )

    if action:
        queryset = queryset.filter(action__icontains=action)
    if resource_type:
        queryset = queryset.filter(resource_type=resource_type)
    if actor_id:
        queryset = queryset.filter(actor_id=actor_id)
    if start_date:
        queryset = queryset.filter(timestamp__gte=datetime.fromisoformat(start_date))
    if end_date:
        queryset = queryset.filter(timestamp__lte=datetime.fromisoformat(end_date))

    logs = queryset.order_by("-timestamp")[:limit]

    # Get facets
    action_facets = dict(
        queryset.values("action")
        .annotate(count=Count("id"))
        .values_list("action", "count")[:10]
    )

    return {
        "query": q,
        "results": [
            {
                "id": str(log.id),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "actor_id": log.actor_id,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in logs
        ],
        "total": queryset.count(),
        "facets": {"actions": action_facets},
    }


# =============================================================================
# PLATFORM-WIDE SEARCH (Super Admin)
# =============================================================================


@router.post("/platform/search")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def platform_search(
    request: AuthenticatedRequest,
    q: str,
    types: Optional[List[str]] = None,
    limit: int = 50,
):
    """
    Search across all tenants (super admin only).

    🔒 Security: Super admin only
    """
    import time

    start_time = time.time()

    results = []
    types = types or ["tenants", "users"]

    if "tenants" in types:
        tenants = Tenant.objects.filter(
            Q(name__icontains=q) | Q(slug__icontains=q) | Q(admin_email__icontains=q)
        )[:limit]

        for t in tenants:
            results.append(
                {
                    "type": "tenant",
                    "id": str(t.id),
                    "title": t.name,
                    "subtitle": t.slug,
                    "relevance": 1.0 if q.lower() in t.name.lower() else 0.5,
                    "metadata": {
                        "status": t.status,
                        "tier": str(t.tier) if t.tier else None,
                    },
                }
            )

    if "users" in types:
        users = TenantUser.objects.filter(
            Q(email__icontains=q) | Q(display_name__icontains=q)
        ).select_related("tenant")[:limit]

        for u in users:
            results.append(
                {
                    "type": "user",
                    "id": str(u.id),
                    "title": u.email,
                    "subtitle": f"Tenant: {u.tenant.name}",
                    "relevance": 1.0 if q.lower() in u.email.lower() else 0.5,
                    "metadata": {"tenant_id": str(u.tenant_id), "role": u.role},
                }
            )

    # Sort by relevance
    results.sort(key=lambda x: x["relevance"], reverse=True)

    return {
        "query": q,
        "total_results": len(results),
        "results": results[:limit],
        "search_time_ms": int((time.time() - start_time) * 1000),
    }


@router.get("/suggestions/{tenant_id}")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_search_suggestions(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    q: str,
    limit: int = 10,
):
    """
    Get autocomplete suggestions for search.

    🎨 UX: Autocomplete
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    suggestions = []

    # User suggestions
    users = TenantUser.objects.filter(
        tenant_id=tenant_id, email__istartswith=q
    ).values_list("email", flat=True)[: limit // 2]
    suggestions.extend([{"type": "user", "value": u} for u in users])

    # Action suggestions from audit logs
    actions = (
        AuditLog.objects.filter(tenant_id=tenant_id, action__istartswith=q)
        .values_list("action", flat=True)
        .distinct()[: limit // 2]
    )
    suggestions.extend([{"type": "action", "value": a} for a in actions])

    return {"query": q, "suggestions": suggestions[:limit]}
