"""
Tenant Invitation System API for SomaBrain.

Invite users to tenants with email tokens and role assignment.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Token-based invitations, expiry validation
- 🏛️ Architect: Clean invitation flow patterns
- 💾 DBA: Django ORM with proper constraints
- 🐍 Django Expert: Native Django patterns, no external frameworks
- 📚 Technical Writer: Comprehensive docstrings
- 🧪 QA Engineer: Testable invitation lifecycle
- 🚨 SRE: Audit logging for invitation actions
- 📊 Performance: Indexed token lookups
- 🎨 UX: Clear invitation status
- 🛠️ DevOps: Configurable expiry times
"""

from typing import List, Optional
from datetime import timedelta
from uuid import UUID, uuid4
import secrets
import hashlib

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from ninja import Router, Schema

from somabrain.saas.models import Tenant, TenantUser, AuditLog, ActorType, UserRole
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Invitations"])


# =============================================================================
# INVITATION TOKEN STORAGE (Cache-backed, would be DB in production)
# =============================================================================

INVITATION_EXPIRY_HOURS = 72  # 3 days


def generate_invitation_token() -> str:
    """Generate a secure invitation token."""
    return secrets.token_urlsafe(32)


def get_invitation_key(token: str) -> str:
    """Get cache key for invitation."""
    return f"invitation:{hashlib.sha256(token.encode()).hexdigest()}"


def store_invitation(token: str, data: dict):
    """Store invitation in cache."""
    key = get_invitation_key(token)
    cache.set(key, data, timeout=INVITATION_EXPIRY_HOURS * 3600)


def get_invitation(token: str) -> Optional[dict]:
    """Retrieve invitation from cache."""
    key = get_invitation_key(token)
    return cache.get(key)


def delete_invitation(token: str):
    """Delete invitation from cache."""
    key = get_invitation_key(token)
    cache.delete(key)


def get_tenant_invitations_key(tenant_id: str) -> str:
    """Get cache key for tenant's pending invitations."""
    return f"invitations:tenant:{tenant_id}"


def add_to_tenant_invitations(tenant_id: str, invitation_id: str):
    """Track invitation for tenant."""
    key = get_tenant_invitations_key(tenant_id)
    invitations = cache.get(key, [])
    invitations.append(invitation_id)
    cache.set(key, invitations, timeout=INVITATION_EXPIRY_HOURS * 3600)


def get_tenant_invitations(tenant_id: str) -> List[str]:
    """Get all invitation IDs for a tenant."""
    key = get_tenant_invitations_key(tenant_id)
    return cache.get(key, [])


# =============================================================================
# SCHEMAS - ALL 10 PERSONAS
# =============================================================================


class InvitationOut(Schema):
    """Invitation output."""

    id: str
    email: str
    role: str
    status: str
    invited_by: Optional[str]
    created_at: str
    expires_at: str
    accepted_at: Optional[str]


class InvitationCreate(Schema):
    """Create invitation request."""

    email: str
    role: str = "member"
    message: Optional[str] = None


class InvitationBulkCreate(Schema):
    """Bulk create invitations."""

    emails: List[str]
    role: str = "member"
    message: Optional[str] = None


class InvitationAccept(Schema):
    """Accept invitation request."""

    display_name: Optional[str] = None


class InvitationVerify(Schema):
    """Verify invitation token response."""

    valid: bool
    email: Optional[str]
    tenant_name: Optional[str]
    role: Optional[str]
    expires_at: Optional[str]
    error: Optional[str]


# =============================================================================
# INVITATION ENDPOINTS - ALL 10 PERSONAS
# =============================================================================


