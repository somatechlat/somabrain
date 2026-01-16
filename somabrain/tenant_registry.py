"""
Centralized Tenant Registry Service for SomaBrain

Implements a perfect, centralized dynamic tenant management system with:
- UUID-based tenant generation
- Persistent tenant registry
- Centralized configuration management
- Tenant lifecycle management
- Audit logging and metrics
- Dynamic exempt tenant management
- Tenant validation and normalization
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Union

import redis.asyncio as redis
from redis.exceptions import RedisError

from somabrain.tenant_validation import normalize_tenant_id, validate_tenant_id
from somabrain.tenant_types import TenantTier, TenantStatus, TenantMetadata

logger = logging.getLogger(__name__)


class TenantRegistry:
    """Centralized tenant management service with perfect architecture."""

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize the instance."""

        self.redis_url = redis_url or "redis://localhost:6379/0"
        self._redis: Optional[redis.Redis] = None
        self._tenant_cache: Dict[str, TenantMetadata] = {}
        self._exempt_cache: Set[str] = set()
        self._system_tenant_ids: Dict[str, str] = {}
        self._initialized = False
        self._cache_ttl = 300  # 5 minutes

    async def initialize(self) -> None:
        """Initialize tenant registry with system tenants.

        The original implementation set ``self._initialized`` *after* creating
        system tenants.  ``_create_system_tenants`` invokes ``register_tenant``
        which itself called ``initialize`` when ``self._initialized`` was
        ``False``.  This resulted in infinite recursion and the observed
        ``maximum recursion depth exceeded`` errors.

        The fix marks the registry as initialized **before** creating system
        tenants.  Subsequent calls to ``register_tenant`` will see the flag set
        and will not re‑enter ``initialize``.  All other logic remains
        unchanged.
        """
        if self._initialized:
            return

        try:
            # Initialise Redis connection first.
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()

            # Mark as initialised early to avoid recursive calls from
            # ``register_tenant`` during system‑tenant creation.
            self._initialized = True

            # Create system tenants with proper UUIDs.
            await self._create_system_tenants()

            # Load any existing tenants from storage.
            await self._load_all_tenants()

            logger.info("Tenant registry initialized successfully")
        except RedisError as e:
            logger.error("Failed to initialize tenant registry: %s", e)
            raise

    async def _create_system_tenants(self) -> None:
        """Create essential system tenants."""
        system_tenants = [
            {
                "tenant_id": self._generate_system_tenant_id("agent_zero"),
                "display_name": "System Agent",
                "tier": TenantTier.SYSTEM,
                "is_exempt": True,
                "exempt_reason": "Internal system agent with unlimited access",
            },
            {
                "tenant_id": self._generate_system_tenant_id("public"),
                "display_name": "Public Access",
                "tier": TenantTier.PUBLIC,
                "is_exempt": False,
            },
            {
                "tenant_id": self._generate_system_tenant_id("sandbox"),
                "display_name": "Development Sandbox",
                "tier": TenantTier.SANDBOX,
                "is_exempt": False,
            },
        ]

        for tenant_config in system_tenants:
            try:
                await self.register_tenant(**tenant_config)
            except ValueError as e:
                # Tenant might already exist, which is fine
                logger.debug("System tenant creation skipped: %s", e)

    def _generate_system_tenant_id(self, prefix: str) -> str:
        """Generate UUID-based tenant ID with system prefix."""
        uuid_suffix = uuid.uuid4().hex[:12]
        return f"{prefix}_{uuid_suffix}"

    def _generate_dynamic_tenant_id(self) -> str:
        """Generate dynamic UUID-based tenant ID."""
        return f"tenant_{uuid.uuid4().hex}"

    async def register_tenant(
        self,
        tenant_id: Optional[str] = None,
        display_name: str = "Unknown",
        tier: Union[TenantTier, str] = TenantTier.ENTERPRISE,
        is_exempt: bool = False,
        exempt_reason: Optional[str] = None,
        created_by: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ) -> str:
        """Register a new tenant with validation and audit logging."""

        if not self._initialized:
            await self.initialize()

        # Generate tenant ID if not provided
        if not tenant_id:
            tenant_id = self._generate_dynamic_tenant_id()

        # Convert tier to enum if string
        if isinstance(tier, str):
            tier = TenantTier(tier.lower())

        # Validate tenant ID format
        if not self._validate_tenant_id(tenant_id):
            raise ValueError(f"Invalid tenant ID format: {tenant_id}")

        # Check if tenant already exists
        if await self.tenant_exists(tenant_id):
            raise ValueError(f"Tenant already exists: {tenant_id}")

        # Create tenant metadata
        metadata = TenantMetadata(
            tenant_id=tenant_id,
            display_name=display_name,
            created_at=datetime.utcnow(),
            status=TenantStatus.ACTIVE,
            tier=tier,
            config=config or {},
            is_exempt=is_exempt,
            exempt_reason=exempt_reason,
            last_activity=datetime.utcnow(),
            created_by=created_by,
            expires_at=expires_at,
        )

        # Store tenant metadata
        await self._store_tenant_metadata(metadata)

        # Update caches
        self._tenant_cache[tenant_id] = metadata
        if is_exempt:
            self._exempt_cache.add(tenant_id)
        if tier == TenantTier.SYSTEM:
            self._system_tenant_ids[display_name.lower()] = tenant_id

        # Audit log
        await self._audit_log(
            "tenant_registered",
            tenant_id,
            {
                "display_name": display_name,
                "tier": tier.value,
                "is_exempt": is_exempt,
                "created_by": created_by,
            },
        )

        logger.info("Tenant registered: %s (%s)", tenant_id, display_name)
        return tenant_id

    async def get_tenant(self, tenant_id: str) -> Optional[TenantMetadata]:
        """Get tenant metadata with caching."""
        if not self._initialized:
            await self.initialize()

        # Normalize tenant ID
        normalized_id = self._normalize_tenant_id(tenant_id)

        # Check cache first
        if normalized_id in self._tenant_cache:
            return self._tenant_cache[normalized_id]

        # Load from persistent storage
        metadata = await self._load_tenant_metadata(normalized_id)
        if metadata:
            self._tenant_cache[normalized_id] = metadata

        return metadata

    async def tenant_exists(self, tenant_id: str) -> bool:
        """Check if tenant exists with normalized comparison."""
        normalized_id = self._normalize_tenant_id(tenant_id)
        return await self.get_tenant(normalized_id) is not None

    def is_exempt(self, tenant_id: str) -> bool:
        """Check if tenant is exempt with cached performance."""
        normalized_id = self._normalize_tenant_id(tenant_id)
        return normalized_id in self._exempt_cache

    async def get_system_tenant_id(self, name: str) -> Optional[str]:
        """Get system tenant ID by name (e.g., 'agent_zero')."""
        return self._system_tenant_ids.get(name.lower())

    async def get_all_tenants(self, tier: Optional[TenantTier] = None) -> List[TenantMetadata]:
        """Get all tenants with optional tier filtering."""
        if not self._initialized:
            await self.initialize()

        try:
            # Get all tenant keys
            pattern = "tenant:*"
            keys = await self._redis.keys(pattern)

            tenants = []
            for key in keys:
                tenant_id = key.replace("tenant:", "")
                metadata = await self.get_tenant(tenant_id)
                if metadata and (tier is None or metadata.tier == tier):
                    tenants.append(metadata)

            return tenants

        except RedisError as e:
            logger.error("Failed to get all tenants: %s", e)
            return []

    async def update_tenant_status(self, tenant_id: str, status: Union[TenantStatus, str]) -> bool:
        """Update tenant status with validation."""
        if not self._initialized:
            await self.initialize()

        # Convert status to enum if string
        if isinstance(status, str):
            status = TenantStatus(status.lower())

        # Get current metadata
        metadata = await self.get_tenant(tenant_id)
        if not metadata:
            return False

        # Update status
        metadata.status = status

        # Store updated metadata
        await self._store_tenant_metadata(metadata)
        self._tenant_cache[tenant_id] = metadata

        # Audit log
        await self._audit_log("tenant_status_updated", tenant_id, {"status": status.value})

        logger.info("Tenant status updated: %s -> %s", tenant_id, status.value)
        return True

    async def delete_tenant(self, tenant_id: str) -> bool:
        """Delete tenant with cleanup and audit logging."""
        if not self._initialized:
            await self.initialize()

        normalized_id = self._normalize_tenant_id(tenant_id)

        # Check if tenant exists
        metadata = await self.get_tenant(normalized_id)
        if not metadata:
            return False

        # Cannot delete system tenants
        if metadata.tier == TenantTier.SYSTEM:
            logger.warning("Cannot delete system tenant: %s", normalized_id)
            return False

        try:
            # Delete from Redis
            await self._redis.delete(f"tenant:{normalized_id}")

            # Remove from caches
            self._tenant_cache.pop(normalized_id, None)
            self._exempt_cache.discard(normalized_id)

            # Audit log
            await self._audit_log(
                "tenant_deleted",
                normalized_id,
                {"display_name": metadata.display_name, "tier": metadata.tier.value},
            )

            logger.info("Tenant deleted: %s", normalized_id)
            return True

        except RedisError as e:
            logger.error("Failed to delete tenant %s: %s", normalized_id, e)
            return False

    async def update_tenant_activity(self, tenant_id: str) -> None:
        """Update tenant last activity timestamp."""
        if not self._initialized:
            await self.initialize()

        normalized_id = self._normalize_tenant_id(tenant_id)
        metadata = await self.get_tenant(normalized_id)
        if metadata:
            metadata.last_activity = datetime.utcnow()
            await self._store_tenant_metadata(metadata)
            self._tenant_cache[normalized_id] = metadata

    def _normalize_tenant_id(self, tenant_id: str) -> str:
        """Normalize tenant ID for consistent comparison."""
        return normalize_tenant_id(tenant_id)

    def _validate_tenant_id(self, tenant_id: str) -> bool:
        """Validate tenant ID format and security."""
        return validate_tenant_id(tenant_id)

    async def _store_tenant_metadata(self, metadata: TenantMetadata) -> None:
        """Store tenant metadata in Redis."""
        if not self._redis:
            raise RuntimeError("Tenant registry not initialized")

        try:
            key = f"tenant:{metadata.tenant_id}"
            data = metadata.to_dict()

            # Convert datetime objects to ISO strings
            data["created_at"] = metadata.created_at.isoformat()
            data["last_activity"] = metadata.last_activity.isoformat()
            if metadata.expires_at:
                data["expires_at"] = metadata.expires_at.isoformat()

            # Store with TTL for temporary tenants
            if metadata.expires_at:
                ttl = int((metadata.expires_at - datetime.utcnow()).total_seconds())
                if ttl > 0:
                    await self._redis.setex(key, ttl, json.dumps(data))
                else:
                    await self._redis.set(key, json.dumps(data))
            else:
                await self._redis.set(key, json.dumps(data))

        except RedisError as e:
            logger.error("Failed to store tenant metadata: %s", e)
            raise

    async def _load_tenant_metadata(self, tenant_id: str) -> Optional[TenantMetadata]:
        """Load tenant metadata from Redis."""
        if not self._redis:
            raise RuntimeError("Tenant registry not initialized")

        try:
            key = f"tenant:{tenant_id}"
            data = await self._redis.get(key)

            if data:
                return TenantMetadata.from_dict(json.loads(data))

            return None

        except RedisError as e:
            logger.error("Failed to load tenant metadata: %s", e)
            return None

    async def _load_all_tenants(self) -> None:
        """Load all tenants from Redis into cache."""
        if not self._redis:
            return

        try:
            # Get all tenant keys
            pattern = "tenant:*"
            keys = await self._redis.keys(pattern)

            # Load each tenant
            for key in keys:
                tenant_id = key.replace("tenant:", "")
                metadata = await self._load_tenant_metadata(tenant_id)
                if metadata:
                    self._tenant_cache[tenant_id] = metadata
                    if metadata.is_exempt:
                        self._exempt_cache.add(tenant_id)
                    if metadata.tier == TenantTier.SYSTEM:
                        self._system_tenant_ids[metadata.display_name.lower()] = tenant_id

            logger.info("Loaded %d tenants from storage", len(self._tenant_cache))

        except RedisError as e:
            logger.error("Failed to load tenants from storage: %s", e)

    async def _audit_log(self, action: str, tenant_id: str, details: Dict[str, Any]) -> None:
        """Audit log tenant operations."""
        if not self._redis:
            return

        try:
            audit_key = f"audit:tenant:{datetime.utcnow().strftime('%Y-%m-%d')}"
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "tenant_id": tenant_id,
                "details": details,
            }

            # Store audit entry
            await self._redis.lpush(audit_key, json.dumps(audit_entry))

            # Trim audit log to last 1000 entries
            await self._redis.ltrim(audit_key, 0, 999)

        except RedisError as e:
            logger.error("Failed to write audit log: %s", e)

    async def get_tenant_stats(self) -> Dict[str, Any]:
        """Get tenant registry statistics."""
        if not self._initialized:
            await self.initialize()

        stats = {
            "total_tenants": len(self._tenant_cache),
            "exempt_tenants": len(self._exempt_cache),
            "system_tenants": len(self._system_tenant_ids),
            "tenants_by_tier": {},
            "tenants_by_status": {},
        }

        # Count by tier and status
        for metadata in self._tenant_cache.values():
            tier = metadata.tier.value
            status = metadata.status.value

            stats["tenants_by_tier"][tier] = stats["tenants_by_tier"].get(tier, 0) + 1
            stats["tenants_by_status"][status] = stats["tenants_by_status"].get(status, 0) + 1

        return stats

    async def cleanup_expired_tenants(self) -> int:
        """Clean up expired temporary tenants."""
        if not self._initialized:
            await self.initialize()

        cleaned_count = 0
        current_time = datetime.utcnow()

        for tenant_id, metadata in list(self._tenant_cache.items()):
            if (
                metadata.expires_at
                and metadata.expires_at <= current_time
                and metadata.tier != TenantTier.SYSTEM
            ):
                if await self.delete_tenant(tenant_id):
                    cleaned_count += 1

        if cleaned_count > 0:
            logger.info("Cleaned up %d expired tenants", cleaned_count)

        return cleaned_count

    async def close(self) -> None:
        """Close the tenant registry."""
        if self._redis:
            await self._redis.close()
            self._redis = None

        self._tenant_cache.clear()
        self._exempt_cache.clear()
        self._system_tenant_ids.clear()
        self._initialized = False

        logger.info("Tenant registry closed")
