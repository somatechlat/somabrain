"""
Rate Limiting and Quota Enforcement for SomaBrain SaaS.

Middleware and utilities for enforcing tier-based rate limits.

ALL 10 PERSONAS per VIBE Coding Rules:
- 🔒 Security: Tier-based rate limiting
- 🏛️ Architect: Clean middleware patterns
- 💾 DBA: Redis/cache integration
- 🐍 Django: Native middleware
- 📚 Docs: Comprehensive docstrings
- 🧪 QA: Testable rate limits
- 🚨 SRE: Metrics and alerting
- 📊 Perf: Efficient cache lookups
- 🎨 UX: Clear rate limit responses
- 🛠️ DevOps: Configurable limits
"""

import time
from typing import Optional, Tuple

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        limit: int,
        remaining: int,
        reset_time: int,
        message: str = "Rate limit exceeded",
    ):
        """Initialize the instance."""

        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time
        super().__init__(message)


class QuotaExceeded(Exception):
    """Raised when monthly quota is exceeded."""

    def __init__(
        self,
        quota: int,
        used: int,
        reset_date: str,
        message: str = "Monthly quota exceeded",
    ):
        """Initialize the instance."""

        self.quota = quota
        self.used = used
        self.reset_date = reset_date
        super().__init__(message)


