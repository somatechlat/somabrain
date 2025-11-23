"""
Tenant Manager Service for SomaBrain

High-level tenant management interface that integrates with the TenantRegistry
and provides centralized tenant operations for all SomaBrain components.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from fastapi import Request, HTTPException

from .tenant_registry import TenantRegistry, TenantMetadata, TenantTier, TenantStatus

# Import get_config for legacy configuration access
from .config import get_config

# Unified Settings instance (still used elsewhere)
from common.config.settings import settings

logger = logging.getLogger(__name__)


class TenantManager:
    """Centralized tenant management for all SomaBrain operations."""

    def __init__(self, tenant_registry: TenantRegistry):
        self.registry = tenant_registry
        self._default_tenant_id: Optional[str] = None
        self._system_tenant_ids: Dict[str, str] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize tenant manager with system tenants."""
        if self._initialized:
            return

        # Ensure registry is initialized
        await self.registry.initialize()

        # Set default tenant
        public_tenant = await self._get_tenant_by_tier(TenantTier.PUBLIC)
        if public_tenant:
            self._default_tenant_id = public_tenant.tenant_id
            logger.info("Default tenant set to: %s", public_tenant.tenant_id)
        else:
            logger.warning("No public tenant found, will create on demand")

        # Cache system tenant IDs
        system_tenants = await self.registry.get_all_tenants(tier=TenantTier.SYSTEM)
        for tenant in system_tenants:
            self._system_tenant_ids[tenant.display_name.lower()] = tenant.tenant_id

        self._initialized = True
        logger.info(
            "Tenant manager initialized with %d system tenants", len(system_tenants)
        )

    async def resolve_tenant_from_request(self, request: Request) -> str:
        """Resolve tenant ID from HTTP request with fallback chain."""

        if not self._initialized:
            await self.initialize()

        # Priority 1: X-Tenant-ID header
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id and await self.registry.tenant_exists(tenant_id):
            await self.registry.update_tenant_activity(tenant_id)
            return tenant_id

        # Priority 2: Bearer token hash
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            token_hash = self._hash_token(token)
            if await self.registry.tenant_exists(token_hash):
                await self.registry.update_tenant_activity(token_hash)
                return token_hash

        # Priority 3: Default tenant (must be explicitly configured)
        if self._default_tenant_id:
            await self.registry.update_tenant_activity(self._default_tenant_id)
            return self._default_tenant_id

        # Explicit opt-in only: anonymous/temp tenants allowed?
        if not getattr(settings, "allow_anonymous_tenants", False):
            raise HTTPException(
                status_code=401,
                detail="Anonymous tenant access is disabled. Configure a default tenant or enable SOMABRAIN_ALLOW_ANONYMOUS_TENANTS=1 explicitly.",
            )

        # Fallback: Create temporary tenant (only when allowed)
        temp_tenant_id = await self.create_temporary_tenant()
        await self.registry.update_tenant_activity(temp_tenant_id)
        return temp_tenant_id

    def _hash_token(self, token: str) -> str:
        """Generate consistent hash from bearer token."""
        return f"token_{hashlib.sha256(token.encode()).hexdigest()[:16]}"

    async def create_temporary_tenant(self) -> str:
        """Create temporary tenant for anonymous access."""
        config = settings

        # Parse expiry time from config
        expiry_hours = 24  # Default
        if hasattr(config, "tenant_temporary_expiry"):
            expiry_str = config.tenant_temporary_expiry
            if expiry_str.endswith("h"):
                expiry_hours = int(expiry_str[:-1])
            elif expiry_str.endswith("d"):
                expiry_hours = int(expiry_str[:-1]) * 24

        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)

        return await self.registry.register_tenant(
            display_name="Temporary Access",
            tier=TenantTier.PUBLIC,
            config={
                "temporary": True,
                "expires_in": f"{expiry_hours}h",
                "auto_created": True,
            },
            expires_at=expires_at,
        )

    async def get_system_tenant_id(self, name: str) -> Optional[str]:
        """Get system tenant ID by name (e.g., 'agent_zero')."""
        if not self._initialized:
            await self.initialize()

        return self._system_tenant_ids.get(name.lower())

    async def is_exempt_tenant(self, tenant_id: str) -> bool:
        """Check if tenant is exempt from quotas."""
        if not self._initialized:
            await self.initialize()

        return self.registry.is_exempt(tenant_id)

    async def get_tenant_config(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant-specific configuration."""
        metadata = await self.registry.get_tenant(tenant_id)
        if metadata:
            return metadata.config
        return {}

    async def get_tenant_metadata(self, tenant_id: str) -> Optional[TenantMetadata]:
        """Get complete tenant metadata."""
        if not self._initialized:
            await self.initialize()

        return await self.registry.get_tenant(tenant_id)

    async def create_tenant(
        self,
        display_name: str,
        tier: Union[TenantTier, str] = TenantTier.ENTERPRISE,
        is_exempt: bool = False,
        exempt_reason: Optional[str] = None,
        created_by: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ) -> str:
        """Create a new tenant with validation."""
        if not self._initialized:
            await self.initialize()

        # Convert tier to enum if string
        if isinstance(tier, str):
            tier = TenantTier(tier.lower())

        # Validate tenant creation permissions
        if tier == TenantTier.SYSTEM and created_by != "system":
            raise ValueError("Only system can create system tenants")

        return await self.registry.register_tenant(
            display_name=display_name,
            tier=tier,
            is_exempt=is_exempt,
            exempt_reason=exempt_reason,
            created_by=created_by,
            config=config or {},
            expires_at=expires_at,
        )

    async def update_tenant_config(
        self, tenant_id: str, config: Dict[str, Any]
    ) -> bool:
        """Update tenant-specific configuration."""
        if not self._initialized:
            await self.initialize()

        metadata = await self.registry.get_tenant(tenant_id)
        if not metadata:
            return False

        # Merge new config with existing config
        merged_config = {**metadata.config, **config}
        metadata.config = merged_config

        # Store updated metadata
        await self.registry._store_tenant_metadata(metadata)

        # Update cache
        self.registry._tenant_cache[tenant_id] = metadata

        return True

    async def suspend_tenant(
        self, tenant_id: str, reason: str = "Administrative action"
    ) -> bool:
        """Suspend a tenant."""
        return await self.registry.update_tenant_status(
            tenant_id, TenantStatus.SUSPENDED
        )

    async def activate_tenant(self, tenant_id: str) -> bool:
        """Activate a suspended tenant."""
        return await self.registry.update_tenant_status(tenant_id, TenantStatus.ACTIVE)

    async def disable_tenant(
        self, tenant_id: str, reason: str = "Violation of terms"
    ) -> bool:
        """Disable a tenant permanently."""
        metadata = await self.registry.get_tenant(tenant_id)
        if metadata and metadata.tier == TenantTier.SYSTEM:
            logger.warning("Cannot disable system tenant: %s", tenant_id)
            return False

        return await self.registry.update_tenant_status(
            tenant_id, TenantStatus.DISABLED
        )

    async def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant."""
        if not self._initialized:
            await self.initialize()

        return await self.registry.delete_tenant(tenant_id)

    async def list_tenants(
        self,
        tier: Optional[Union[TenantTier, str]] = None,
        status: Optional[Union[TenantStatus, str]] = None,
        exempt_only: bool = False,
    ) -> List[TenantMetadata]:
        """List tenants with optional filtering."""
        if not self._initialized:
            await self.initialize()

        # Convert tier to enum if string
        if isinstance(tier, str):
            tier = TenantTier(tier.lower())

        # Get all tenants or filter by tier
        if tier:
            tenants = await self.registry.get_all_tenants(tier)
        else:
            tenants = await self.registry.get_all_tenants()

        # Apply additional filters
        filtered_tenants = []
        for tenant in tenants:
            if status and tenant.status != (
                TenantStatus(status) if isinstance(status, str) else status
            ):
                continue

            if exempt_only and not tenant.is_exempt:
                continue

            filtered_tenants.append(tenant)

        return filtered_tenants

    async def get_tenant_stats(self) -> Dict[str, Any]:
        """Get tenant management statistics."""
        if not self._initialized:
            await self.initialize()

        return await self.registry.get_tenant_stats()

    async def cleanup_expired_tenants(self) -> int:
        """Clean up expired temporary tenants."""
        if not self._initialized:
            await self.initialize()

        return await self.registry.cleanup_expired_tenants()

    async def validate_tenant_access(self, tenant_id: str) -> bool:
        """Validate that a tenant can access the system."""
        if not self._initialized:
            await self.initialize()

        metadata = await self.registry.get_tenant(tenant_id)
        if not metadata:
            return False

        # Check tenant status
        if metadata.status == TenantStatus.DISABLED:
            return False

        # Check if tenant is expired
        if metadata.expires_at and metadata.expires_at <= datetime.utcnow():
            return False

        return True

    async def get_tenant_quota_config(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant-specific quota configuration."""
        default_config = {
            "daily_quota": 10000,
            "rate_limit_rps": 50.0,
            "rate_limit_burst": 100,
            "max_connections": 100,
            "memory_limit_mb": 1024,
        }

        # Get tenant-specific config
        tenant_config = await self.get_tenant_config(tenant_id)

        # Merge with defaults
        quota_config = {**default_config, **tenant_config.get("quota", {})}

        # Exempt tenants get unlimited quotas
        if await self.is_exempt_tenant(tenant_id):
            quota_config["daily_quota"] = float("inf")
            quota_config["rate_limit_rps"] = float("inf")
            quota_config["rate_limit_burst"] = float("inf")

        return quota_config

    async def resolve_tenant_for_legacy_compatibility(
        self, tenant_id: Optional[str] = None
    ) -> str:
        """Resolve tenant ID for legacy compatibility."""
        if not self._initialized:
            await self.initialize()

        # If tenant_id is provided, validate it exists
        if tenant_id and await self.registry.tenant_exists(tenant_id):
            return tenant_id

        # Try to resolve legacy hardcoded names
        legacy_mappings = {
            "agent_zero": "agent_zero",
            "public": "public",
            "sandbox": "sandbox",
            "default": "public",
        }

        for legacy_name, system_name in legacy_mappings.items():
            if tenant_id == legacy_name:
                system_tenant_id = await self.get_system_tenant_id(system_name)
                if system_tenant_id:
                    return system_tenant_id

        # Fallback to default tenant
        if self._default_tenant_id:
            return self._default_tenant_id

        # Create temporary tenant
        return await self.create_temporary_tenant()

    async def _get_tenant_by_tier(self, tier: TenantTier) -> Optional[TenantMetadata]:
        """Get first tenant of specified tier."""
        tenants = await self.registry.get_all_tenants(tier)
        return tenants[0] if tenants else None

    async def close(self) -> None:
        """Close the tenant manager."""
        await self.registry.close()
        self._default_tenant_id = None
        self._system_tenant_ids.clear()
        self._initialized = False

        logger.info("Tenant manager closed")


# Global tenant manager instance
_tenant_manager: Optional[TenantManager] = None


async def get_tenant_manager() -> TenantManager:
    """Get the global tenant manager instance."""
    global _tenant_manager

    if _tenant_manager is None:
        # Create registry and manager
        config = get_config()
        redis_url = getattr(config, "redis_url", None)

        registry = TenantRegistry(redis_url)
        _tenant_manager = TenantManager(registry)

        # Initialize
        await _tenant_manager.initialize()

    return _tenant_manager


async def close_tenant_manager() -> None:
    """Close the global tenant manager instance."""
    global _tenant_manager

    if _tenant_manager:
        await _tenant_manager.close()
        _tenant_manager = None
