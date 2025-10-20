from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class RecallRequest(BaseModel):
    query: str
    top_k: int = 3
    universe: Optional[str] = None


class MemoryPayload(BaseModel):
    # Minimal episodic payload
    task: Optional[str] = None
    importance: int = 1
    memory_type: str = "episodic"
    timestamp: Optional[float] = None
    universe: Optional[str] = None
    # Optional event tuple fields
    who: Optional[str] = None
    did: Optional[str] = None
    what: Optional[str] = None
    where: Optional[str] = None
    when: Optional[str] = None
    why: Optional[str] = None


class RememberRequest(BaseModel):
    coord: Optional[str] = Field(None, description="x,y,z; optional — auto if omitted")
    payload: MemoryPayload


class ActRequest(BaseModel):
    task: str
    top_k: int = 3
    universe: Optional[str] = None


class ActStepResult(BaseModel):
    step: str
    novelty: float
    pred_error: float
    salience: float
    stored: bool
    wm_hits: int
    memory_hits: int
    policy: Optional[dict] = None


class ActResponse(BaseModel):
    task: str
    results: List[ActStepResult]
    plan: Optional[List[str]] = None
    plan_universe: Optional[str] = None


class HealthResponse(BaseModel):
    ok: bool
    components: dict


class PersonalityState(BaseModel):
    # MVP placeholder
    traits: dict[str, Any] = {}


class MigrateExportRequest(BaseModel):
    include_wm: bool = True
    wm_limit: int = 128


class MigrateExportResponse(BaseModel):
    manifest: dict
    memories: list[dict]
    wm: list[dict] = []


class MigrateImportRequest(BaseModel):
    manifest: dict
    memories: list[dict]
    wm: list[dict] = []
    replace: bool = False


class NeuromodStateModel(BaseModel):
    dopamine: float = 0.4
    serotonin: float = 0.5
    noradrenaline: float = 0.0
    acetylcholine: float = 0.0