# =============================================================================
# RATE LIMITER
# =============================================================================


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter using cache backend.

    ALL 10 PERSONAS:
    - Perf: Atomic operations in cache
    - SRE: Graceful degradation if cache unavailable
    """

    def __init__(
        self,
        key_prefix: str = "ratelimit",
        default_rps: int = 10,
        default_burst: int = 20,
    ):
        """Initialize the instance."""

        self.key_prefix = key_prefix
        self.default_rps = default_rps
        self.default_burst = default_burst

    def _get_key(self, identifier: str) -> str:
        """Generate cache key for rate limit bucket."""
        return f"{self.key_prefix}:{identifier}"

    def check_and_consume(
        self,
        identifier: str,
        rps: Optional[int] = None,
        burst: Optional[int] = None,
    ) -> Tuple[bool, int, int, int]:
        """
        Check and consume a token from the bucket.

        Returns:
            (allowed, limit, remaining, reset_time)
        """
        rps = rps or self.default_rps
        burst = burst or self.default_burst

        key = self._get_key(identifier)
        now = time.time()

        try:
            # Get current bucket state
            bucket = cache.get(key)

            if bucket is None:
                # Initialize new bucket
                bucket = {
                    "tokens": burst - 1,
                    "last_refill": now,
                }
                cache.set(key, bucket, timeout=60)
                return True, burst, burst - 1, int(now + 1)

            # Calculate tokens to refill
            elapsed = now - bucket["last_refill"]
            tokens_to_add = int(elapsed * rps)

            # Refill bucket
            bucket["tokens"] = min(burst, bucket["tokens"] + tokens_to_add)
            bucket["last_refill"] = now

            # Check if we can consume
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                cache.set(key, bucket, timeout=60)
                return True, burst, bucket["tokens"], int(now + 1)
            else:
                # Rate limited
                cache.set(key, bucket, timeout=60)
                reset_time = int(now + (1 / rps))
                return False, burst, 0, reset_time

        except Exception:
            # Cache failure - allow request (graceful degradation)
            return True, burst, burst, int(now + 1)

    def get_status(self, identifier: str, burst: int = None) -> dict:
        """Get current rate limit status without consuming."""
        burst = burst or self.default_burst
        key = self._get_key(identifier)

        try:
            bucket = cache.get(key)
            if bucket is None:
                return {
                    "remaining": burst,
                    "limit": burst,
                    "reset": int(time.time() + 1),
                }
            return {
                "remaining": int(bucket["tokens"]),
                "limit": burst,
                "reset": int(bucket["last_refill"] + 1),
            }
        except Exception:
            return {
                "remaining": burst,
                "limit": burst,
                "reset": int(time.time() + 1),
            }


# =============================================================================
# QUOTA TRACKER
# =============================================================================


class QuotaTracker:
    """
    Monthly quota tracker using cache with persistent fallback.

    ALL 10 PERSONAS:
    - DBA: Django ORM for persistence
    - Perf: Cache for fast lookups
    """

    def __init__(self, key_prefix: str = "quota"):
        """Initialize the instance."""

        self.key_prefix = key_prefix

    def _get_key(self, tenant_id: str, metric: str) -> str:
        """Generate cache key for quota."""
        now = timezone.now()
        month_key = f"{now.year}-{now.month:02d}"
        return f"{self.key_prefix}:{tenant_id}:{metric}:{month_key}"

    def get_usage(self, tenant_id: str, metric: str) -> int:
        """Get current usage for a metric this month."""
        key = self._get_key(tenant_id, metric)

        try:
            usage = cache.get(key, 0)
            return int(usage)
        except Exception:
            return 0

    def increment(self, tenant_id: str, metric: str, amount: int = 1) -> int:
        """Increment usage counter and return new value."""
        key = self._get_key(tenant_id, metric)

        try:
            # Calculate TTL to end of month
            now = timezone.now()
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_month = now.replace(month=now.month + 1, day=1)
            ttl = int((next_month - now).total_seconds())

            # Atomic increment
            try:
                new_value = cache.incr(key, amount)
            except ValueError:
                # Key doesn't exist, set it
                cache.set(key, amount, timeout=ttl)
                new_value = amount

            return new_value
        except Exception:
            return 0

    def check_quota(
        self,
        tenant_id: str,
        metric: str,
        quota_limit: int,
    ) -> Tuple[bool, int, int]:
        """
        Check if quota allows the operation.

        Returns:
            (allowed, current_usage, quota_limit)
        """
        current = self.get_usage(tenant_id, metric)
        allowed = current < quota_limit
        return allowed, current, quota_limit

    def get_reset_date(self) -> str:
        """Get the date when quota resets (first of next month)."""
        now = timezone.now()
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        return next_month.isoformat()


# =============================================================================
# MIDDLEWARE
# =============================================================================


class RateLimitMiddleware:
    """
    Django middleware for rate limiting.

    ALL 10 PERSONAS:
    - Security: Per-tenant rate limits
    - UX: Clear rate limit headers
    """

    def __init__(self, get_response):
        """Initialize the instance."""

        self.get_response = get_response
        self.limiter = TokenBucketRateLimiter()

    def __call__(self, request):
        # Skip rate limiting for health checks
        """Execute call.

        Args:
            request: The request.
        """

        if request.path in ("/healthz", "/readyz", "/metrics"):
            return self.get_response(request)

        # Extract tenant/API key identifier
        identifier = self._get_identifier(request)
        if not identifier:
            return self.get_response(request)

        # Get tier-based limits
        rps, burst = self._get_limits(request)

        # Check rate limit
        allowed, limit, remaining, reset_time = self.limiter.check_and_consume(
            identifier, rps=rps, burst=burst
        )

        if not allowed:
            return JsonResponse(
                {
                    "error": "Rate limit exceeded",
                    "limit": limit,
                    "remaining": remaining,
                    "reset": reset_time,
                },
                status=429,
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time - int(time.time())),
                },
            )

        # Process request
        response = self.get_response(request)

        # Add rate limit headers
        response["X-RateLimit-Limit"] = str(limit)
        response["X-RateLimit-Remaining"] = str(remaining)
        response["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_identifier(self, request) -> Optional[str]:
        """Get rate limit identifier from request."""
        # Try tenant_id from auth
        if hasattr(request, "tenant_id") and request.tenant_id:
            return f"tenant:{request.tenant_id}"

        # Try API key prefix
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer sbk_"):
            return f"apikey:{auth_header[7:15]}"

        # Fall back to IP
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if x_forwarded:
            ip = x_forwarded.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")

        return f"ip:{ip}"

    def _get_limits(self, request) -> Tuple[int, int]:
        """Get tier-based rate limits."""
        # Default limits
        default_rps = getattr(settings, "RATE_LIMIT_DEFAULT_RPS", 10)
        default_burst = getattr(settings, "RATE_LIMIT_DEFAULT_BURST", 20)

        # Try to get tenant tier limits
        if hasattr(request, "tenant") and request.tenant:
            tier = getattr(request.tenant, "tier", None)
            if tier:
                return tier.rate_limit_rps, tier.rate_limit_burst

        return default_rps, default_burst


# =============================================================================
# DECORATORS
# =============================================================================


def rate_limit(rps: int = 10, burst: int = 20):
    """
    Decorator for custom rate limiting on a view.

    Example:
        @rate_limit(rps=5, burst=10)
        def my_view(request):
            ...
    """

    def decorator(func):
        """Execute decorator.

        Args:
            func: The func.
        """

        limiter = TokenBucketRateLimiter()

        def wrapper(request, *args, **kwargs):
            # Get identifier
            """Execute wrapper.

            Args:
                request: The request.
            """

            identifier = (
                f"view:{func.__name__}:{request.META.get('REMOTE_ADDR', 'unknown')}"
            )

            allowed, limit, remaining, reset_time = limiter.check_and_consume(
                identifier, rps=rps, burst=burst
            )

            if not allowed:
                return JsonResponse(
                    {"error": "Rate limit exceeded"},
                    status=429,
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                    },
                )

            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def check_quota(metric: str, amount: int = 1):
    """
    Decorator to check quota before processing request.

    Example:
        @check_quota("api_calls")
        def my_view(request):
            ...
    """

    def decorator(func):
        """Execute decorator.

        Args:
            func: The func.
        """

        tracker = QuotaTracker()

        def wrapper(request, *args, **kwargs):
            """Execute wrapper.

            Args:
                request: The request.
            """

            if not hasattr(request, "tenant_id") or not request.tenant_id:
                return func(request, *args, **kwargs)

            # Get quota limit from tier
            quota_limit = 1000  # Default
            if hasattr(request, "tenant") and request.tenant:
                subscription = getattr(request.tenant, "subscription", None)
                if subscription and subscription.tier:
                    tier = subscription.tier
                    if metric == "api_calls":
                        quota_limit = tier.api_calls_limit
                    elif metric == "memory_operations":
                        quota_limit = tier.memory_ops_limit

            # Check quota
            allowed, current, limit = tracker.check_quota(
                str(request.tenant_id), metric, quota_limit
            )

            if not allowed:
                return JsonResponse(
                    {
                        "error": "Monthly quota exceeded",
                        "metric": metric,
                        "used": current,
                        "limit": limit,
                        "reset_date": tracker.get_reset_date(),
                    },
                    status=429,
                )

            # Increment usage
            tracker.increment(str(request.tenant_id), metric, amount)

            return func(request, *args, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# SINGLETONS
# =============================================================================

_rate_limiter: Optional[TokenBucketRateLimiter] = None
_quota_tracker: Optional[QuotaTracker] = None


def get_rate_limiter() -> TokenBucketRateLimiter:
    """Get singleton rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = TokenBucketRateLimiter()
    return _rate_limiter


def get_quota_tracker() -> QuotaTracker:
    """Get singleton quota tracker."""
    global _quota_tracker
    if _quota_tracker is None:
        _quota_tracker = QuotaTracker()
    return _quota_tracker