@router.get("/{tenant_id}", response=List[InvitationOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def list_invitations(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    status: Optional[str] = None,
):
    """
    List all pending invitations for a tenant.

    🔒 Security: Tenant isolation enforced
    🎨 UX: Filter by status
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    invitation_ids = get_tenant_invitations(str(tenant_id))
    invitations = []

    for inv_id in invitation_ids:
        # Get invitation data from cache
        inv_data = cache.get(f"invitation_data:{inv_id}")
        if inv_data:
            if status and inv_data.get("status") != status:
                continue
            invitations.append(InvitationOut(**inv_data))

    return invitations


@router.post("/{tenant_id}", response=InvitationOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def create_invitation(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: InvitationCreate,
):
    """
    Create a new invitation for a tenant.

    🔒 Security: Token-based invitation
    🚨 SRE: Audit logging
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    tenant = get_object_or_404(Tenant, id=tenant_id)

    # Check if user already exists
    existing = TenantUser.objects.filter(tenant=tenant, email=data.email).first()
    if existing:
        from ninja.errors import HttpError

        raise HttpError(400, f"User {data.email} is already a member of this tenant")

    # Generate token and invitation
    token = generate_invitation_token()
    invitation_id = str(uuid4())
    now = timezone.now()
    expires_at = now + timedelta(hours=INVITATION_EXPIRY_HOURS)

    invitation_data = {
        "id": invitation_id,
        "token": token,
        "tenant_id": str(tenant_id),
        "tenant_name": tenant.name,
        "email": data.email,
        "role": data.role,
        "message": data.message,
        "status": "pending",
        "invited_by": str(request.user_id),
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "accepted_at": None,
    }

    # Store invitation
    store_invitation(token, invitation_data)
    cache.set(
        f"invitation_data:{invitation_id}",
        invitation_data,
        timeout=INVITATION_EXPIRY_HOURS * 3600,
    )
    add_to_tenant_invitations(str(tenant_id), invitation_id)

    # Audit log
    AuditLog.log(
        action="invitation.created",
        resource_type="Invitation",
        resource_id=invitation_id,
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"email": data.email, "role": data.role},
    )

    return InvitationOut(
        id=invitation_id,
        email=data.email,
        role=data.role,
        status="pending",
        invited_by=str(request.user_id),
        created_at=now.isoformat(),
        expires_at=expires_at.isoformat(),
        accepted_at=None,
    )


@router.post("/{tenant_id}/bulk", response=List[InvitationOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def create_bulk_invitations(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: InvitationBulkCreate,
):
    """
    Create multiple invitations at once.

    📊 Performance: Batch creation
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    tenant = get_object_or_404(Tenant, id=tenant_id)
    invitations = []
    now = timezone.now()
    expires_at = now + timedelta(hours=INVITATION_EXPIRY_HOURS)

    for email in data.emails:
        # Skip if already a member
        existing = TenantUser.objects.filter(tenant=tenant, email=email).first()
        if existing:
            continue

        token = generate_invitation_token()
        invitation_id = str(uuid4())

        invitation_data = {
            "id": invitation_id,
            "token": token,
            "tenant_id": str(tenant_id),
            "tenant_name": tenant.name,
            "email": email,
            "role": data.role,
            "message": data.message,
            "status": "pending",
            "invited_by": str(request.user_id),
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "accepted_at": None,
        }

        store_invitation(token, invitation_data)
        cache.set(
            f"invitation_data:{invitation_id}",
            invitation_data,
            timeout=INVITATION_EXPIRY_HOURS * 3600,
        )
        add_to_tenant_invitations(str(tenant_id), invitation_id)

        invitations.append(
            InvitationOut(
                id=invitation_id,
                email=email,
                role=data.role,
                status="pending",
                invited_by=str(request.user_id),
                created_at=now.isoformat(),
                expires_at=expires_at.isoformat(),
                accepted_at=None,
            )
        )

    # Audit log
    AuditLog.log(
        action="invitation.bulk_created",
        resource_type="Invitation",
        resource_id="bulk",
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"count": len(invitations), "role": data.role},
    )

    return invitations


@router.get("/verify/{token}", response=InvitationVerify)
def verify_invitation(token: str):
    """
    Verify an invitation token (public endpoint).

    🔒 Security: Token validation without auth
    """
    invitation = get_invitation(token)

    if not invitation:
        return InvitationVerify(
            valid=False,
            email=None,
            tenant_name=None,
            role=None,
            expires_at=None,
            error="Invitation not found or expired",
        )

    # Check expiry
    expires_at = invitation.get("expires_at")
    if expires_at:
        from datetime import datetime

        expiry = datetime.fromisoformat(expires_at)
        if timezone.now() > expiry:
            return InvitationVerify(
                valid=False,
                email=invitation.get("email"),
                tenant_name=invitation.get("tenant_name"),
                role=None,
                expires_at=expires_at,
                error="Invitation has expired",
            )

    # Check if already accepted
    if invitation.get("status") == "accepted":
        return InvitationVerify(
            valid=False,
            email=invitation.get("email"),
            tenant_name=invitation.get("tenant_name"),
            role=None,
            expires_at=expires_at,
            error="Invitation has already been accepted",
        )

    return InvitationVerify(
        valid=True,
        email=invitation.get("email"),
        tenant_name=invitation.get("tenant_name"),
        role=invitation.get("role"),
        expires_at=expires_at,
        error=None,
    )


@router.post("/accept/{token}")
def accept_invitation(token: str, data: InvitationAccept):
    """
    Accept an invitation and join the tenant.

    🧪 QA: Invitation lifecycle
    🔒 Security: Token consumption
    """
    invitation = get_invitation(token)

    if not invitation:
        from ninja.errors import HttpError

        raise HttpError(404, "Invitation not found or expired")

    # Check expiry
    expires_at = invitation.get("expires_at")
    if expires_at:
        from datetime import datetime

        expiry = datetime.fromisoformat(expires_at)
        if timezone.now() > expiry:
            from ninja.errors import HttpError

            raise HttpError(400, "Invitation has expired")

    # Check if already accepted
    if invitation.get("status") == "accepted":
        from ninja.errors import HttpError

        raise HttpError(400, "Invitation has already been accepted")

    # Get tenant
    tenant = get_object_or_404(Tenant, id=invitation["tenant_id"])

    # Create tenant user
    user = TenantUser.objects.create(
        tenant=tenant,
        email=invitation["email"],
        display_name=data.display_name or invitation["email"].split("@")[0],
        role=invitation.get("role", UserRole.MEMBER),
        is_active=True,
    )

    # Update invitation status
    invitation["status"] = "accepted"
    invitation["accepted_at"] = timezone.now().isoformat()

    # Update cache
    store_invitation(token, invitation)
    cache.set(
        f"invitation_data:{invitation['id']}",
        invitation,
        timeout=INVITATION_EXPIRY_HOURS * 3600,
    )

    # Audit log
    AuditLog.log(
        action="invitation.accepted",
        resource_type="Invitation",
        resource_id=invitation["id"],
        actor_id=str(user.id),
        actor_type=ActorType.USER,
        tenant=tenant,
        details={"email": invitation["email"]},
    )

    return {
        "success": True,
        "user_id": str(user.id),
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "role": user.role,
    }


@router.post("/decline/{token}")
def decline_invitation(token: str):
    """
    Decline an invitation.

    🎨 UX: Clean decline flow
    """
    invitation = get_invitation(token)

    if not invitation:
        from ninja.errors import HttpError

        raise HttpError(404, "Invitation not found or expired")

    # Update status
    invitation["status"] = "declined"
    store_invitation(token, invitation)
    cache.set(
        f"invitation_data:{invitation['id']}",
        invitation,
        timeout=INVITATION_EXPIRY_HOURS * 3600,
    )

    return {"success": True, "status": "declined"}


@router.delete("/{tenant_id}/{invitation_id}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def revoke_invitation(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    invitation_id: str,
):
    """
    Revoke a pending invitation.

    🔒 Security: Admin-only revocation
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    # Get invitation data
    inv_data = cache.get(f"invitation_data:{invitation_id}")
    if not inv_data:
        from ninja.errors import HttpError

        raise HttpError(404, "Invitation not found")

    # Verify tenant ownership
    if inv_data.get("tenant_id") != str(tenant_id):
        from ninja.errors import HttpError

        raise HttpError(403, "Invitation does not belong to this tenant")

    # Mark as revoked
    inv_data["status"] = "revoked"
    cache.set(
        f"invitation_data:{invitation_id}",
        inv_data,
        timeout=INVITATION_EXPIRY_HOURS * 3600,
    )

    # Delete token
    if inv_data.get("token"):
        delete_invitation(inv_data["token"])

    # Audit log
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="invitation.revoked",
        resource_type="Invitation",
        resource_id=invitation_id,
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"email": inv_data.get("email")},
    )

    return {"success": True, "status": "revoked"}


@router.post("/{tenant_id}/{invitation_id}/resend")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def resend_invitation(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    invitation_id: str,
):
    """
    Resend an invitation with a new token.

    🛠️ DevOps: Token refresh
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    # Get invitation data
    inv_data = cache.get(f"invitation_data:{invitation_id}")
    if not inv_data:
        from ninja.errors import HttpError

        raise HttpError(404, "Invitation not found")

    # Delete old token
    if inv_data.get("token"):
        delete_invitation(inv_data["token"])

    # Generate new token and extend expiry
    new_token = generate_invitation_token()
    now = timezone.now()
    expires_at = now + timedelta(hours=INVITATION_EXPIRY_HOURS)

    inv_data["token"] = new_token
    inv_data["expires_at"] = expires_at.isoformat()
    inv_data["status"] = "pending"

    # Store with new token
    store_invitation(new_token, inv_data)
    cache.set(
        f"invitation_data:{invitation_id}",
        inv_data,
        timeout=INVITATION_EXPIRY_HOURS * 3600,
    )

    return {
        "success": True,
        "invitation_id": invitation_id,
        "new_expires_at": expires_at.isoformat(),
    }
