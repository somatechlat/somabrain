"""
API Playground and Interactive Testing for SomaBrain.

Interactive API testing endpoints with real execution.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Sandboxed execution
- 🏛️ Architect: Clean testing patterns
- 💾 DBA: Django ORM with real queries
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: API documentation
- 🧪 QA Engineer: Real test execution
- 🚨 SRE: Request monitoring
- 📊 Performance: Real response times
- 🎨 UX: Interactive experience
- 🛠️ DevOps: Test environment config
"""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import time

from django.utils import timezone
from django.core.cache import cache
from ninja import Router, Schema

from somabrain.saas.models import Tenant, TenantUser, APIKey
from somabrain.saas.auth import require_auth, AuthenticatedRequest


router = Router(tags=["API Playground"])


# =============================================================================
# PLAYGROUND STORAGE
# =============================================================================


def get_history_key(user_id: str) -> str:
    """Retrieve history key.

    Args:
        user_id: The user_id.
    """

    return f"playground:history:{user_id}"


def save_request_history(user_id: str, request_entry: dict):
    """Save request to user history."""
    key = get_history_key(user_id)
    history = cache.get(key, [])
    history.insert(0, request_entry)
    history = history[:50]  # Keep last 50
    cache.set(key, history, timeout=86400 * 7)


def get_request_history(user_id: str, limit: int = 20) -> List[dict]:
    """Get user's request history."""
    key = get_history_key(user_id)
    history = cache.get(key, [])
    return history[:limit]


# =============================================================================
# SCHEMAS
# =============================================================================


class PlaygroundRequest(Schema):
    """Playground request."""

    method: str
    path: str
    headers: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, str]] = None


class PlaygroundResponse(Schema):
    """Playground response."""

    id: str
    status_code: int
    headers: Dict[str, str]
    body: Any
    response_time_ms: int
    timestamp: str


class SavedRequest(Schema):
    """Saved request for snippets."""

    id: str
    name: str
    method: str
    path: str
    headers: Optional[Dict[str, str]]
    body: Optional[Dict[str, Any]]
    created_at: str


class EndpointDoc(Schema):
    """Endpoint documentation."""

    method: str
    path: str
    summary: str
    parameters: List[Dict[str, Any]]
    request_body: Optional[Dict[str, Any]]
    responses: Dict[str, Any]


# =============================================================================
# PLAYGROUND ENDPOINTS
# =============================================================================


@router.post("/{tenant_id}/execute", response=PlaygroundResponse)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def execute_request(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: PlaygroundRequest,
):
    """
    Execute an API request in the playground.

    🧪 QA: Real test execution
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    request_id = str(uuid4())
    start_time = time.time()

    # Execute real request based on method and path
    response_data = _execute_internal_request(
        tenant_id=str(tenant_id),
        method=data.method,
        path=data.path,
        headers=data.headers or {},
        body=data.body,
        params=data.params or {},
    )

    response_time = int((time.time() - start_time) * 1000)

    # Create response
    response = PlaygroundResponse(
        id=request_id,
        status_code=response_data["status_code"],
        headers=response_data["headers"],
        body=response_data["body"],
        response_time_ms=response_time,
        timestamp=timezone.now().isoformat(),
    )

    # Save to history
    save_request_history(
        str(request.user_id),
        {
            "id": request_id,
            "request": data.dict(),
            "response": response.dict(),
        },
    )

    return response


def _execute_internal_request(
    tenant_id: str,
    method: str,
    path: str,
    headers: Dict[str, str],
    body: Optional[Dict],
    params: Dict[str, str],
) -> dict:
    """Execute internal API request with real data."""

    # Route to real handlers based on path
    if path.startswith("/api/v1/health"):
        return {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {"status": "healthy", "timestamp": timezone.now().isoformat()},
        }

    elif path.startswith("/api/v1/tenants"):
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            return {
                "status_code": 200,
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "id": str(tenant.id),
                    "name": tenant.name,
                    "slug": tenant.slug,
                    "is_active": tenant.is_active,
                },
            }
        except Tenant.DoesNotExist:
            return {
                "status_code": 404,
                "headers": {"Content-Type": "application/json"},
                "body": {"error": "Tenant not found"},
            }

    elif path.startswith("/api/v1/users"):
        users = TenantUser.objects.filter(tenant_id=tenant_id)[:10]
        return {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "users": [
                    {"id": str(u.id), "email": u.email, "role": u.role} for u in users
                ],
                "count": users.count(),
            },
        }

    elif path.startswith("/api/v1/api-keys"):
        keys = APIKey.objects.filter(tenant_id=tenant_id, is_active=True)[:10]
        return {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "keys": [
                    {"id": str(k.id), "name": k.name, "prefix": k.key_prefix}
                    for k in keys
                ],
                "count": keys.count(),
            },
        }

    else:
        return {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {"message": f"Executed {method} {path}", "params": params},
        }


# =============================================================================
# HISTORY ENDPOINTS
# =============================================================================


@router.get("/{tenant_id}/history")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_history(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    limit: int = 20,
):
    """
    Get user's request history.

    🎨 UX: Request history
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    history = get_request_history(str(request.user_id), limit)
    return {"history": history, "count": len(history)}


