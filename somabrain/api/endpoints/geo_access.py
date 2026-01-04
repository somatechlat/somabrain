"""
IP Geolocation and Access Control API for SomaBrain.

Geographic access control and IP-based restrictions.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: IP-based access control
- 🏛️ Architect: Clean geo patterns
- 💾 DBA: Django ORM with IP ranges
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Comprehensive docstrings
- 🧪 QA Engineer: Access rule validation
- 🚨 SRE: Geo monitoring
- 📊 Performance: Cached geo lookups
- 🎨 UX: Clear access rules
- 🛠️ DevOps: Geo configuration
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from ninja import Router, Schema

from somabrain.saas.models import Tenant, AuditLog, ActorType
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Geo Access"])


# =============================================================================
# ACCESS RULE TYPES
# =============================================================================

class RuleAction(str, Enum):
    """Access rule actions."""
    ALLOW = "allow"
    DENY = "deny"


class RuleType(str, Enum):
    """Access rule types."""
    COUNTRY = "country"
    REGION = "region"
    IP_RANGE = "ip_range"
    IP_ADDRESS = "ip_address"


# =============================================================================
# ACCESS RULE STORAGE
# =============================================================================

def get_rules_key(tenant_id: str) -> str:
    """Retrieve rules key.

        Args:
            tenant_id: The tenant_id.
        """

    return f"geo_rules:{tenant_id}"


def get_rule_key(rule_id: str) -> str:
    """Retrieve rule key.

        Args:
            rule_id: The rule_id.
        """

    return f"geo_rule:{rule_id}"


# Sample country codes
COUNTRY_CODES = {
    "US": "United States",
    "CA": "Canada",
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "JP": "Japan",
    "AU": "Australia",
    "BR": "Brazil",
    "IN": "India",
    "CN": "China",
}


def create_access_rule(
    tenant_id: str,
    rule_type: str,
    value: str,
    action: str,
    description: str,
    created_by: str,
) -> dict:
    """Create an access rule."""
    rule_id = str(uuid4())
    rule = {
        "id": rule_id,
        "tenant_id": tenant_id,
        "type": rule_type,
        "value": value,
        "action": action,
        "description": description,
        "enabled": True,
        "created_by": created_by,
        "created_at": timezone.now().isoformat(),
        "hits": 0,
    }
    
    cache.set(get_rule_key(rule_id), rule, timeout=86400 * 30)
    
    # Add to tenant list
    tenant_key = get_rules_key(tenant_id)
    rules = cache.get(tenant_key, [])
    rules.append(rule_id)
    cache.set(tenant_key, rules, timeout=86400 * 30)
    
    return rule


def get_access_rule(rule_id: str) -> Optional[dict]:
    """Retrieve access rule.

        Args:
            rule_id: The rule_id.
        """

    return cache.get(get_rule_key(rule_id))


def update_access_rule(rule_id: str, **updates) -> Optional[dict]:
    """Execute update access rule.

        Args:
            rule_id: The rule_id.
        """

    key = get_rule_key(rule_id)
    rule = cache.get(key)
    if rule:
        rule.update(updates)
        cache.set(key, rule, timeout=86400 * 30)
    return rule


def get_tenant_rules(tenant_id: str) -> List[dict]:
    """Retrieve tenant rules.

        Args:
            tenant_id: The tenant_id.
        """

    rule_ids = cache.get(get_rules_key(tenant_id), [])
    rules = []
    for rid in rule_ids:
        rule = get_access_rule(rid)
        if rule:
            rules.append(rule)
    return rules


# =============================================================================
# SCHEMAS
# =============================================================================

class AccessRuleOut(Schema):
    """Access rule output."""
    id: str
    type: str
    value: str
    action: str
    description: Optional[str]
    enabled: bool
    hits: int
    created_at: str


class AccessRuleCreate(Schema):
    """Create access rule."""
    type: str  # country, region, ip_range, ip_address
    value: str
    action: str = "deny"
    description: Optional[str] = None


class AccessRuleUpdate(Schema):
    """Update access rule."""
    value: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class GeoSettings(Schema):
    """Geo settings for tenant."""
    geo_blocking_enabled: bool = False
    default_action: str = "allow"  # allow or deny
    log_blocked_requests: bool = True
    notify_on_blocked: bool = False


class IPInfo(Schema):
    """IP address information."""
    ip_address: str
    country_code: Optional[str]
    country_name: Optional[str]
    region: Optional[str]
    city: Optional[str]
    is_blocked: bool


# =============================================================================
# ACCESS RULE ENDPOINTS
# =============================================================================

@router.get("/{tenant_id}/rules", response=List[AccessRuleOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def list_access_rules(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    rule_type: Optional[str] = None,
):
    """
    List all access rules for a tenant.
    
    🔒 Security: Access control rules
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    rules = get_tenant_rules(str(tenant_id))
    
    if rule_type:
        rules = [r for r in rules if r["type"] == rule_type]
    
    return [
        AccessRuleOut(
            id=r["id"],
            type=r["type"],
            value=r["value"],
            action=r["action"],
            description=r.get("description"),
            enabled=r["enabled"],
            hits=r.get("hits", 0),
            created_at=r["created_at"],
        )
        for r in rules
    ]


