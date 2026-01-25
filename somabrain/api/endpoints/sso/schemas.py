"""
SSO and Identity Provider Schemas.

Django Ninja schemas for SSO configuration.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Secure IdP configuration schemas
- 📚 Docs: Comprehensive docstrings
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from ninja import Schema


class IdPType(str, Enum):
    """Identity provider types."""

    SAML = "saml"
    OIDC = "oidc"
    OAUTH2 = "oauth2"
    LDAP = "ldap"


class IdPStatus(str, Enum):
    """IdP status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    ERROR = "error"


class SAMLConfig(Schema):
    """SAML configuration."""

    entity_id: str
    sso_url: str
    slo_url: Optional[str] = None
    certificate: str
    name_id_format: str = "emailAddress"
    sign_requests: bool = True


class OIDCConfig(Schema):
    """OIDC configuration."""

    issuer_url: str
    client_id: str
    client_secret: str
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    userinfo_endpoint: Optional[str] = None
    scopes: List[str] = ["openid", "email", "profile"]


class LDAPConfig(Schema):
    """LDAP configuration."""

    server_url: str
    base_dn: str
    bind_dn: str
    bind_password: str
    user_search_filter: str = "(uid={username})"
    group_search_filter: Optional[str] = None
    use_ssl: bool = True


class IdPOut(Schema):
    """Identity provider output."""

    id: str
    name: str
    type: str
    status: str
    created_at: str
    last_verified_at: Optional[str]
    login_count: int
    error_count: int


class IdPDetailOut(Schema):
    """Detailed IdP output."""

    id: str
    name: str
    type: str
    status: str
    config: Dict[str, Any]
    created_at: str
    created_by: Optional[str]
    last_verified_at: Optional[str]
    login_count: int
    error_count: int
    last_error: Optional[str]


class IdPCreate(Schema):
    """Create IdP request."""

    name: str
    type: str
    config: Dict[str, Any]


class IdPUpdate(Schema):
    """Update IdP request."""

    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class SSOSettings(Schema):
    """SSO settings for tenant."""

    enabled: bool = False
    enforce_sso: bool = False
    default_idp_id: Optional[str] = None
    allow_password_login: bool = True
    auto_provision_users: bool = True
    jit_user_role: str = "member"
