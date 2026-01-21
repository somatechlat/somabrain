"""Tenant type definitions for SomaBrain.

Extracted from tenant_registry.py per monolithic-decomposition spec.
Provides TenantTier, TenantStatus enums and TenantMetadata dataclass.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class TenantTier(str, Enum):
    """Tenant tier classification."""

    SYSTEM = "system"
    ENTERPRISE = "enterprise"
    SANDBOX = "sandbox"
    PUBLIC = "public"


class TenantStatus(str, Enum):
    """Tenant status options."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"
    PENDING = "pending"


@dataclass
class TenantMetadata:
    """Comprehensive tenant metadata."""

    tenant_id: str
    display_name: str
    created_at: datetime
    status: TenantStatus
    tier: TenantTier
    config: Dict[str, Any]
    is_exempt: bool
    exempt_reason: Optional[str]
    last_activity: datetime
    created_by: Optional[str]
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["status"] = self.status.value
        data["tier"] = self.tier.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TenantMetadata:
        """Create from dictionary."""
        data = data.copy()
        data["status"] = TenantStatus(data["status"])
        data["tier"] = TenantTier(data["tier"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["last_activity"] = datetime.fromisoformat(data["last_activity"])
        if data.get("expires_at"):
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        return cls(**data)
