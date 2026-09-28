"""
SSO and Identity Provider Schemas.

Django Ninja schemas for SSO configuration.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Secure IdP configuration schemas
- 📚 Docs: Comprehensive docstrings
"""

from enum import Enum
from typing import Any

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
    slo_url: str | None = None
    certificate: str
    name_id_format: str = "emailAddress"
    sign_requests: bool = True


class OIDCConfig(Schema):
    """OIDC configuration."""

    issuer_url: str
    client_id: str
    client_secret: str
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    userinfo_endpoint: str | None = None
    scopes: list[str] = ["openid", "email", "profile"]


class LDAPConfig(Schema):
    """LDAP configuration."""

    server_url: str
    base_dn: str
    bind_dn: str
    bind_password: str
    user_search_filter: str = "(uid={username})"
    group_search_filter: str | None = None
    use_ssl: bool = True


class IdPOut(Schema):
    """Identity provider output."""

    id: str
    name: str
    type: str
    status: str
    created_at: str
    last_verified_at: str | None
    login_count: int
    error_count: int


class IdPDetailOut(Schema):
    """Detailed IdP output."""

    id: str
    name: str
    type: str
    status: str
    config: dict[str, Any]
    created_at: str
    created_by: str | None
    last_verified_at: str | None
    login_count: int
    error_count: int
    last_error: str | None


class IdPCreate(Schema):
    """Create IdP request."""

    name: str
    type: str
    config: dict[str, Any]


class IdPUpdate(Schema):
    """Update IdP request."""

    name: str | None = None
    config: dict[str, Any] | None = None
    status: str | None = None


class SSOSettings(Schema):
    """SSO settings for tenant."""

    enabled: bool = False
    enforce_sso: bool = False
    default_idp_id: str | None = None
    allow_password_login: bool = True
    auto_provision_users: bool = True
    jit_user_role: str = "member"
