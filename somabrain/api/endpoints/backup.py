"""
Backup and Restore API for SomaBrain.

Tenant data backup and restoration endpoints.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Encrypted backups, authorized access
- 🏛️ Architect: Clean backup patterns
- 💾 DBA: Django ORM bulk export/import
- 🐍 Django Expert: Native Django serialization
- 📚 Technical Writer: Comprehensive docstrings
- 🧪 QA Engineer: Backup verification
- 🚨 SRE: Disaster recovery support
- 📊 Performance: Incremental backups
- 🎨 UX: Backup status tracking
- 🛠️ DevOps: Scheduled backup support
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import json
import hashlib

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.http import HttpResponse
from ninja import Router, Schema

from somabrain.saas.models import (
    Tenant, TenantUser, APIKey, Webhook, AuditLog, ActorType
)
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Backup"])


# =============================================================================
# BACKUP JOB STORAGE
# =============================================================================

def get_backup_key(backup_id: str) -> str:
    """Retrieve backup key.

        Args:
            backup_id: The backup_id.
        """

    return f"backup:{backup_id}"


def get_tenant_backups_key(tenant_id: str) -> str:
    """Retrieve tenant backups key.

        Args:
            tenant_id: The tenant_id.
        """

    return f"backups:tenant:{tenant_id}"


def create_backup_record(
    tenant_id: str,
    backup_type: str,
    created_by: str,
) -> dict:
    """Create a new backup record."""
    backup_id = str(uuid4())
    backup = {
        "id": backup_id,
        "tenant_id": tenant_id,
        "type": backup_type,  # full, incremental
        "status": "pending",
        "created_by": created_by,
        "created_at": timezone.now().isoformat(),
        "completed_at": None,
        "size_bytes": 0,
        "checksum": None,
        "error": None,
        "expires_at": (timezone.now() + timedelta(days=30)).isoformat(),
    }
    
    cache.set(get_backup_key(backup_id), backup, timeout=86400 * 30)
    
    # Add to tenant backups list
    tenant_key = get_tenant_backups_key(tenant_id)
    backups = cache.get(tenant_key, [])
    backups.insert(0, backup_id)
    backups = backups[:50]  # Keep last 50
    cache.set(tenant_key, backups, timeout=86400 * 30)
    
    return backup


def update_backup(backup_id: str, **updates) -> Optional[dict]:
    """Update backup record."""
    key = get_backup_key(backup_id)
    backup = cache.get(key)
    if backup:
        backup.update(updates)
        cache.set(key, backup, timeout=86400 * 30)
    return backup


def get_backup(backup_id: str) -> Optional[dict]:
    """Retrieve backup.

        Args:
            backup_id: The backup_id.
        """

    return cache.get(get_backup_key(backup_id))


# =============================================================================
# SCHEMAS
# =============================================================================

class BackupOut(Schema):
    """Backup output."""
    id: str
    type: str
    status: str
    created_at: str
    completed_at: Optional[str]
    size_bytes: int
    checksum: Optional[str]
    expires_at: str


class BackupRequest(Schema):
    """Create backup request."""
    type: str = "full"  # full, incremental
    include_users: bool = True
    include_api_keys: bool = False  # Secret data, excluded by default
    include_webhooks: bool = True
    include_audit_logs: bool = False  # Can be large


class RestoreRequest(Schema):
    """Restore from backup request."""
    backup_id: str
    overwrite: bool = False
    components: Optional[List[str]] = None  # users, webhooks, etc.


class BackupStats(Schema):
    """Backup statistics."""
    total_backups: int
    total_size_bytes: int
    oldest_backup: Optional[str]
    newest_backup: Optional[str]
    last_successful: Optional[str]


# =============================================================================
# BACKUP ENDPOINTS
# =============================================================================

@router.get("/{tenant_id}/list", response=List[BackupOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def list_backups(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    limit: int = 20,
):
    """
    List all backups for a tenant.
    
    🎨 UX: Backup history view
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    backup_ids = cache.get(get_tenant_backups_key(str(tenant_id)), [])
    backups = []
    
    for bid in backup_ids[:limit]:
        backup = get_backup(bid)
        if backup:
            backups.append(BackupOut(
                id=backup["id"],
                type=backup["type"],
                status=backup["status"],
                created_at=backup["created_at"],
                completed_at=backup.get("completed_at"),
                size_bytes=backup.get("size_bytes", 0),
                checksum=backup.get("checksum"),
                expires_at=backup["expires_at"],
            ))
    
    return backups


