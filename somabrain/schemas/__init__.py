"""
Schemas Package.

Pydantic models for API requests and responses used throughout SomaBrain.
"""

# Common
from .common import normalize_vector

# Cognitive (Nano Profile)
from .cognitive import (
    Action,
    Feedback,
    Memory,
    Metric,
    Observation,
    PlanStep,
    Thought,
    ToolCall,
)

# Memory operations
from .memory import (
    DeleteRequest,
    DeleteResponse,
    GraphLinksRequest,
    GraphLinksResponse,
    LinkRequest,
    LinkResponse,
    MemoryPayload,
    RecallRequest,
    RecallResponse,
    RememberRequest,
    RememberResponse,
    RetrievalCandidate,
    RetrievalRequest,
    RetrievalResponse,
    TimestampInput,
    WMHit,
)

# API operations
from .api import (
    ActRequest,
    ActResponse,
    ActStepResult,
    HealthResponse,
    MigrateExportRequest,
    MigrateExportResponse,
    MigrateImportRequest,
    MigrateImportResponse,
    NeuromodStateModel,
    Persona,
    PersonalityState,
    PlanSuggestRequest,
    PlanSuggestResponse,
    ReflectResponse,
    SleepRunRequest,
    SleepRunResponse,
    SleepStatusAllResponse,
    SleepStatusResponse,
)

# Admin operations
from .admin import (
    FeatureFlagsResponse,
    FeatureFlagsUpdateRequest,
    FeatureFlagsUpdateResponse,
    OutboxEventModel,
    OutboxListResponse,
    OutboxReplayRequest,
    OutboxReplayResponse,
    OutboxSummaryResponse,
    OutboxTenantListResponse,
    OutboxTenantReplayRequest,
    OutboxTenantReplayResponse,
    OutboxTenantSummary,
    QuotaAdjustRequest,
    QuotaAdjustResponse,
    QuotaListResponse,
    QuotaResetRequest,
    QuotaResetResponse,
    QuotaStatus,
)

# Oak
from .oak import OakOptionCreateRequest, OakPlanSuggestResponse

__all__ = [
    # Common
    "normalize_vector",
    # Cognitive
    "Action",
    "Feedback",
    "Memory",
    "Metric",
    "Observation",
    "PlanStep",
    "Thought",
    "ToolCall",
    # Memory
    "DeleteRequest",
    "DeleteResponse",
    "GraphLinksRequest",
    "GraphLinksResponse",
    "LinkRequest",
    "LinkResponse",
    "MemoryPayload",
    "RecallRequest",
    "RecallResponse",
    "RememberRequest",
    "RememberResponse",
    "RetrievalCandidate",
    "RetrievalRequest",
    "RetrievalResponse",
    "TimestampInput",
    "WMHit",
    # API
    "ActRequest",
    "ActResponse",
    "ActStepResult",
    "HealthResponse",
    "MigrateExportRequest",
    "MigrateExportResponse",
    "MigrateImportRequest",
    "MigrateImportResponse",
    "NeuromodStateModel",
    "Persona",
    "PersonalityState",
    "PlanSuggestRequest",
    "PlanSuggestResponse",
    "ReflectResponse",
    "SleepRunRequest",
    "SleepRunResponse",
    "SleepStatusAllResponse",
    "SleepStatusResponse",
    # Admin
    "FeatureFlagsResponse",
    "FeatureFlagsUpdateRequest",
    "FeatureFlagsUpdateResponse",
    "OutboxEventModel",
    "OutboxListResponse",
    "OutboxReplayRequest",
    "OutboxReplayResponse",
    "OutboxSummaryResponse",
    "OutboxTenantListResponse",
    "OutboxTenantReplayRequest",
    "OutboxTenantReplayResponse",
    "OutboxTenantSummary",
    "QuotaAdjustRequest",
    "QuotaAdjustResponse",
    "QuotaListResponse",
    "QuotaResetRequest",
    "QuotaResetResponse",
    "QuotaStatus",
    # Oak
    "OakOptionCreateRequest",
    "OakPlanSuggestResponse",
]
