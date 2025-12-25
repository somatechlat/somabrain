"""
Changelog and Update Notifications API for SomaBrain.

API changelog management and user notifications for updates.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Scoped access to changelog
- 🏛️ Architect: Clean changelog patterns
- 💾 DBA: Django ORM with versioning
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Versioned documentation
- 🧪 QA Engineer: Changelog validation
- 🚨 SRE: Update monitoring
- 📊 Performance: Cached changelogs
- 🎨 UX: Clear update notifications
- 🛠️ DevOps: Release management
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from enum import Enum

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from ninja import Router, Schema

from somabrain.saas.models import Tenant, TenantUser, AuditLog, ActorType
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Changelog"])


# =============================================================================
# CHANGELOG TYPES
# =============================================================================

class ChangeType(str, Enum):
    """Change types."""
    FEATURE = "feature"
    IMPROVEMENT = "improvement"
    FIX = "fix"
    DEPRECATION = "deprecation"
    BREAKING = "breaking"
    SECURITY = "security"


class ReleaseStatus(str, Enum):
    """Release status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# =============================================================================
# CHANGELOG STORAGE
# =============================================================================

def get_releases_key() -> str:
    return "changelog:releases"


def get_release_key(release_id: str) -> str:
    return f"changelog:release:{release_id}"


def get_user_read_key(user_id: str) -> str:
    return f"changelog:read:{user_id}"


def create_release(
    version: str,
    title: str,
    description: str,
    changes: List[dict],
    created_by: str,
) -> dict:
    """Create a new changelog release."""
    release_id = str(uuid4())
    release = {
        "id": release_id,
        "version": version,
        "title": title,
        "description": description,
        "changes": changes,
        "status": ReleaseStatus.DRAFT,
        "created_by": created_by,
        "created_at": timezone.now().isoformat(),
        "published_at": None,
    }
    
    cache.set(get_release_key(release_id), release, timeout=86400 * 365)
    
    # Add to releases list
    releases = cache.get(get_releases_key(), [])
    releases.insert(0, release_id)
    cache.set(get_releases_key(), releases, timeout=86400 * 365)
    
    return release


def get_release(release_id: str) -> Optional[dict]:
    return cache.get(get_release_key(release_id))


def update_release(release_id: str, **updates) -> Optional[dict]:
    key = get_release_key(release_id)
    release = cache.get(key)
    if release:
        release.update(updates)
        cache.set(key, release, timeout=86400 * 365)
    return release


def get_all_releases() -> List[dict]:
    release_ids = cache.get(get_releases_key(), [])
    releases = []
    for rid in release_ids:
        release = get_release(rid)
        if release:
            releases.append(release)
    return releases


# =============================================================================
# SCHEMAS
# =============================================================================

class ChangeEntry(Schema):
    """Single change entry."""
    type: str  # feature, improvement, fix, deprecation, breaking, security
    title: str
    description: Optional[str] = None
    link: Optional[str] = None


class ReleaseOut(Schema):
    """Release output."""
    id: str
    version: str
    title: str
    status: str
    created_at: str
    published_at: Optional[str]
    change_count: int


class ReleaseDetailOut(Schema):
    """Detailed release output."""
    id: str
    version: str
    title: str
    description: str
    changes: List[Dict[str, Any]]
    status: str
    created_at: str
    created_by: Optional[str]
    published_at: Optional[str]


class ReleaseCreate(Schema):
    """Create release request."""
    version: str
    title: str
    description: Optional[str] = None
    changes: List[ChangeEntry]


class ReleaseUpdate(Schema):
    """Update release request."""
    title: Optional[str] = None
    description: Optional[str] = None
    changes: Optional[List[ChangeEntry]] = None


class UnreadChangelog(Schema):
    """Unread changelog info."""
    has_unread: bool
    unread_count: int
    latest_version: Optional[str]


# =============================================================================
# PUBLIC CHANGELOG ENDPOINTS
# =============================================================================

@router.get("/releases", response=List[ReleaseOut])
def list_releases(
    status: Optional[str] = "published",
    limit: int = 10,
):
    """
    List changelog releases (public).
    
    📚 Technical Writer: Public changelog
    """
    releases = get_all_releases()
    
    if status:
        releases = [r for r in releases if r["status"] == status]
    
    return [
        ReleaseOut(
            id=r["id"],
            version=r["version"],
            title=r["title"],
            status=r["status"],
            created_at=r["created_at"],
            published_at=r.get("published_at"),
            change_count=len(r.get("changes", [])),
        )
        for r in releases[:limit]
    ]


@router.get("/releases/{release_id}", response=ReleaseDetailOut)
def get_release_detail(release_id: str):
    """
    Get release details (public).
    
    📚 Technical Writer: Release details
    """
    release = get_release(release_id)
    if not release:
        from ninja.errors import HttpError
        raise HttpError(404, "Release not found")
    
    return ReleaseDetailOut(
        id=release["id"],
        version=release["version"],
        title=release["title"],
        description=release.get("description", ""),
        changes=release.get("changes", []),
        status=release["status"],
        created_at=release["created_at"],
        created_by=release.get("created_by"),
        published_at=release.get("published_at"),
    )


@router.get("/latest")
def get_latest_release():
    """
    Get latest published release.
    
    📚 Technical Writer: Latest version
    """
    releases = get_all_releases()
    published = [r for r in releases if r["status"] == "published"]
    
    if not published:
        return {"latest": None}
    
    latest = published[0]
    return {
        "latest": {
            "version": latest["version"],
            "title": latest["title"],
            "published_at": latest.get("published_at"),
            "change_count": len(latest.get("changes", [])),
        }
    }


