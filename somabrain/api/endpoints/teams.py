"""
Team Management API for SomaBrain.

Manage teams within tenants for enterprise organization.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Team-level access control
- 🏛️ Architect: Clean team hierarchy patterns
- 💾 DBA: Django ORM with proper relations
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Comprehensive docstrings
- 🧪 QA Engineer: Team membership validation
- 🚨 SRE: Team audit logging
- 📊 Performance: Optimized team queries
- 🎨 UX: Clear team management
- 🛠️ DevOps: Team configuration
"""

from typing import Any
from uuid import UUID, uuid4

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema

from somabrain.aaas.auth import AuthenticatedRequest, require_auth
from somabrain.aaas.granular import Permission, require_permission
from somabrain.aaas.models import ActorType, AuditLog, Tenant, TenantUser

router = Router(tags=["Teams"])


# =============================================================================
# TEAM STORAGE (Cache-backed, would be Django model in production)
# =============================================================================


def get_teams_key(tenant_id: str) -> str:
    """Retrieve teams key.

    Args:
        tenant_id: The tenant_id.
    """

    return f"teams:tenant:{tenant_id}"


def get_team_key(team_id: str) -> str:
    """Retrieve team key.

    Args:
        team_id: The team_id.
    """

    return f"team:{team_id}"


def get_user_teams_key(user_id: str) -> str:
    """Retrieve user teams key.

    Args:
        user_id: The user_id.
    """

    return f"teams:user:{user_id}"


def create_team(tenant_id: str, name: str, description: str, created_by: str) -> dict:
    """Create a new team."""
    team_id = str(uuid4())
    team = {
        "id": team_id,
        "tenant_id": tenant_id,
        "name": name,
        "description": description,
        "created_by": created_by,
        "created_at": timezone.now().isoformat(),
        "members": [],
        "settings": {
            "private": False,
            "allow_self_join": False,
        },
    }

    # Store team
    cache.set(get_team_key(team_id), team, timeout=86400 * 30)

    # Add to tenant teams list
    tenant_key = get_teams_key(tenant_id)
    teams = cache.get(tenant_key, [])
    teams.append(team_id)
    cache.set(tenant_key, teams, timeout=86400 * 30)

    return team


def get_team(team_id: str) -> dict | None:
    """Retrieve team.

    Args:
        team_id: The team_id.
    """

    return cache.get(get_team_key(team_id))


def update_team(team_id: str, **updates) -> dict | None:
    """Execute update team.

    Args:
        team_id: The team_id.
    """

    key = get_team_key(team_id)
    team = cache.get(key)
    if team:
        team.update(updates)
        cache.set(key, team, timeout=86400 * 30)
    return team


def get_tenant_teams(tenant_id: str) -> list[dict]:
    """Get all teams for a tenant."""
    team_ids = cache.get(get_teams_key(tenant_id), [])
    teams = []
    for tid in team_ids:
        team = get_team(tid)
        if team:
            teams.append(team)
    return teams


# =============================================================================
# SCHEMAS
# =============================================================================


class TeamOut(Schema):
    """Team output."""

    id: str
    name: str
    description: str | None
    member_count: int
    created_at: str
    created_by: str | None
    is_private: bool


class TeamDetailOut(Schema):
    """Detailed team output."""

    id: str
    name: str
    description: str | None
    members: list[dict[str, Any]]
    settings: dict[str, Any]
    created_at: str
    created_by: str | None


class TeamCreate(Schema):
    """Create team request."""

    name: str
    description: str | None = None
    is_private: bool = False
    allow_self_join: bool = False


class TeamUpdate(Schema):
    """Update team request."""

    name: str | None = None
    description: str | None = None
    is_private: bool | None = None
    allow_self_join: bool | None = None


class TeamMemberAdd(Schema):
    """Add team member request."""

    user_id: str
    role: str = "member"  # owner, admin, member


class TeamMemberOut(Schema):
    """Team member output."""

    user_id: str
    email: str
    display_name: str | None
    role: str
    joined_at: str


# =============================================================================
# TEAM CRUD ENDPOINTS
# =============================================================================


@router.get("/{tenant_id}/teams", response=list[TeamOut])
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def list_teams(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    include_private: bool = False,
):
    """
    List all teams in a tenant.

    🎨 UX: Team discovery
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    teams = get_tenant_teams(str(tenant_id))

    result = []
    for team in teams:
        # Filter private teams unless admin
        if team.get("settings", {}).get("private", False) and not include_private:
            if not request.is_super_admin and request.role != "tenant-admin":
                continue

        result.append(
            TeamOut(
                id=team["id"],
                name=team["name"],
                description=team.get("description"),
                member_count=len(team.get("members", [])),
                created_at=team["created_at"],
                created_by=team.get("created_by"),
                is_private=team.get("settings", {}).get("private", False),
            )
        )

    return result


@router.post("/{tenant_id}/teams", response=TeamDetailOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_CREATE.value)
def create_new_team(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: TeamCreate,
):
    """
    Create a new team.

    🔒 Security: Admin team creation
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    team = create_team(
        tenant_id=str(tenant_id),
        name=data.name,
        description=data.description or "",
        created_by=str(request.user_id),
    )

    # Update settings
    team["settings"] = {
        "private": data.is_private,
        "allow_self_join": data.allow_self_join,
    }
    update_team(team["id"], settings=team["settings"])

    # Add creator as owner
    team["members"] = [
        {
            "user_id": str(request.user_id),
            "role": "owner",
            "joined_at": timezone.now().isoformat(),
        }
    ]
    update_team(team["id"], members=team["members"])

    # Audit log
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="team.created",
        resource_type="Team",
        resource_id=team["id"],
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"name": data.name},
    )

    return TeamDetailOut(
        id=team["id"],
        name=team["name"],
        description=team.get("description"),
        members=team["members"],
        settings=team["settings"],
        created_at=team["created_at"],
        created_by=team.get("created_by"),
    )


