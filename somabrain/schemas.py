"""
API Schemas Module for SomaBrain.

This module defines Pydantic models for API requests and responses used throughout
the SomaBrain system. These schemas provide type validation, serialization, and
documentation for the REST API endpoints.

Key Features:
- Pydantic-based data validation and serialization
- Comprehensive API request/response models
- Memory and cognitive operation schemas
- Health monitoring and migration schemas
- Type-safe data structures with automatic validation

Classes:
    RecallRequest: Schema for memory recall API requests.
    MemoryPayload: Schema for episodic memory payloads.
    RememberRequest: Schema for memory storage requests.
    ActRequest: Schema for action execution requests.
    ActStepResult: Schema for individual action step results.
    ActResponse: Schema for action execution responses.
    HealthResponse: Schema for system health check responses.
    PersonalityState: Schema for personality trait states.
    MigrateExportRequest: Schema for data export requests.
    MigrateExportResponse: Schema for export operation responses.
    MigrateImportRequest: Schema for data import requests.
    NeuromodStateModel: Schema for neuromodulator state representation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Union

from datetime import datetime

import numpy as np
from pydantic import BaseModel, Field, model_validator, ConfigDict

from somabrain.nano_profile import HRR_DIM, HRR_DTYPE
from somabrain.datetime_utils import coerce_to_epoch_seconds


def normalize_vector(vec_like, dim: int = HRR_DIM):
    """
    Convert an input sequence/array to a unit-norm float32 list of length `dim`.
    Raises ValueError on invalid inputs.
    """
    # Delegate to the canonical numeric helper for consistent behavior
    from somabrain.numerics import normalize_array

    # Ensure we have a 1-D numpy array, pad or truncate to `dim` as needed
    arr = np.asarray(vec_like, dtype=HRR_DTYPE)
    if arr.ndim != 1:
        arr = arr.reshape(-1)
    if arr.size < dim:
        # pad with zeros
        padded = np.zeros((dim,), dtype=HRR_DTYPE)
        padded[: arr.size] = arr
        arr = padded
    elif arr.size > dim:
        arr = arr[:dim]

    # normalize_array expects the data array and keyword args
    normed = normalize_array(arr, axis=-1, keepdims=False, dtype=HRR_DTYPE)
    return normed.tolist()


# === Canonical Agent Brain Contracts (Nano Profile) ===
class Observation(BaseModel):
    who: str
    where: str
    when: str  # ISO 8601
    channel: str
    content: str
    embeddings: List[float]
    tags: List[str] = []
    traceId: str

    @model_validator(mode="after")
    def _validate_embeddings(self):
        self.embeddings = normalize_vector(self.embeddings, dim=HRR_DIM)
        return self


class Thought(BaseModel):
    id: str
    causeIds: List[str] = []
    text: str
    vector: List[float]
    uncertainty: float = 0.0
    citations: List[str] = []
    policyState: Dict[str, Any] = {}

    @model_validator(mode="after")
    def _validate_vector(self):
        self.vector = normalize_vector(self.vector, dim=HRR_DIM)
        return self


class Memory(BaseModel):
    id: str
    type: str  # "episodic"|"semantic"|"procedural"
    vector: List[float]
    graphRefs: List[str] = []
    payload: Dict[str, Any] = {}
    strength: float = 1.0

    @model_validator(mode="after")
    def _validate_memory_vector(self):
        self.vector = normalize_vector(self.vector, dim=HRR_DIM)
        return self


class ToolCall(BaseModel):
    toolId: str
    schemaVersion: str
    args: Dict[str, Any]
    budget: float = 0.0
    retry: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PlanStep(BaseModel):
    id: str
    preconds: List[str] = []
    action: str
    expected: Dict[str, Any] = {}
    deadline: Optional[str] = None  # ISO 8601
    risk: float = 0.0


class Action(BaseModel):
    channel: str
    toolId: str
    content: str
    args: Dict[str, Any] = {}
    constraints: Dict[str, Any] = {}
    outcome: Optional[Dict[str, Any]] = None


class Feedback(BaseModel):
    signal: str  # "success"|"fail"|"reward"
    reason: str
    metrics: Dict[str, Any] = {}

    class Observation(BaseModel):
        data: dict
        timestamp: float

    class Thought(BaseModel):
        query: str
        context: dict = {}

    class Memory(BaseModel):
        data: dict
        timestamp: float

        @classmethod
        def from_observation(cls, obs: Any):
            # Accept top-level Observation, nested Observation, or dict-like
            if hasattr(obs, "embeddings"):
                vec = getattr(obs, "embeddings", [])
                ts = float(getattr(obs, "when", 0.0)) if hasattr(obs, "when") else 0.0
            elif hasattr(obs, "data"):
                vec = getattr(obs, "data", {}).get("vector", [])
                ts = float(getattr(obs, "timestamp", 0.0))
            else:
                d = dict(obs) if not isinstance(obs, dict) else obs
                vec = d.get("vector", d.get("embeddings", []))
                ts = float(d.get("timestamp", 0.0))
            # Normalize and enforce contract via helper
            normalized = normalize_vector(vec)
            return cls(data={"vector": normalized}, timestamp=ts)

        def matches(self, thought: Any) -> bool:
            # Accept top-level Thought, nested Thought, or dict-like
            if hasattr(thought, "vector"):
                query_vec = np.array(getattr(thought, "vector", []), dtype=np.float32)
            else:
                d = dict(thought) if not isinstance(thought, dict) else thought
                query_vec = np.array(
                    d.get("vector", d.get("context", {}).get("vector", [])),
                    dtype=np.float32,
                )
            query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-8)
            mem_vec = np.array(self.data.get("vector", []), dtype=np.float32)
            mem_vec = mem_vec / (np.linalg.norm(mem_vec) + 1e-8)
            if query_vec.shape[0] != mem_vec.shape[0]:
                return False
            return float(np.dot(query_vec, mem_vec)) > 0.95


class Metric(BaseModel):
    name: str
    value: float
    unit: str
    ts: str  # ISO 8601
    spanId: str


class RecallRequest(BaseModel):
    """
    Schema for memory recall API requests.

    Defines the structure for requests to retrieve memories from the cognitive system
    based on a query string with optional filtering and ranking parameters.

    Attributes:
        query (str): Search query string for memory retrieval.
        top_k (int): Number of top similar memories to return. Default 3.
        universe (Optional[str]): Optional universe/namespace filter for memories.

    Example:
        >>> request = RecallRequest(query="machine learning", top_k=5, universe="research")
    """

    query: str
    top_k: int = 3
    universe: Optional[str] = None


TimestampInput = Union[float, int, str, datetime]


class MemoryPayload(BaseModel):
    """
    Schema for episodic memory payloads.

    Represents the structure of memory content stored in the system, including
    metadata and optional event tuple fields following the "who, did, what, where,
    when, why" framework.

    Attributes:
        task (Optional[str]): Associated task or context identifier.
        importance (int): Importance score (higher values = more important). Default 1.
        memory_type (str): Type of memory ("episodic", "semantic", etc.). Default "episodic".
        timestamp (Optional[float]): Unix epoch seconds (float). Accepts
            ISO-8601 input from clients but is stored internally as epoch
            seconds for consistency across the API.
        universe (Optional[str]): Universe/namespace identifier.
        who (Optional[str]): Who performed the action.
        did (Optional[str]): What action was performed.
        what (Optional[str]): What was affected by the action.
        where (Optional[str]): Where the action occurred.
        when (Optional[str]): When the action occurred.
        why (Optional[str]): Why the action was performed.

    Example:
        >>> payload = MemoryPayload(
        ...     task="learning",
        ...     importance=5,
        ...     who="user",
        ...     did="studied",
        ...     what="neural networks",
        ...     why="to understand AI"
        ... )
    """

    # Minimal episodic payload
    task: Optional[str] = None
    content: Optional[str] = None
    phase: Optional[str] = None
    quality_score: Optional[float] = None
    domains: Optional[Union[List[str], str]] = None
    reasoning_chain: Optional[Union[List[str], str]] = None
    # Importance can be a float (0.0-1.0) or an int; using float for broader compatibility.
    importance: float = 1.0
    memory_type: str = "episodic"
    timestamp: Optional[TimestampInput] = None
    universe: Optional[str] = None
    # Optional event tuple fields
    who: Optional[str] = None
    did: Optional[str] = None
    what: Optional[str] = None
    where: Optional[str] = None
    when: Optional[str] = None
    why: Optional[str] = None

    @model_validator(mode="after")
    def _normalize_timestamp(self):
        if self.timestamp is not None:
            try:
                self.timestamp = coerce_to_epoch_seconds(self.timestamp)
            except ValueError as exc:
                raise ValueError(f"Invalid timestamp format: {exc}")
        return self


class RememberRequest(BaseModel):
    """
    Schema for memory storage requests.

    Defines the structure for requests to store new memories in the cognitive system,
    including optional coordinate specification and memory payload.

    Attributes:
        coord (Optional[str]): Optional 3D coordinate string "x,y,z" for memory placement.
                              Auto-generated if omitted.
        payload (MemoryPayload): Memory content and metadata to store.

    Example:
        >>> request = RememberRequest(
        ...     coord="1.0,2.0,3.0",
        ...     payload=MemoryPayload(task="example", importance=3)
        ... )
    """

    coord: Optional[str] = Field(None, description="x,y,z; optional — auto if omitted")
    payload: MemoryPayload


# ----- Explicit response models for API parity -----
class WMHit(BaseModel):
    score: float
    payload: Dict[str, Any]


class RecallResponse(BaseModel):
    """Canonical response model for the /recall endpoint.

    Fields mirror what the runtime returns in `app.recall` so OpenAPI is accurate.
    Timestamp-bearing fields (e.g. ``payload.timestamp``) are normalized to Unix
    epoch seconds (float) for consistency.
    """

    wm: List[WMHit]
    memory: List[Dict[str, Any]]
    namespace: str
    trace_id: str
    deadline_ms: Optional[str] = None
    idempotency_key: Optional[str] = None
    reality: Optional[Dict[str, Any]] = None
    drift: Optional[Dict[str, Any]] = None
    hrr_cleanup: Optional[Dict[str, Any]] = None
    # Compatibility field: older clients (including our test suite) expect a
    # top‑level ``results`` list containing the recalled memory payloads. The
    # ``memory`` field remains the canonical source; ``results`` mirrors it for
    # backward compatibility.
    results: List[Dict[str, Any]] = []


# ----- Retrieval request and response models -----
class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 10
    # Default to full-power multi-retriever set. Can be overridden via API/env.
    retrievers: List[str] = ["vector", "wm", "graph", "lexical"]
    # Default to auto so the pipeline selects HRR→MMR→cosine based on availability.
    rerank: str = "auto"  # "auto"|"cosine"|"mmr"|"hrr" (validated in pipeline)
    # Enable session learning by default; can be disabled via API/env.
    persist: bool = True
    universe: Optional[str] = None
    # Advanced targeting (optional):
    # mode: auto|id|key|coord|vector|wm|graph (auto by default)
    mode: Optional[str] = None
    # Direct lookup hints; when provided, exact matches are boosted to the top
    id: Optional[str] = None
    key: Optional[str] = None
    coord: Optional[str] = None


class RetrievalCandidate(BaseModel):
    coord: Optional[str] = None
    key: Optional[str] = None
    score: float
    retriever: str
    payload: Dict[str, Any]


class RetrievalResponse(BaseModel):
    candidates: List[RetrievalCandidate]
    session_coord: Optional[str] = None
    namespace: str
    trace_id: str
    metrics: Optional[Dict[str, Any]] = None


class RememberResponse(BaseModel):
    """Canonical response model for the /remember endpoint.

    Mirrors the ad-hoc dict returned by the runtime so docs and OpenAPI are precise.
    """

    ok: bool
    success: bool
    namespace: str
    trace_id: str
    deadline_ms: Optional[str] = None
    idempotency_key: Optional[str] = None
    # Fail-fast: no queued or breaker flags are exposed


# Compact request/response models for previously-dynamic endpoints
class SleepRunRequest(BaseModel):
    nrem: Optional[bool] = True
    rem: Optional[bool] = True


class PlanSuggestRequest(BaseModel):
    task_key: str
    max_steps: Optional[int] = None
    rel_types: Optional[List[str]] = None
    universe: Optional[str] = None


class PlanSuggestResponse(BaseModel):
    plan: List[str]


class LinkRequest(BaseModel):
    from_key: Optional[str] = None
    to_key: Optional[str] = None
    from_coord: Optional[str] = None
    to_coord: Optional[str] = None
    type: Optional[str] = None
    weight: Optional[float] = 1.0
    universe: Optional[str] = None


class GraphLinksRequest(BaseModel):
    from_key: Optional[str] = None
    from_coord: Optional[str] = None
    type: Optional[str] = None
    limit: Optional[int] = 50
    universe: Optional[str] = None


class GraphLinksResponse(BaseModel):
    edges: List[Dict[str, Any]]
    universe: Optional[str] = None


class SleepRunResponse(BaseModel):
    ok: bool = Field(..., description="Whether the sleep run started successfully")
    run_id: Optional[str] = Field(
        None, description="Identifier for the initiated sleep run"
    )

# ---------------------------------------------------------------------------
# Feature flag admin schemas
# ---------------------------------------------------------------------------

class FeatureFlagsResponse(BaseModel):
    """Response model for the admin feature‑flags status endpoint.

    Attributes
    ----------
    status: Dict[str, Any]
        Mapping of each feature flag key to its boolean enabled state.
    overrides: List[str]
        List of flag keys that are currently disabled via local overrides.
    """

    status: Dict[str, Any]
    overrides: List[str]


class FeatureFlagsUpdateRequest(BaseModel):
    """Request model for updating feature‑flag overrides.

    The ``disabled`` list contains the flag keys that the caller wishes to
    disable for the current tenant/environment. Validation of unknown keys is
    performed in the endpoint implementation.
    """

    disabled: List[str]


class FeatureFlagsUpdateResponse(BaseModel):
    """Response model after attempting to update feature‑flag overrides.

    Returns the current list of disabled overrides after the operation.
    """

    overrides: List[str]
    started_at_ms: Optional[int] = Field(
        None, description="Epoch ms when the run started"
    )
    mode: Optional[str] = Field(
        None, description="Sleep mode executed, e.g. 'nrem' or 'rem'"
    )
    details: Optional[Dict[str, Any]] = Field(
        None, description="Optional additional runtime details"
    )


class SleepStatusResponse(BaseModel):
    enabled: bool
    interval_seconds: int
    last: Dict[str, Optional[float]]


class SleepStatusAllResponse(BaseModel):
    enabled: bool
    interval_seconds: int
    tenants: Dict[str, Dict[str, Optional[float]]]


class MigrateImportResponse(BaseModel):
    imported: int
    wm_warmed: int


class ReflectResponse(BaseModel):
    created: int
    summaries: List[str]


class LinkResponse(BaseModel):
    ok: bool


class ActRequest(BaseModel):
    """
    Schema for action execution requests.

    Defines the structure for requests to execute cognitive actions or tasks,
    with optional universe filtering and result limiting.

    Attributes:
        task (str): Description of the task or action to perform.
        top_k (int): Number of top results to return. Default 3.
        universe (Optional[str]): Optional universe/namespace filter.

    Example:
        >>> request = ActRequest(task="analyze data", top_k=10, universe="analysis")
    """

    task: str
    top_k: int = 3
    universe: Optional[str] = None


class ActStepResult(BaseModel):
    """
    Schema for individual action step results.

    Represents the outcome of a single step in an action execution, including
    cognitive metrics and memory operation results.

    Attributes:
        step (str): Description of the action step performed.
        novelty (float): Novelty score for this step (0.0 to 1.0).
        pred_error (float): Prediction error for this step (0.0 to 1.0).
        salience (float): Salience score for this step.
        stored (bool): Whether this step was stored in memory.
        wm_hits (int): Number of working memory hits.
        memory_hits (int): Number of long-term memory hits.
        policy (Optional[dict]): Optional policy decision data.

    Example:
        >>> result = ActStepResult(
        ...     step="processed input",
        ...     novelty=0.2,
        ...     pred_error=0.1,
        ...     salience=0.8,
        ...     stored=True,
        ...     wm_hits=2,
        ...     memory_hits=5
        ... )
    """

    step: str
    novelty: float
    pred_error: float
    salience: float
    stored: bool
    wm_hits: int
    memory_hits: int
    policy: Optional[dict] = None


class ActResponse(BaseModel):
    """
    Schema for action execution responses.

    Defines the structure of responses from action execution, including step-by-step
    results and optional planning information.

    Attributes:
        task (str): Original task description.
        results (List[ActStepResult]): List of step results from execution.
        plan (Optional[List[str]]): Optional list of planned steps.
        plan_universe (Optional[str]): Universe associated with the plan.

    Example:
        >>> response = ActResponse(
        ...     task="solve problem",
        ...     results=[step_result1, step_result2],
        ...     plan=["step 1", "step 2", "step 3"]
        ... )
    """

    task: str
    results: List[ActStepResult]
    plan: Optional[List[str]] = None
    plan_universe: Optional[str] = None


class HealthResponse(BaseModel):
    """
    Schema for system health check responses.

    Provides a simple health status response with component-level status information
    for monitoring the system's operational state.

    Attributes:
        ok (bool): Overall system health status.
        components (dict): Dictionary of component names to their status information.

    Example:
        >>> response = HealthResponse(
        ...     ok=True,
        ...     components={"memory": "healthy", "wm": "healthy", "api": "healthy"}
        ... )
    """

    ok: bool
    components: dict
    namespace: Optional[str] = None
    trace_id: Optional[str] = None
    deadline_ms: Optional[str] = None
    idempotency_key: Optional[str] = None
    constitution_version: Optional[str] = None
    constitution_status: Optional[str] = None
    minimal_public_api: Optional[bool] = None
    external_backends_required: Optional[bool] = None
    predictor_provider: Optional[str] = None
    full_stack: Optional[bool] = None
    embedder: Optional[Dict[str, Any]] = None
    stub_counts: Optional[Dict[str, int]] = None
    ready: Optional[bool] = None
    memory_items: Optional[int] = None
    predictor_ok: Optional[bool] = None
    memory_ok: Optional[bool] = None
    embedder_ok: Optional[bool] = None
    # Retrieval readiness: lightweight probe combining embedder + vector recall path
    retrieval_ready: Optional[bool] = None
    # Extended diagnostics
    opa_ok: Optional[bool] = None
    opa_required: Optional[bool] = None
    kafka_ok: Optional[bool] = None
    postgres_ok: Optional[bool] = None
    metrics_ready: Optional[bool] = None
    metrics_required: Optional[list[str]] = None
    alerts: Optional[list[str]] = None
    memory_circuit_open: Optional[bool] = None
    fd_trace_norm_error: Optional[float] = None
    fd_psd_ok: Optional[bool] = None
    fd_capture_ratio: Optional[float] = None
    scorer: Optional[Dict[str, Any]] = None


class PersonalityState(BaseModel):
    """
    Schema for personality trait states.

    Represents normalized personality traits in the cognitive system. Trait values
    should be floats in ``[0.0, 1.0]``. Additional traits are allowed but must also
    be numeric.

    Attributes:
        traits (dict[str, Any]): Dictionary of personality trait names to their values.
                                Default empty dict.

    Example:
        >>> state = PersonalityState(traits={"openness": 0.8, "conscientiousness": 0.6})
    """

    traits: Dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_traits(self):
        validated: Dict[str, float] = {}
        for k, v in (self.traits or {}).items():
            try:
                fv = float(v)
            except Exception as exc:
                raise ValueError(f"Trait '{k}' must be numeric") from exc
            if not 0.0 <= fv <= 1.0:
                raise ValueError(f"Trait '{k}' must be in [0,1]")
            validated[k] = fv
        object.__setattr__(self, "traits", validated)
        return self


class Persona(BaseModel):
    """
    Persona record schema used by the Persona endpoints.

    Attributes:
        id: identifier for the persona (path param)
        display_name: optional human-readable name
        properties: arbitrary dict with persona data
        fact: metadata field set to 'persona' when persisted
    """

    id: str
    display_name: str | None = None
    properties: dict[str, Any] = {}
    fact: str = "persona"


class MigrateExportRequest(BaseModel):
    """
    Schema for data export requests.

    Defines parameters for exporting system data including memories and working memory
    for backup, migration, or analysis purposes.

    Attributes:
        include_wm (bool): Whether to include working memory in export. Default True.
        wm_limit (int): Maximum number of working memory items to export. Default 128.

    Example:
        >>> request = MigrateExportRequest(include_wm=True, wm_limit=256)
    """

    include_wm: bool = True
    wm_limit: int = 128


class MigrateExportResponse(BaseModel):
    """
    Schema for export operation responses.

    Contains the exported data including manifest, memories, and working memory items.

    Attributes:
        manifest (dict): Metadata about the export operation.
        memories (list[dict]): List of exported memory items.
        wm (list[dict]): List of exported working memory items. Default empty.

    Example:
        >>> response = MigrateExportResponse(
        ...     manifest={"version": "1.0", "timestamp": 1234567890},
        ...     memories=[memory1, memory2],
        ...     wm=[wm_item1, wm_item2]
        ... )
    """

    manifest: dict
    memories: list[dict]
    wm: list[dict] = []


class MigrateImportRequest(BaseModel):
    """
    Schema for data import requests.

    Defines the structure for importing previously exported data back into the system,
    with options for replacement or merging.

    Attributes:
        manifest (dict): Metadata from the export operation.
        memories (list[dict]): List of memory items to import.
        wm (list[dict]): List of working memory items to import. Default empty.
        replace (bool): Whether to replace existing data or merge. Default False.

    Example:
        >>> request = MigrateImportRequest(
        ...     manifest={"version": "1.0"},
        ...     memories=[memory1, memory2],
        ...     wm=[wm_item1],
        ...     replace=False
        ... )
    """

    manifest: dict
    memories: list[dict]
    wm: list[dict] = []
    replace: bool = False


class NeuromodStateModel(BaseModel):
    """
    Schema for neuromodulator state representation.

    Represents the current levels of key neuromodulators in the cognitive system,
    used for API serialization and state monitoring.

    Attributes:
        dopamine (float): Dopamine level (0.0 to 1.0). Default 0.4.
        serotonin (float): Serotonin level (0.0 to 1.0). Default 0.5.
        noradrenaline (float): Noradrenaline level (0.0 to 1.0). Default 0.0.
        acetylcholine (float): Acetylcholine level (0.0 to 1.0). Default 0.0.

    Example:
        >>> state = NeuromodStateModel(
        ...     dopamine=0.6,
        ...     serotonin=0.7,
        ...     noradrenaline=0.1,
        ...     acetylcholine=0.2
        ... )
    """

    dopamine: float = 0.4
    serotonin: float = 0.5
    noradrenaline: float = 0.0
    acetylcholine: float = 0.0


class DeleteRequest(BaseModel):
    """Schema for delete memory requests.

    Attributes:
        coordinate: 3-element list representing the memory coordinate to delete.
    """

    coordinate: List[float]


class DeleteResponse(BaseModel):
    """Simple response indicating delete success.

    Attributes:
        ok: True if delete operation was performed.
    """

    ok: bool = True


class OutboxEventModel(BaseModel):
    """Admin-facing view of an outbox event."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    topic: str
    status: str
    tenant_id: Optional[str] = None
    dedupe_key: str
    retries: Optional[int] = None
    created_at: Optional[datetime] = None
    last_error: Optional[str] = None
    payload: Dict[str, Any]