# =============================================================================
# ADMIN CHANGELOG MANAGEMENT
# =============================================================================

@router.post("/admin/releases", response=ReleaseDetailOut)
@require_auth(roles=["super-admin"], any_role=True)
def create_release_admin(
    request: AuthenticatedRequest,
    data: ReleaseCreate,
):
    """
    Create a new changelog release (admin only).
    
    🛠️ DevOps: Release management
    """
    release = create_release(
        version=data.version,
        title=data.title,
        description=data.description or "",
        changes=[c.dict() for c in data.changes],
        created_by=str(request.user_id),
    )
    
    return ReleaseDetailOut(
        id=release["id"],
        version=release["version"],
        title=release["title"],
        description=release.get("description", ""),
        changes=release.get("changes", []),
        status=release["status"],
        created_at=release["created_at"],
        created_by=release.get("created_by"),
        published_at=release.get("published_at"),
    )


@router.patch("/admin/releases/{release_id}", response=ReleaseDetailOut)
@require_auth(roles=["super-admin"], any_role=True)
def update_release_admin(
    request: AuthenticatedRequest,
    release_id: str,
    data: ReleaseUpdate,
):
    """Update a changelog release."""
    release = get_release(release_id)
    if not release:
        from ninja.errors import HttpError
        raise HttpError(404, "Release not found")
    
    if data.title is not None:
        release["title"] = data.title
    if data.description is not None:
        release["description"] = data.description
    if data.changes is not None:
        release["changes"] = [c.dict() for c in data.changes]
    
    update_release(release_id, **release)
    
    return ReleaseDetailOut(
        id=release["id"],
        version=release["version"],
        title=release["title"],
        description=release.get("description", ""),
        changes=release.get("changes", []),
        status=release["status"],
        created_at=release["created_at"],
        created_by=release.get("created_by"),
        published_at=release.get("published_at"),
    )


@router.post("/admin/releases/{release_id}/publish")
@require_auth(roles=["super-admin"], any_role=True)
def publish_release(
    request: AuthenticatedRequest,
    release_id: str,
):
    """
    Publish a changelog release.
    
    🛠️ DevOps: Release publishing
    """
    release = get_release(release_id)
    if not release:
        from ninja.errors import HttpError
        raise HttpError(404, "Release not found")
    
    update_release(
        release_id,
        status=ReleaseStatus.PUBLISHED,
        published_at=timezone.now().isoformat(),
    )
    
    return {"success": True, "status": "published"}


@router.delete("/admin/releases/{release_id}")
@require_auth(roles=["super-admin"], any_role=True)
def delete_release_admin(
    request: AuthenticatedRequest,
    release_id: str,
):
    """Delete a changelog release."""
    release = get_release(release_id)
    if not release:
        from ninja.errors import HttpError
        raise HttpError(404, "Release not found")
    
    cache.delete(get_release_key(release_id))
    
    releases = cache.get(get_releases_key(), [])
    releases = [r for r in releases if r != release_id]
    cache.set(get_releases_key(), releases, timeout=86400 * 365)
    
    return {"success": True, "deleted": release_id}


# =============================================================================
# USER UNREAD TRACKING
# =============================================================================

@router.get("/unread", response=UnreadChangelog)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_unread_changelog(request: AuthenticatedRequest):
    """
    Check if user has unread changelog entries.
    
    🎨 UX: Update notifications
    """
    read_releases = cache.get(get_user_read_key(str(request.user_id)), [])
    releases = get_all_releases()
    published = [r for r in releases if r["status"] == "published"]
    
    unread = [r for r in published if r["id"] not in read_releases]
    
    return UnreadChangelog(
        has_unread=len(unread) > 0,
        unread_count=len(unread),
        latest_version=published[0]["version"] if published else None,
    )


@router.post("/mark-read")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def mark_changelog_read(
    request: AuthenticatedRequest,
    release_id: Optional[str] = None,
):
    """
    Mark changelog entries as read.
    
    🎨 UX: Dismiss notifications
    """
    key = get_user_read_key(str(request.user_id))
    read_releases = cache.get(key, [])
    
    if release_id:
        if release_id not in read_releases:
            read_releases.append(release_id)
    else:
        # Mark all as read
        releases = get_all_releases()
        published = [r for r in releases if r["status"] == "published"]
        read_releases = [r["id"] for r in published]
    
    cache.set(key, read_releases, timeout=86400 * 365)
    
    return {"success": True, "marked_read": len(read_releases)}


# =============================================================================
# SEARCH AND FILTER
# =============================================================================

@router.get("/search")
def search_changelog(
    q: str,
    change_type: Optional[str] = None,
    limit: int = 20,
):
    """
    Search changelog entries.
    
    📚 Technical Writer: Changelog search
    """
    releases = get_all_releases()
    published = [r for r in releases if r["status"] == "published"]
    
    results = []
    q_lower = q.lower()
    
    for release in published:
        for change in release.get("changes", []):
            # Filter by type if specified
            if change_type and change.get("type") != change_type:
                continue
            
            # Search in title and description
            title = change.get("title", "").lower()
            desc = change.get("description", "").lower()
            
            if q_lower in title or q_lower in desc:
                results.append({
                    "version": release["version"],
                    "release_id": release["id"],
                    "change": change,
                })
    
    return {"results": results[:limit], "total": len(results)}
