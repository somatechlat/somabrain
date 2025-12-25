"""
Tenant Onboarding Wizard API for SomaBrain.

Guided onboarding experience for new tenants.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security Engineer: Tenant isolation, secure step validation
- 🏛️ Architect: Clean wizard state machine patterns
- 💾 DBA: Django ORM with efficient step tracking
- 🐍 Django Expert: Native Django patterns, no external frameworks
- 📚 Technical Writer: Comprehensive docstrings and clear responses
- 🧪 QA Engineer: Testable step transitions, validation
- 🚨 SRE: Progress tracking, failure recovery
- 📊 Performance Engineer: Cached progress, efficient queries
- 🎨 UX Advocate: Clear step progression, helpful guidance
- 🛠️ DevOps: Environment-aware setup
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from ninja import Router, Schema

from somabrain.saas.models import Tenant, TenantUser, AuditLog, ActorType
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Onboarding"])


# =============================================================================
# ONBOARDING STEPS DEFINITION - ALL 10 PERSONAS
# =============================================================================

class OnboardingStep(str, Enum):
    """Onboarding wizard steps."""
    WELCOME = "welcome"
    ORGANIZATION_PROFILE = "organization_profile"
    INVITE_TEAM = "invite_team"
    API_KEY_SETUP = "api_key_setup"
    FIRST_MEMORY = "first_memory"
    WEBHOOK_CONFIG = "webhook_config"
    BILLING_SETUP = "billing_setup"
    COMPLETED = "completed"


STEP_ORDER = [
    OnboardingStep.WELCOME,
    OnboardingStep.ORGANIZATION_PROFILE,
    OnboardingStep.INVITE_TEAM,
    OnboardingStep.API_KEY_SETUP,
    OnboardingStep.FIRST_MEMORY,
    OnboardingStep.WEBHOOK_CONFIG,
    OnboardingStep.BILLING_SETUP,
    OnboardingStep.COMPLETED,
]

STEP_INFO = {
    OnboardingStep.WELCOME: {
        "title": "Welcome to SomaBrain",
        "description": "Get started with your intelligent memory platform",
        "required": True,
        "estimated_minutes": 2,
    },
    OnboardingStep.ORGANIZATION_PROFILE: {
        "title": "Set Up Organization",
        "description": "Configure your organization's profile and settings",
        "required": True,
        "estimated_minutes": 3,
    },
    OnboardingStep.INVITE_TEAM: {
        "title": "Invite Team Members",
        "description": "Add your team members to collaborate",
        "required": False,
        "estimated_minutes": 5,
    },
    OnboardingStep.API_KEY_SETUP: {
        "title": "Create API Key",
        "description": "Generate your first API key for integration",
        "required": True,
        "estimated_minutes": 2,
    },
    OnboardingStep.FIRST_MEMORY: {
        "title": "Create First Memory",
        "description": "Store your first memory to see the system in action",
        "required": False,
        "estimated_minutes": 5,
    },
    OnboardingStep.WEBHOOK_CONFIG: {
        "title": "Configure Webhooks",
        "description": "Set up event notifications for your system",
        "required": False,
        "estimated_minutes": 5,
    },
    OnboardingStep.BILLING_SETUP: {
        "title": "Set Up Billing",
        "description": "Configure your subscription and billing details",
        "required": True,
        "estimated_minutes": 3,
    },
    OnboardingStep.COMPLETED: {
        "title": "Onboarding Complete",
        "description": "You're all set! Start using SomaBrain",
        "required": True,
        "estimated_minutes": 0,
    },
}


# =============================================================================
# SCHEMAS - ALL 10 PERSONAS
# =============================================================================

class OnboardingStepOut(Schema):
    """Step information output."""
    step: str
    title: str
    description: str
    required: bool
    estimated_minutes: int
    completed: bool
    completed_at: Optional[str]
    skipped: bool


class OnboardingProgressOut(Schema):
    """Complete onboarding progress."""
    tenant_id: UUID
    current_step: str
    completed_steps: List[str]
    skipped_steps: List[str]
    progress_percentage: int
    started_at: str
    last_activity_at: str
    is_complete: bool


class StepCompleteRequest(Schema):
    """Request to mark step as complete."""
    data: Optional[Dict[str, Any]] = None


class StepSkipRequest(Schema):
    """Request to skip a step."""
    reason: Optional[str] = None


# =============================================================================
# PROGRESS STORAGE - CACHE BACKED
# =============================================================================

def get_progress_key(tenant_id: str) -> str:
    """Generate cache key for onboarding progress."""
    return f"onboarding:progress:{tenant_id}"


def get_onboarding_progress(tenant_id: str) -> Dict[str, Any]:
    """Get or create onboarding progress for tenant."""
    key = get_progress_key(tenant_id)
    progress = cache.get(key)
    
    if not progress:
        now = timezone.now().isoformat()
        progress = {
            "tenant_id": tenant_id,
            "current_step": OnboardingStep.WELCOME.value,
            "completed_steps": [],
            "skipped_steps": [],
            "step_data": {},
            "started_at": now,
            "last_activity_at": now,
        }
        cache.set(key, progress, timeout=86400 * 30)  # 30 days
    
    return progress


def save_onboarding_progress(tenant_id: str, progress: Dict[str, Any]):
    """Save onboarding progress to cache."""
    key = get_progress_key(tenant_id)
    progress["last_activity_at"] = timezone.now().isoformat()
    cache.set(key, progress, timeout=86400 * 30)


def calculate_progress_percentage(progress: Dict[str, Any]) -> int:
    """Calculate completion percentage."""
    total_required = sum(1 for s in STEP_ORDER if STEP_INFO[s]["required"])
    completed_required = sum(
        1 for s in progress["completed_steps"]
        if STEP_INFO.get(OnboardingStep(s), {}).get("required", False)
    )
    return int((completed_required / total_required) * 100) if total_required > 0 else 0


# =============================================================================
# ENDPOINTS - ALL 10 PERSONAS
# =============================================================================

@router.get("/{tenant_id}/steps", response=List[OnboardingStepOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def list_onboarding_steps(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    List all onboarding steps with completion status.
    
    🔒 Security: Tenant isolation enforced
    🎨 UX: Clear step progression
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    progress = get_onboarding_progress(str(tenant_id))
    
    steps = []
    for step in STEP_ORDER:
        info = STEP_INFO[step]
        step_data = progress.get("step_data", {}).get(step.value, {})
        
        steps.append(OnboardingStepOut(
            step=step.value,
            title=info["title"],
            description=info["description"],
            required=info["required"],
            estimated_minutes=info["estimated_minutes"],
            completed=step.value in progress["completed_steps"],
            completed_at=step_data.get("completed_at"),
            skipped=step.value in progress["skipped_steps"],
        ))
    
    return steps


@router.get("/{tenant_id}/progress", response=OnboardingProgressOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_progress(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get current onboarding progress.
    
    🚨 SRE: Progress tracking
    📊 Performance: Cached progress
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    progress = get_onboarding_progress(str(tenant_id))
    
    return OnboardingProgressOut(
        tenant_id=UUID(progress["tenant_id"]),
        current_step=progress["current_step"],
        completed_steps=progress["completed_steps"],
        skipped_steps=progress["skipped_steps"],
        progress_percentage=calculate_progress_percentage(progress),
        started_at=progress["started_at"],
        last_activity_at=progress["last_activity_at"],
        is_complete=OnboardingStep.COMPLETED.value in progress["completed_steps"],
    )


@router.post("/{tenant_id}/steps/{step}/complete")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def complete_step(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    step: str,
    data: StepCompleteRequest,
):
    """
    Mark an onboarding step as complete.
    
    🧪 QA: Step validation
    🏛️ Architect: State machine transitions
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    # Validate step
    try:
        step_enum = OnboardingStep(step)
    except ValueError:
        from ninja.errors import HttpError
        raise HttpError(400, f"Invalid step: {step}")
    
    progress = get_onboarding_progress(str(tenant_id))
    
    # Mark as complete
    if step not in progress["completed_steps"]:
        progress["completed_steps"].append(step)
    
    # Remove from skipped if it was skipped
    if step in progress["skipped_steps"]:
        progress["skipped_steps"].remove(step)
    
    # Store step data
    progress.setdefault("step_data", {})[step] = {
        "completed_at": timezone.now().isoformat(),
        "data": data.data or {},
    }
    
    # Advance to next step
    current_idx = STEP_ORDER.index(step_enum)
    if current_idx < len(STEP_ORDER) - 1:
        progress["current_step"] = STEP_ORDER[current_idx + 1].value
    
    save_onboarding_progress(str(tenant_id), progress)
    
    # Audit log
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="onboarding.step_completed",
        resource_type="Onboarding",
        resource_id=step,
        actor_id=str(request.user_id),
        actor_type=ActorType.USER,
        tenant=tenant,
        details={"step": step, "percentage": calculate_progress_percentage(progress)},
    )
    
    return {
        "success": True,
        "step": step,
        "next_step": progress["current_step"],
        "progress_percentage": calculate_progress_percentage(progress),
    }