class OutboxListResponse(BaseModel):
    events: List[OutboxEventModel]
    count: int


class OutboxReplayRequest(BaseModel):
    event_ids: List[int] = Field(..., min_length=1, max_length=1000)


class OutboxReplayResponse(BaseModel):
    replayed: int


class OutboxTenantReplayRequest(BaseModel):
    """Request to replay outbox events for a specific tenant with filtering."""
    
    tenant_id: str = Field(..., description="Tenant ID to replay events for")
    status: str = Field("failed", description="Status to filter: pending|failed|sent")
    topic_filter: Optional[str] = Field(None, description="Optional topic pattern filter")
    before_timestamp: Optional[datetime] = Field(None, description="Only replay events before this time")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of events to replay")


class OutboxTenantReplayResponse(BaseModel):
    """Response from tenant-specific outbox replay operation."""
    
    tenant_id: str
    replayed: int
    status: str


class OutboxTenantListResponse(BaseModel):
    """Response for tenant-specific outbox event listing."""
    
    tenant_id: str
    events: List[OutboxEventModel]
    count: int
    status: str


class OutboxTenantSummary(BaseModel):
    """Summary statistics for a single tenant's outbox events."""
    
    tenant_id: str
    pending_count: int
    failed_count: int
    sent_count: int
    total_count: int


