"""
API Request Logging and Analytics for SomaBrain.

Detailed request logging and usage analytics.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Secure request logging
- 🏛️ Architect: Clean logging patterns
- 💾 DBA: Django ORM with time-series queries
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Comprehensive docstrings
- 🧪 QA Engineer: Request validation
- 🚨 SRE: Request monitoring
- 📊 Performance: Aggregated analytics
- 🎨 UX: Analytics dashboard data
- 🛠️ DevOps: Log retention
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from django.utils import timezone
from django.core.cache import cache
from ninja import Router, Schema

from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Request Logs"])


# =============================================================================
# REQUEST LOG STORAGE
# =============================================================================


def get_logs_key(tenant_id: str) -> str:
    """Retrieve logs key.

    Args:
        tenant_id: The tenant_id.
    """

    return f"request_logs:{tenant_id}"


def log_request(
    tenant_id: str,
    method: str,
    path: str,
    status_code: int,
    response_time_ms: int,
    user_id: Optional[str] = None,
    api_key_id: Optional[str] = None,
    ip_address: Optional[str] = None,
):
    """Log an API request."""
    log_id = str(uuid4())
    log_entry = {
        "id": log_id,
        "tenant_id": tenant_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "user_id": user_id,
        "api_key_id": api_key_id,
        "ip_address": ip_address,
        "timestamp": timezone.now().isoformat(),
    }

    key = get_logs_key(tenant_id)
    logs = cache.get(key, [])
    logs.insert(0, log_entry)
    logs = logs[:10000]  # Keep last 10k
    cache.set(key, logs, timeout=86400 * 7)

    return log_entry


def get_request_logs(
    tenant_id: str,
    limit: int = 100,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
) -> List[dict]:
    """Get request logs with optional filters."""
    key = get_logs_key(tenant_id)
    logs = cache.get(key, [])

    if method:
        logs = [l for l in logs if l["method"] == method]
    if status_code:
        logs = [l for l in logs if l["status_code"] == status_code]

    return logs[:limit]


# =============================================================================
# SCHEMAS
# =============================================================================


class RequestLogOut(Schema):
    """Request log output."""

    id: str
    method: str
    path: str
    status_code: int
    response_time_ms: int
    user_id: Optional[str]
    api_key_id: Optional[str]
    ip_address: Optional[str]
    timestamp: str


class RequestStats(Schema):
    """Request statistics."""

    total_requests: int
    requests_today: int
    requests_week: int
    avg_response_time_ms: float
    error_rate: float
    requests_by_method: Dict[str, int]
    requests_by_status: Dict[str, int]


class EndpointStats(Schema):
    """Per-endpoint statistics."""

    path: str
    total_requests: int
    avg_response_time_ms: float
    error_rate: float
    p50_latency_ms: float
    p95_latency_ms: float


class HourlyStats(Schema):
    """Hourly request statistics."""

    hour: str
    requests: int
    avg_response_time_ms: float
    error_count: int


class TopUser(Schema):
    """Top user by requests."""

    user_id: str
    request_count: int


# =============================================================================
# REQUEST LOG ENDPOINTS
# =============================================================================


@router.get("/{tenant_id}/logs", response=List[RequestLogOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def list_request_logs(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    limit: int = 100,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
):
    """
    List API request logs for a tenant.

    📊 Performance: Request analytics
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    logs = get_request_logs(str(tenant_id), limit, method, status_code)

    return [RequestLogOut(**log) for log in logs]