@router.get("/{tenant_id}/teams/{team_id}", response=TeamDetailOut)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_team_detail(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    team_id: str,
):
    """
    Get team details.

    📊 Performance: Team view
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    team = get_team(team_id)
    if not team or team["tenant_id"] != str(tenant_id):
        from ninja.errors import HttpError

        raise HttpError(404, "Team not found")

    return TeamDetailOut(
        id=team["id"],
        name=team["name"],
        description=team.get("description"),
        members=team.get("members", []),
        settings=team.get("settings", {}),
        created_at=team["created_at"],
        created_by=team.get("created_by"),
    )


@router.patch("/{tenant_id}/teams/{team_id}", response=TeamDetailOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_UPDATE.value)
def update_team_info(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    team_id: str,
    data: TeamUpdate,
):
    """
    Update team information.

    🔒 Security: Admin update
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    team = get_team(team_id)
    if not team or team["tenant_id"] != str(tenant_id):
        from ninja.errors import HttpError

        raise HttpError(404, "Team not found")

    if data.name is not None:
        team["name"] = data.name
    if data.description is not None:
        team["description"] = data.description
    if data.is_private is not None:
        team["settings"]["private"] = data.is_private
    if data.allow_self_join is not None:
        team["settings"]["allow_self_join"] = data.allow_self_join

    update_team(team_id, **team)

    return TeamDetailOut(
        id=team["id"],
        name=team["name"],
        description=team.get("description"),
        members=team.get("members", []),
        settings=team.get("settings", {}),
        created_at=team["created_at"],
        created_by=team.get("created_by"),
    )


@router.delete("/{tenant_id}/teams/{team_id}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_DELETE.value)
def delete_team(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    team_id: str,
):
    """
    Delete a team.

    🔒 Security: Admin deletion
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    team = get_team(team_id)
    if not team or team["tenant_id"] != str(tenant_id):
        from ninja.errors import HttpError

        raise HttpError(404, "Team not found")

    # Remove from cache
    cache.delete(get_team_key(team_id))

    # Remove from tenant list
    tenant_key = get_teams_key(str(tenant_id))
    teams = cache.get(tenant_key, [])
    teams = [t for t in teams if t != team_id]
    cache.set(tenant_key, teams, timeout=86400 * 30)

    # Audit log
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="team.deleted",
        resource_type="Team",
        resource_id=team_id,
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
    )

    return {"success": True, "deleted": team_id}


# =============================================================================
# TEAM MEMBERSHIP
# =============================================================================


@router.get("/{tenant_id}/teams/{team_id}/members", response=list[TeamMemberOut])
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def list_team_members(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    team_id: str,
):
    """
    List team members.

    🎨 UX: Member view
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    team = get_team(team_id)
    if not team or team["tenant_id"] != str(tenant_id):
        from ninja.errors import HttpError

        raise HttpError(404, "Team not found")

    members = []
    for m in team.get("members", []):
        try:
            user = TenantUser.objects.get(id=m["user_id"])
            members.append(
                TeamMemberOut(
                    user_id=m["user_id"],
                    email=user.email,
                    display_name=user.display_name,
                    role=m["role"],
                    joined_at=m["joined_at"],
                )
            )
        except TenantUser.DoesNotExist:
            continue

    return members


@router.post("/{tenant_id}/teams/{team_id}/members")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_UPDATE.value)
def add_team_member(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    team_id: str,
    data: TeamMemberAdd,
):
    """
    Add a member to a team.

    🔒 Security: Membership management
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    team = get_team(team_id)
    if not team or team["tenant_id"] != str(tenant_id):
        from ninja.errors import HttpError

        raise HttpError(404, "Team not found")

    # Verify user exists
    get_object_or_404(TenantUser, id=data.user_id, tenant_id=tenant_id)

    # Check if already a member
    for m in team.get("members", []):
        if m["user_id"] == data.user_id:
            from ninja.errors import HttpError

            raise HttpError(400, "User is already a team member")

    # Add member
    members = team.get("members", [])
    members.append(
        {
            "user_id": data.user_id,
            "role": data.role,
            "joined_at": timezone.now().isoformat(),
        }
    )
    update_team(team_id, members=members)

    return {"success": True, "user_id": data.user_id, "team_id": team_id}


@router.delete("/{tenant_id}/teams/{team_id}/members/{user_id}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_UPDATE.value)
def remove_team_member(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    team_id: str,
    user_id: str,
):
    """
    Remove a member from a team.

    🔒 Security: Membership removal
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    team = get_team(team_id)
    if not team or team["tenant_id"] != str(tenant_id):
        from ninja.errors import HttpError

        raise HttpError(404, "Team not found")

    # Remove member
    members = [m for m in team.get("members", []) if m["user_id"] != user_id]
    update_team(team_id, members=members)

    return {"success": True, "removed": user_id}


# =============================================================================
# USER'S TEAMS
# =============================================================================


@router.get("/my-teams", response=list[TeamOut])
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_my_teams(request: AuthenticatedRequest):
    """
    Get teams the current user belongs to.

    🎨 UX: Personal team view
    """
    teams = get_tenant_teams(str(request.tenant_id))
    my_teams = []

    for team in teams:
        for m in team.get("members", []):
            if m["user_id"] == str(request.user_id):
                my_teams.append(
                    TeamOut(
                        id=team["id"],
                        name=team["name"],
                        description=team.get("description"),
                        member_count=len(team.get("members", [])),
                        created_at=team["created_at"],
                        created_by=team.get("created_by"),
                        is_private=team.get("settings", {}).get("private", False),
                    )
                )
                break

    return my_teams