@router.post("/{tenant_id}/rules", response=AccessRuleOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def create_rule(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: AccessRuleCreate,
):
    """
    Create an access rule.
    
    🔒 Security: Rule creation
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    # Validate type
    if data.type not in [t.value for t in RuleType]:
        from ninja.errors import HttpError
        raise HttpError(400, f"Invalid rule type: {data.type}")
    
    # Validate action
    if data.action not in [a.value for a in RuleAction]:
        from ninja.errors import HttpError
        raise HttpError(400, f"Invalid action: {data.action}")
    
    rule = create_access_rule(
        tenant_id=str(tenant_id),
        rule_type=data.type,
        value=data.value,
        action=data.action,
        description=data.description or "",
        created_by=str(request.user_id),
    )
    
    # Audit log
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="geo.rule_created",
        resource_type="AccessRule",
        resource_id=rule["id"],
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"type": data.type, "value": data.value, "action": data.action},
    )
    
    return AccessRuleOut(
        id=rule["id"],
        type=rule["type"],
        value=rule["value"],
        action=rule["action"],
        description=rule.get("description"),
        enabled=rule["enabled"],
        hits=rule.get("hits", 0),
        created_at=rule["created_at"],
    )


@router.patch("/{tenant_id}/rules/{rule_id}", response=AccessRuleOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def update_rule(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    rule_id: str,
    data: AccessRuleUpdate,
):
    """Update an access rule."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    rule = get_access_rule(rule_id)
    if not rule or rule["tenant_id"] != str(tenant_id):
        from ninja.errors import HttpError
        raise HttpError(404, "Rule not found")
    
    if data.value is not None:
        rule["value"] = data.value
    if data.action is not None:
        rule["action"] = data.action
    if data.description is not None:
        rule["description"] = data.description
    if data.enabled is not None:
        rule["enabled"] = data.enabled
    
    update_access_rule(rule_id, **rule)
    
    return AccessRuleOut(
        id=rule["id"],
        type=rule["type"],
        value=rule["value"],
        action=rule["action"],
        description=rule.get("description"),
        enabled=rule["enabled"],
        hits=rule.get("hits", 0),
        created_at=rule["created_at"],
    )


@router.delete("/{tenant_id}/rules/{rule_id}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def delete_rule(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    rule_id: str,
):
    """Delete an access rule."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    rule = get_access_rule(rule_id)
    if not rule or rule["tenant_id"] != str(tenant_id):
        from ninja.errors import HttpError
        raise HttpError(404, "Rule not found")
    
    # Remove from cache
    cache.delete(get_rule_key(rule_id))
    
    # Remove from tenant list
    tenant_key = get_rules_key(str(tenant_id))
    rules = cache.get(tenant_key, [])
    rules = [r for r in rules if r != rule_id]
    cache.set(tenant_key, rules, timeout=86400 * 30)
    
    return {"success": True, "deleted": rule_id}


# =============================================================================
# GEO SETTINGS
# =============================================================================

@router.get("/{tenant_id}/settings", response=GeoSettings)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def get_geo_settings(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """Get geo access settings."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    settings = cache.get(f"geo_settings:{tenant_id}", {})
    return GeoSettings(**settings)


@router.put("/{tenant_id}/settings", response=GeoSettings)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def update_geo_settings(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: GeoSettings,
):
    """Update geo access settings."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    cache.set(f"geo_settings:{tenant_id}", data.dict(), timeout=86400 * 30)
    
    return data


# =============================================================================
# IP LOOKUP
# =============================================================================

@router.get("/{tenant_id}/lookup/{ip_address}", response=IPInfo)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def lookup_ip(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    ip_address: str,
):
    """
    Lookup IP address information.
    
    📊 Performance: IP lookup
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    # Simulate geo lookup (in production, use MaxMind or similar)
    is_blocked = False
    rules = get_tenant_rules(str(tenant_id))
    
    for rule in rules:
        if not rule["enabled"]:
            continue
        if rule["type"] == "ip_address" and rule["value"] == ip_address:
            is_blocked = rule["action"] == "deny"
            break
    
    return IPInfo(
        ip_address=ip_address,
        country_code="US",
        country_name="United States",
        region="California",
        city="San Francisco",
        is_blocked=is_blocked,
    )


@router.post("/{tenant_id}/check")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def check_access(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    ip_address: str,
):
    """
    Check if IP address is allowed.
    
    🔒 Security: Access check
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    rules = get_tenant_rules(str(tenant_id))
    settings = cache.get(f"geo_settings:{tenant_id}", {})
    
    default_action = settings.get("default_action", "allow")
    
    for rule in rules:
        if not rule["enabled"]:
            continue
        
        if rule["type"] == "ip_address" and rule["value"] == ip_address:
            return {
                "allowed": rule["action"] == "allow",
                "reason": f"Matched rule: {rule['description'] or rule['value']}",
                "rule_id": rule["id"],
            }
    
    return {
        "allowed": default_action == "allow",
        "reason": f"Default action: {default_action}",
        "rule_id": None,
    }


# =============================================================================
# COUNTRY MANAGEMENT
# =============================================================================

@router.get("/countries")
def list_countries():
    """List available country codes."""
    return {
        "countries": [
            {"code": code, "name": name}
            for code, name in COUNTRY_CODES.items()
        ]
    }


@router.post("/{tenant_id}/block-country")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def block_country(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    country_code: str,
):
    """
    Quick block a country.
    
    🔒 Security: Country blocking
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    if country_code not in COUNTRY_CODES:
        from ninja.errors import HttpError
        raise HttpError(400, f"Unknown country code: {country_code}")
    
    rule = create_access_rule(
        tenant_id=str(tenant_id),
        rule_type="country",
        value=country_code,
        action="deny",
        description=f"Block {COUNTRY_CODES[country_code]}",
        created_by=str(request.user_id),
    )
    
    return {"success": True, "rule_id": rule["id"]}