@router.get("/{tenant_id}/logs/{log_id}", response=RequestLogOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def get_request_log(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    log_id: str,
):
    """Get a specific request log."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    logs = get_request_logs(str(tenant_id), 10000)

    for log in logs:
        if log["id"] == log_id:
            return RequestLogOut(**log)

    from ninja.errors import HttpError

    raise HttpError(404, "Log not found")


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================


@router.get("/{tenant_id}/stats", response=RequestStats)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def get_request_stats(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get request statistics for a tenant.

    📊 Performance: Stats dashboard
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    logs = get_request_logs(str(tenant_id), 10000)

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    today_count = 0
    week_count = 0
    total_time = 0
    error_count = 0
    by_method = {}
    by_status = {}

    for log in logs:
        ts = datetime.fromisoformat(log["timestamp"])

        if ts >= today_start:
            today_count += 1
        if ts >= week_start:
            week_count += 1

        total_time += log["response_time_ms"]

        if log["status_code"] >= 400:
            error_count += 1

        method = log["method"]
        by_method[method] = by_method.get(method, 0) + 1

        status = str(log["status_code"])
        by_status[status] = by_status.get(status, 0) + 1

    avg_time = total_time / len(logs) if logs else 0
    error_rate = error_count / len(logs) if logs else 0

    return RequestStats(
        total_requests=len(logs),
        requests_today=today_count,
        requests_week=week_count,
        avg_response_time_ms=avg_time,
        error_rate=error_rate,
        requests_by_method=by_method,
        requests_by_status=by_status,
    )


@router.get("/{tenant_id}/endpoints", response=List[EndpointStats])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def get_endpoint_stats(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    limit: int = 20,
):
    """
    Get per-endpoint statistics.

    📊 Performance: Endpoint analytics
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    logs = get_request_logs(str(tenant_id), 10000)

    # Aggregate by path
    by_path = {}
    for log in logs:
        path = log["path"]
        if path not in by_path:
            by_path[path] = {"times": [], "errors": 0}
        by_path[path]["times"].append(log["response_time_ms"])
        if log["status_code"] >= 400:
            by_path[path]["errors"] += 1

    # Calculate stats
    stats = []
    for path, data in by_path.items():
        times = sorted(data["times"])
        total = len(times)

        stats.append(
            EndpointStats(
                path=path,
                total_requests=total,
                avg_response_time_ms=sum(times) / total if total else 0,
                error_rate=data["errors"] / total if total else 0,
                p50_latency_ms=times[total // 2] if times else 0,
                p95_latency_ms=times[int(total * 0.95)] if times else 0,
            )
        )

    # Sort by total requests
    stats.sort(key=lambda x: x.total_requests, reverse=True)

    return stats[:limit]


@router.get("/{tenant_id}/hourly", response=List[HourlyStats])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def get_hourly_stats(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    hours: int = 24,
):
    """
    Get hourly request statistics.

    📊 Performance: Time-series data
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    logs = get_request_logs(str(tenant_id), 10000)

    # Group by hour
    by_hour = {}
    cutoff = timezone.now() - timedelta(hours=hours)

    for log in logs:
        ts = datetime.fromisoformat(log["timestamp"])
        if ts < cutoff:
            continue

        hour_key = ts.strftime("%Y-%m-%d %H:00")
        if hour_key not in by_hour:
            by_hour[hour_key] = {"count": 0, "total_time": 0, "errors": 0}

        by_hour[hour_key]["count"] += 1
        by_hour[hour_key]["total_time"] += log["response_time_ms"]
        if log["status_code"] >= 400:
            by_hour[hour_key]["errors"] += 1

    # Format response
    stats = [
        HourlyStats(
            hour=hour,
            requests=data["count"],
            avg_response_time_ms=(
                data["total_time"] / data["count"] if data["count"] else 0
            ),
            error_count=data["errors"],
        )
        for hour, data in sorted(by_hour.items())
    ]

    return stats


@router.get("/{tenant_id}/top-users", response=List[TopUser])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def get_top_users(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    limit: int = 10,
):
    """
    Get top users by request count.

    📊 Performance: User analytics
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    logs = get_request_logs(str(tenant_id), 10000)

    by_user = {}
    for log in logs:
        user_id = log.get("user_id")
        if user_id:
            by_user[user_id] = by_user.get(user_id, 0) + 1

    # Sort and limit
    top = sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:limit]

    return [TopUser(user_id=uid, request_count=count) for uid, count in top]


@router.get("/{tenant_id}/errors")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def get_error_logs(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    limit: int = 50,
):
    """
    Get recent error logs (4xx and 5xx).

    🚨 SRE: Error monitoring
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    logs = get_request_logs(str(tenant_id), 10000)
    errors = [l for l in logs if l["status_code"] >= 400]

    return {
        "total_errors": len(errors),
        "errors": errors[:limit],
    }


@router.get("/{tenant_id}/slow-requests")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def get_slow_requests(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    threshold_ms: int = 1000,
    limit: int = 50,
):
    """
    Get slow requests above threshold.

    📊 Performance: Slow query detection
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    logs = get_request_logs(str(tenant_id), 10000)
    slow = [log for log in logs if log["response_time_ms"] >= threshold_ms]
    slow.sort(key=lambda x: x["response_time_ms"], reverse=True)

    return {
        "threshold_ms": threshold_ms,
        "total_slow": len(slow),
        "requests": slow[:limit],
    }