@router.post("/{tenant_id}/steps/{step}/skip")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def skip_step(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    step: str,
    data: StepSkipRequest,
):
    """
    Skip an optional onboarding step.
    
    🔒 Security: Only optional steps can be skipped
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    # Validate step
    try:
        step_enum = OnboardingStep(step)
    except ValueError:
        from ninja.errors import HttpError
        raise HttpError(400, f"Invalid step: {step}")
    
    # Check if step can be skipped
    if STEP_INFO[step_enum]["required"]:
        from ninja.errors import HttpError
        raise HttpError(400, f"Step '{step}' is required and cannot be skipped")
    
    progress = get_onboarding_progress(str(tenant_id))
    
    # Mark as skipped
    if step not in progress["skipped_steps"]:
        progress["skipped_steps"].append(step)
    
    # Advance to next step
    current_idx = STEP_ORDER.index(step_enum)
    if current_idx < len(STEP_ORDER) - 1:
        progress["current_step"] = STEP_ORDER[current_idx + 1].value
    
    save_onboarding_progress(str(tenant_id), progress)
    
    return {
        "success": True,
        "step": step,
        "next_step": progress["current_step"],
        "skipped": True,
    }


@router.post("/{tenant_id}/reset")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def reset_onboarding(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Reset onboarding progress for a tenant.
    
    🛠️ DevOps: Development/testing support
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    key = get_progress_key(str(tenant_id))
    cache.delete(key)
    
    # Audit log
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="onboarding.reset",
        resource_type="Onboarding",
        resource_id=str(tenant_id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
    )
    
    return {"success": True, "message": "Onboarding progress reset"}


@router.get("/{tenant_id}/checklist")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_checklist(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get a simplified checklist view of onboarding.
    
    🎨 UX: Simple progress display
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    progress = get_onboarding_progress(str(tenant_id))
    
    checklist = []
    for step in STEP_ORDER:
        info = STEP_INFO[step]
        if step.value in progress["completed_steps"]:
            status = "completed"
        elif step.value in progress["skipped_steps"]:
            status = "skipped"
        elif step.value == progress["current_step"]:
            status = "current"
        else:
            status = "pending"
        
        checklist.append({
            "step": step.value,
            "title": info["title"],
            "required": info["required"],
            "status": status,
        })
    
    return {
        "tenant_id": str(tenant_id),
        "checklist": checklist,
        "progress_percentage": calculate_progress_percentage(progress),
    }


# =============================================================================
# STEP-SPECIFIC ACTIONS - ALL 10 PERSONAS
# =============================================================================

@router.post("/{tenant_id}/steps/organization_profile/save")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def save_organization_profile(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    name: Optional[str] = None,
    industry: Optional[str] = None,
    size: Optional[str] = None,
    timezone_str: Optional[str] = None,
):
    """
    Save organization profile during onboarding.
    
    💾 DBA: Update tenant record
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    if name:
        tenant.name = name
    if industry:
        tenant.industry = industry
    if size:
        tenant.company_size = size
    if timezone_str:
        tenant.timezone = timezone_str
    
    tenant.save()
    
    return {
        "success": True,
        "tenant_id": str(tenant_id),
        "updated_fields": {
            k: v for k, v in [
                ("name", name), 
                ("industry", industry), 
                ("size", size), 
                ("timezone", timezone_str)
            ] if v
        },
    }