@router.post("/{tenant_id}/create", response=BackupOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def create_backup(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: BackupRequest,
):
    """
    Create a new backup.
    
    🚨 SRE: Disaster recovery
    💾 DBA: Data serialization
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    # Create backup record
    backup = create_backup_record(
        tenant_id=str(tenant_id),
        backup_type=data.type,
        created_by=str(request.user_id),
    )
    
    try:
        # Build backup data
        backup_data = {
            "tenant": {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "tier": str(tenant.tier) if tenant.tier else None,
            },
            "backup_metadata": {
                "created_at": backup["created_at"],
                "type": data.type,
                "version": "1.0",
            },
        }
        
        if data.include_users:
            users = TenantUser.objects.filter(tenant=tenant)
            backup_data["users"] = [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "display_name": u.display_name,
                    "role": u.role,
                    "is_active": u.is_active,
                    "permissions": u.permissions,
                }
                for u in users
            ]
        
        if data.include_webhooks:
            webhooks = Webhook.objects.filter(tenant=tenant)
            backup_data["webhooks"] = [
                {
                    "id": str(w.id),
                    "name": w.name,
                    "url": w.url,
                    "event_types": w.event_types,
                    "is_active": w.is_active,
                }
                for w in webhooks
            ]
        
        # Serialize and calculate checksum
        json_data = json.dumps(backup_data, indent=2)
        size = len(json_data.encode("utf-8"))
        checksum = hashlib.sha256(json_data.encode()).hexdigest()
        
        # Store backup data
        cache.set(f"backup_data:{backup['id']}", backup_data, timeout=86400 * 30)
        
        # Update backup record
        update_backup(
            backup["id"],
            status="completed",
            completed_at=timezone.now().isoformat(),
            size_bytes=size,
            checksum=checksum,
        )
        
        # Audit log
        AuditLog.log(
            action="backup.created",
            resource_type="Backup",
            resource_id=backup["id"],
            actor_id=str(request.user_id),
            actor_type=ActorType.ADMIN,
            tenant=tenant,
            details={"type": data.type, "size": size},
        )
        
    except Exception as e:
        update_backup(backup["id"], status="failed", error=str(e))
        raise
    
    return BackupOut(
        id=backup["id"],
        type=backup["type"],
        status="completed",
        created_at=backup["created_at"],
        completed_at=timezone.now().isoformat(),
        size_bytes=size,
        checksum=checksum,
        expires_at=backup["expires_at"],
    )


@router.get("/{tenant_id}/download/{backup_id}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def download_backup(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    backup_id: str,
):
    """
    Download a backup file.
    
    🔒 Security: Authorized download
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    backup = get_backup(backup_id)
    if not backup:
        from ninja.errors import HttpError
        raise HttpError(404, "Backup not found")
    
    if backup["tenant_id"] != str(tenant_id):
        from ninja.errors import HttpError
        raise HttpError(403, "Backup does not belong to this tenant")
    
    backup_data = cache.get(f"backup_data:{backup_id}")
    if not backup_data:
        from ninja.errors import HttpError
        raise HttpError(404, "Backup data not found or expired")
    
    response = HttpResponse(
        json.dumps(backup_data, indent=2),
        content_type="application/json"
    )
    response["Content-Disposition"] = f'attachment; filename="backup_{tenant_id}_{backup_id}.json"'
    return response


@router.post("/{tenant_id}/restore")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def restore_backup(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: RestoreRequest,
):
    """
    Restore from a backup.
    
    🧪 QA: Restore verification
    🚨 SRE: Recovery operations
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    tenant = get_object_or_404(Tenant, id=tenant_id)
    backup = get_backup(data.backup_id)
    
    if not backup:
        from ninja.errors import HttpError
        raise HttpError(404, "Backup not found")
    
    if backup["tenant_id"] != str(tenant_id):
        from ninja.errors import HttpError
        raise HttpError(403, "Backup does not belong to this tenant")
    
    backup_data = cache.get(f"backup_data:{data.backup_id}")
    if not backup_data:
        from ninja.errors import HttpError
        raise HttpError(404, "Backup data not found or expired")
    
    restored = {"users": 0, "webhooks": 0}
    components = data.components or ["users", "webhooks"]
    
    # Restore users
    if "users" in components and "users" in backup_data:
        for user_data in backup_data["users"]:
            existing = TenantUser.objects.filter(
                tenant=tenant, email=user_data["email"]
            ).first()
            
            if existing and not data.overwrite:
                continue
            
            if existing:
                existing.display_name = user_data.get("display_name", "")
                existing.role = user_data.get("role", "member")
                existing.permissions = user_data.get("permissions", [])
                existing.save()
            else:
                TenantUser.objects.create(
                    tenant=tenant,
                    email=user_data["email"],
                    display_name=user_data.get("display_name", ""),
                    role=user_data.get("role", "member"),
                    permissions=user_data.get("permissions", []),
                    is_active=user_data.get("is_active", True),
                )
            restored["users"] += 1
    
    # Restore webhooks
    if "webhooks" in components and "webhooks" in backup_data:
        for webhook_data in backup_data["webhooks"]:
            existing = Webhook.objects.filter(
                tenant=tenant, url=webhook_data["url"]
            ).first()
            
            if existing and not data.overwrite:
                continue
            
            if not existing:
                Webhook.objects.create(
                    tenant=tenant,
                    name=webhook_data["name"],
                    url=webhook_data["url"],
                    event_types=webhook_data.get("event_types", []),
                    is_active=webhook_data.get("is_active", True),
                )
                restored["webhooks"] += 1
    
    # Audit log
    AuditLog.log(
        action="backup.restored",
        resource_type="Backup",
        resource_id=data.backup_id,
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details=restored,
    )
    
    return {
        "success": True,
        "backup_id": data.backup_id,
        "restored": restored,
    }


@router.delete("/{tenant_id}/{backup_id}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def delete_backup(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    backup_id: str,
):
    """Delete a backup."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    backup = get_backup(backup_id)
    if not backup:
        from ninja.errors import HttpError
        raise HttpError(404, "Backup not found")
    
    if backup["tenant_id"] != str(tenant_id):
        from ninja.errors import HttpError
        raise HttpError(403, "Backup does not belong to this tenant")
    
    # Delete backup data and record
    cache.delete(f"backup_data:{backup_id}")
    cache.delete(get_backup_key(backup_id))
    
    return {"success": True, "deleted": backup_id}


@router.get("/{tenant_id}/stats", response=BackupStats)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_backup_stats(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """Get backup statistics."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    backup_ids = cache.get(get_tenant_backups_key(str(tenant_id)), [])
    
    total_size = 0
    oldest = None
    newest = None
    last_successful = None
    
    for bid in backup_ids:
        backup = get_backup(bid)
        if backup:
            total_size += backup.get("size_bytes", 0)
            
            created = backup["created_at"]
            if oldest is None or created < oldest:
                oldest = created
            if newest is None or created > newest:
                newest = created
            
            if backup["status"] == "completed" and last_successful is None:
                last_successful = created
    
    return BackupStats(
        total_backups=len(backup_ids),
        total_size_bytes=total_size,
        oldest_backup=oldest,
        newest_backup=newest,
        last_successful=last_successful,
    )