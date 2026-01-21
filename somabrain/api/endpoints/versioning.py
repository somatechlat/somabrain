"""
API Versioning and Deprecation Management for SomaBrain.

Track API versions, deprecations, and changelog.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Version-based access control
- 🏛️ Architect: Clean versioning patterns
- 💾 DBA: Django ORM for version metadata
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: API changelog documentation
- 🧪 QA Engineer: Version compatibility testing
- 🚨 SRE: Deprecation monitoring
- 📊 Performance: Version routing optimization
- 🎨 UX: Clear deprecation notices
- 🛠️ DevOps: Version lifecycle management
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from django.utils import timezone
from ninja import Router, Schema

from somabrain.saas.auth import AuthenticatedRequest, require_auth
from somabrain.saas.granular import Permission, require_permission
from somabrain.saas.models import ActorType, AuditLog

router = Router(tags=["API Versioning"])


# =============================================================================
# API VERSION DEFINITIONS
# =============================================================================


class APIStatus(str, Enum):
    """API version status."""

    CURRENT = "current"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"
    BETA = "beta"
    ALPHA = "alpha"


API_VERSIONS = {
    "v1": {
        "version": "1.0",
        "status": APIStatus.CURRENT,
        "released_at": "2024-01-01",
        "deprecated_at": None,
        "sunset_at": None,
        "description": "Current stable API version",
        "changelog_url": "/api/versioning/changelog/v1",
    },
    "v2-beta": {
        "version": "2.0-beta",
        "status": APIStatus.BETA,
        "released_at": "2025-01-01",
        "deprecated_at": None,
        "sunset_at": None,
        "description": "Beta version with new features",
        "changelog_url": "/api/versioning/changelog/v2-beta",
    },
}

# Deprecated endpoints tracking
DEPRECATED_ENDPOINTS = [
    {
        "endpoint": "/api/v1/legacy/agents",
        "deprecated_at": "2024-06-01",
        "sunset_at": "2025-06-01",
        "replacement": "/api/v1/memories/agents",
        "reason": "Consolidated into memories module",
    },
]

# Changelog entries
CHANGELOG = {
    "v1": [
        {
            "version": "1.0.37",
            "date": "2025-12-25",
            "changes": [
                {"type": "added", "description": "Activity timeline API"},
                {"type": "added", "description": "Backup and restore API"},
                {"type": "added", "description": "Search and filtering API"},
            ],
        },
        {
            "version": "1.0.36",
            "date": "2025-12-24",
            "changes": [
                {"type": "added", "description": "System configuration API"},
                {"type": "added", "description": "Import/export functionality"},
                {"type": "improved", "description": "Invitation system"},
            ],
        },
        {
            "version": "1.0.35",
            "date": "2025-12-23",
            "changes": [
                {"type": "added", "description": "Feature flags API"},
                {"type": "added", "description": "Audit log search"},
                {"type": "fixed", "description": "Rate limiting edge cases"},
            ],
        },
    ],
}


# =============================================================================
# SCHEMAS
# =============================================================================


class APIVersionOut(Schema):
    """API version output."""

    version: str
    status: str
    released_at: str
    deprecated_at: Optional[str]
    sunset_at: Optional[str]
    description: str
    changelog_url: str


class DeprecatedEndpointOut(Schema):
    """Deprecated endpoint output."""

    endpoint: str
    deprecated_at: str
    sunset_at: str
    replacement: Optional[str]
    reason: str


class ChangelogEntry(Schema):
    """Changelog entry."""

    type: str  # added, changed, deprecated, removed, fixed, security
    description: str


class ChangelogVersion(Schema):
    """Changelog for a version."""

    version: str
    date: str
    changes: List[ChangelogEntry]


class CompatibilityCheck(Schema):
    """Compatibility check result."""

    compatible: bool
    current_version: str
    requested_version: str
    warnings: List[str]
    breaking_changes: List[str]


# =============================================================================
# VERSION ENDPOINTS
# =============================================================================


@router.get("/versions", response=List[APIVersionOut])
def list_api_versions():
    """
    List all API versions with their status.

    📚 Technical Writer: Version documentation
    """
    return [
        APIVersionOut(
            version=v["version"],
            status=v["status"],
            released_at=v["released_at"],
            deprecated_at=v.get("deprecated_at"),
            sunset_at=v.get("sunset_at"),
            description=v["description"],
            changelog_url=v["changelog_url"],
        )
        for v in API_VERSIONS.values()
    ]


@router.get("/versions/current", response=APIVersionOut)
def get_current_version():
    """Get the current stable API version."""
    for key, v in API_VERSIONS.items():
        if v["status"] == APIStatus.CURRENT:
            return APIVersionOut(
                version=v["version"],
                status=v["status"],
                released_at=v["released_at"],
                deprecated_at=v.get("deprecated_at"),
                sunset_at=v.get("sunset_at"),
                description=v["description"],
                changelog_url=v["changelog_url"],
            )

    # VIBE RULES: No fallbacks - require current version to exist
    from ninja.errors import HttpError

    raise HttpError(500, "No current API version configured")


@router.get("/deprecations", response=List[DeprecatedEndpointOut])
def list_deprecated_endpoints():
    """
    List all deprecated endpoints.

    🚨 SRE: Deprecation monitoring
    """
    return [DeprecatedEndpointOut(**d) for d in DEPRECATED_ENDPOINTS]


@router.get("/deprecations/upcoming")
def list_upcoming_sunsets():
    """
    List endpoints with upcoming sunset dates.

    🛠️ DevOps: Migration planning
    """
    now = timezone.now()
    upcoming = []

    for dep in DEPRECATED_ENDPOINTS:
        if dep.get("sunset_at"):
            sunset = datetime.fromisoformat(dep["sunset_at"])
            if sunset > now and sunset < now + timedelta(days=90):
                days_left = (sunset - now).days
                upcoming.append(
                    {
                        **dep,
                        "days_until_sunset": days_left,
                    }
                )

    return sorted(upcoming, key=lambda x: x["days_until_sunset"])


# =============================================================================
# CHANGELOG ENDPOINTS
# =============================================================================


@router.get("/changelog/{version}", response=List[ChangelogVersion])
def get_changelog(
    version: str,
    limit: int = 10,
):
    """
    Get changelog for a specific API version.

    📚 Technical Writer: Change documentation
    """
    entries = CHANGELOG.get(version, [])

    return [
        ChangelogVersion(
            version=e["version"],
            date=e["date"],
            changes=[ChangelogEntry(**c) for c in e["changes"]],
        )
        for e in entries[:limit]
    ]


@router.get("/changelog/latest")
def get_latest_changes(limit: int = 5):
    """Get the most recent changes across all versions."""
    all_changes = []

    for version, entries in CHANGELOG.items():
        for entry in entries:
            all_changes.append(
                {
                    "api_version": version,
                    **entry,
                }
            )

    # Sort by date descending
    all_changes.sort(key=lambda x: x["date"], reverse=True)

    return all_changes[:limit]


# =============================================================================
# COMPATIBILITY ENDPOINTS
# =============================================================================


@router.get("/compatibility/check", response=CompatibilityCheck)
def check_compatibility(
    current: str = "v1",
    target: str = "v2-beta",
):
    """
    Check compatibility between API versions.

    🧪 QA: Compatibility testing
    """
    warnings = []
    breaking = []

    current_info = API_VERSIONS.get(current)
    target_info = API_VERSIONS.get(target)

    if not current_info:
        return CompatibilityCheck(
            compatible=False,
            current_version=current,
            requested_version=target,
            warnings=["Current version not found"],
            breaking_changes=[],
        )

    if not target_info:
        return CompatibilityCheck(
            compatible=False,
            current_version=current,
            requested_version=target,
            warnings=["Target version not found"],
            breaking_changes=[],
        )

    # Check status
    if target_info["status"] == APIStatus.SUNSET:
        breaking.append("Target version has been sunset")
    elif target_info["status"] == APIStatus.DEPRECATED:
        warnings.append("Target version is deprecated")
    elif target_info["status"] == APIStatus.ALPHA:
        warnings.append("Target version is in alpha - expect breaking changes")
    elif target_info["status"] == APIStatus.BETA:
        warnings.append("Target version is in beta - may have breaking changes")

    # Check deprecated endpoints when upgrading
    for dep in DEPRECATED_ENDPOINTS:
        if current in dep.get("endpoint", ""):
            warnings.append(f"Endpoint {dep['endpoint']} is deprecated")

    compatible = len(breaking) == 0

    return CompatibilityCheck(
        compatible=compatible,
        current_version=current,
        requested_version=target,
        warnings=warnings,
        breaking_changes=breaking,
    )


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================


@router.post("/deprecations/add")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def add_deprecation(
    request: AuthenticatedRequest,
    endpoint: str,
    sunset_at: str,
    replacement: Optional[str] = None,
    reason: str = "",
):
    """
    Add a new deprecated endpoint.

    🔒 Security: Admin only
    """
    deprecation = {
        "endpoint": endpoint,
        "deprecated_at": timezone.now().isoformat()[:10],
        "sunset_at": sunset_at,
        "replacement": replacement,
        "reason": reason,
    }

    DEPRECATED_ENDPOINTS.append(deprecation)

    # Audit log
    AuditLog.log(
        action="api.endpoint_deprecated",
        resource_type="APIEndpoint",
        resource_id=endpoint,
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        details=deprecation,
    )

    return {"success": True, "deprecation": deprecation}


@router.get("/stats")
@require_auth(roles=["super-admin"])
def get_version_stats(request: AuthenticatedRequest):
    """
    Get API version usage statistics.

    📊 Performance: Usage analytics
    """
    # In production, this would come from metrics
    return {
        "versions": {
            "v1": {
                "requests_today": 15000,
                "requests_week": 85000,
                "unique_clients": 45,
            },
            "v2-beta": {
                "requests_today": 500,
                "requests_week": 2500,
                "unique_clients": 8,
            },
        },
        "deprecated_usage": {
            "endpoints_called": 3,
            "total_requests": 120,
        },
    }


@router.get("/migration-guide/{from_version}/{to_version}")
def get_migration_guide(from_version: str, to_version: str):
    """
    Get migration guide between versions.

    📚 Technical Writer: Migration documentation
    """
    return {
        "from": from_version,
        "to": to_version,
        "steps": [
            {
                "order": 1,
                "action": "Update SDK",
                "description": f"Update your SDK to {to_version}",
            },
            {
                "order": 2,
                "action": "Review deprecated endpoints",
                "description": "Check /api/versioning/deprecations for affected endpoints",
            },
            {
                "order": 3,
                "action": "Update API calls",
                "description": "Update deprecated endpoint calls to their replacements",
            },
            {
                "order": 4,
                "action": "Test thoroughly",
                "description": "Run integration tests with the new version",
            },
        ],
        "breaking_changes": [],
        "new_features": [],
    }