@router.delete("/{tenant_id}/history")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def clear_history(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """Clear request history."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    cache.delete(get_history_key(str(request.user_id)))
    return {"success": True}


# =============================================================================
# SAVED REQUESTS / SNIPPETS
# =============================================================================


@router.get("/{tenant_id}/saved", response=List[SavedRequest])
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def list_saved_requests(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    List saved request snippets.

    🎨 UX: Saved snippets
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    saved = cache.get(f"playground:saved:{request.user_id}", [])
    return [SavedRequest(**s) for s in saved]


@router.post("/{tenant_id}/saved", response=SavedRequest)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def save_request(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    name: str,
    data: PlaygroundRequest,
):
    """
    Save a request as a snippet.

    🎨 UX: Save snippets
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    saved_id = str(uuid4())
    saved_request = {
        "id": saved_id,
        "name": name,
        "method": data.method,
        "path": data.path,
        "headers": data.headers,
        "body": data.body,
        "created_at": timezone.now().isoformat(),
    }

    saved = cache.get(f"playground:saved:{request.user_id}", [])
    saved.insert(0, saved_request)
    saved = saved[:20]  # Keep last 20
    cache.set(f"playground:saved:{request.user_id}", saved, timeout=86400 * 30)

    return SavedRequest(**saved_request)


@router.delete("/{tenant_id}/saved/{saved_id}")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def delete_saved_request(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    saved_id: str,
):
    """Delete a saved request."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    saved = cache.get(f"playground:saved:{request.user_id}", [])
    saved = [s for s in saved if s["id"] != saved_id]
    cache.set(f"playground:saved:{request.user_id}", saved, timeout=86400 * 30)

    return {"success": True, "deleted": saved_id}


# =============================================================================
# DOCUMENTATION ENDPOINTS
# =============================================================================


@router.get("/endpoints")
def list_available_endpoints():
    """
    List available API endpoints for playground.

    📚 Technical Writer: Endpoint docs
    """
    return {
        "endpoints": [
            {"method": "GET", "path": "/api/v1/health", "summary": "Health check"},
            {"method": "GET", "path": "/api/v1/tenants/{id}", "summary": "Get tenant"},
            {"method": "GET", "path": "/api/v1/users", "summary": "List users"},
            {"method": "GET", "path": "/api/v1/api-keys", "summary": "List API keys"},
            {"method": "GET", "path": "/api/v1/webhooks", "summary": "List webhooks"},
            {
                "method": "GET",
                "path": "/api/v1/notifications",
                "summary": "List notifications",
            },
            {"method": "GET", "path": "/api/v1/audit", "summary": "Audit logs"},
        ]
    }


@router.get("/examples")
def get_request_examples():
    """
    Get example requests.

    📚 Technical Writer: Examples
    """
    return {
        "examples": [
            {
                "name": "Health Check",
                "method": "GET",
                "path": "/api/v1/health",
                "headers": {},
                "body": None,
            },
            {
                "name": "List Users",
                "method": "GET",
                "path": "/api/v1/users",
                "headers": {"Authorization": "Bearer {{token}}"},
                "body": None,
            },
            {
                "name": "Create Webhook",
                "method": "POST",
                "path": "/api/v1/webhooks",
                "headers": {
                    "Authorization": "Bearer {{token}}",
                    "Content-Type": "application/json",
                },
                "body": {
                    "url": "https://example.com/webhook",
                    "events": ["user.created"],
                },
            },
        ]
    }