class OutboxSummaryResponse(BaseModel):
    """Summary statistics for outbox events across all tenants."""
    
    tenants: List[OutboxTenantSummary]
    total_tenants: int
    total_pending: int
    total_failed: int
    total_sent: int


class QuotaStatus(BaseModel):
    """Per-tenant quota status for admin monitoring."""
    
    tenant_id: str
    daily_limit: int
    remaining: Union[int, float]  # Allow float('inf') for exempt tenants
    used_today: int
    reset_at: Optional[datetime] = None
    is_exempt: bool = False


class QuotaListResponse(BaseModel):
    """Response for listing all tenant quotas."""
    
    quotas: List[QuotaStatus]
    total_tenants: int


class QuotaResetRequest(BaseModel):
    """Request to reset a tenant's quota."""
    
    reason: Optional[str] = Field(None, description="Reason for quota reset")


class QuotaResetResponse(BaseModel):
    """Response after quota reset."""
    
    tenant_id: str
    reset: bool
    new_remaining: int
    message: str


class QuotaAdjustRequest(BaseModel):
    """Request to adjust a tenant's quota limit."""
    
    new_limit: int = Field(..., gt=0, description="New daily quota limit")
    reason: Optional[str] = Field(None, description="Reason for quota adjustment")


class QuotaAdjustResponse(BaseModel):
    """Response after quota adjustment."""
    
    tenant_id: str
    old_limit: int
    new_limit: int
    adjusted: bool
    message: str
