# Design Document: Unified Planning Kernel

## Introduction

This document specifies the technical design for the Unified Planning Kernel and FocusState integration. The design addresses 12 requirements from `requirements.md`, fixing critical VIBE violations and wiring existing infrastructure.

**VIBE COMPLIANCE PRINCIPLE:** This design uses ONLY existing, working infrastructure:
- `GraphClient` from `somabrain/somabrain/memory/graph_client.py` - FULLY IMPLEMENTED
- `HRRContext` from `somabrain/somabrain/context/context_hrr.py` - FULLY IMPLEMENTED
- SFM endpoints `/graph/link`, `/graph/neighbors`, `/graph/path` - EXIST AND WORK

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Cognitive Router                                   │
│                    /plan/suggest, /act endpoints                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PlanEngine                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ GraphPlanner│  │ContextPlan │  │ OptionPlan  │  │ ActionPlan  │        │
│  │  (BFS/RWR)  │  │   (util)   │  │  (ranking)  │  │  (sequence) │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│         │                                                                    │
│         │ USES EXISTING                                                      │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              GraphClient (ALREADY IMPLEMENTED)                       │   │
│  │  • get_neighbors() → SFM /graph/neighbors                           │   │
│  │  • create_link() → SFM /graph/link                                  │   │
│  │  • find_path() → SFM /graph/path                                    │   │
│  │  • outbox queue for retry (ALREADY IMPLEMENTED)                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FocusState                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              HRRContext (ALREADY IMPLEMENTED)                        │   │
│  │  • context vector (superposition)                                    │   │
│  │  • anchors (LRU bounded)                                             │   │
│  │  • exponential decay                                                 │   │
│  │  • novelty scoring                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  • current_focus_vec / previous_focus_vec (NEW - session tracking)          │
│  • focus_digest (NEW - deterministic hash)                                  │
│  • persistence gate (NEW)                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component 1: Fix Planner BFS - Wire to GraphClient (Requirement 1)

**File**: `somabrain/somabrain/planner.py` (REPLACE STUB)

**Current VIBE Violation**:
```python
# VIOLATION: Hardcoded return with FALSE documentation
return []  # Claims "endpoints don't exist" - THIS IS A LIE
```

**Fix - Use Existing GraphClient**:
```python
"""Graph-Informed Planner Module - REAL IMPLEMENTATION."""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from somabrain.memory.graph_client import GraphClient, GraphNeighbor
from somabrain.metrics.planning import PLAN_GRAPH_UNAVAILABLE, PLAN_LATENCY

logger = logging.getLogger(__name__)


def plan_from_graph(
    task_key: str,
    graph_client: GraphClient,
    start_coord: Tuple[float, ...],
    max_steps: int = 5,
    rel_types: Optional[List[str]] = None,
    graph_limit: int = 10,
) -> List[str]:
    """
    BFS graph traversal for planning using EXISTING GraphClient.
    
    This function uses the fully-implemented GraphClient which connects
    to SFM's /graph/neighbors endpoint. NO STUBS, NO MOCKS.
    """
    if graph_client is None:
        PLAN_GRAPH_UNAVAILABLE.inc()
        logger.warning("GraphClient not provided - cannot plan")
        return []
    
    visited: set[str] = set()
    queue: List[Tuple[Tuple[float, ...], int]] = [(start_coord, 0)]
    results: List[str] = []
    
    while queue and len(results) < max_steps:
        current_coord, depth = queue.pop(0)
        coord_str = _coord_to_str(current_coord)
        
        if coord_str in visited:
            continue
        visited.add(coord_str)
        
        # USE EXISTING GraphClient.get_neighbors()
        neighbors: List[GraphNeighbor] = graph_client.get_neighbors(
            coord=current_coord,
            k_hop=1,
            limit=graph_limit,
            link_type=rel_types[0] if rel_types else None,
        )
        
        # Filter by rel_types if specified
        if rel_types and len(rel_types) > 1:
            neighbors = [n for n in neighbors if n.link_type in rel_types]
        
        # Deterministic ordering: strength desc, then coord string
        neighbors.sort(key=lambda n: (-n.strength, _coord_to_str(n.coord)))
        
        for neighbor in neighbors:
            if len(results) >= max_steps:
                break
            neighbor_str = _coord_to_str(neighbor.coord)
            if neighbor_str not in visited:
                # Extract task from metadata if available
                task_str = _extract_task_from_neighbor(neighbor)
                if task_str:
                    results.append(task_str)
                queue.append((neighbor.coord, depth + 1))
    
    return results


def _coord_to_str(coord: Tuple[float, ...]) -> str:
    """Convert coordinate tuple to string for set membership."""
    return ",".join(f"{c:.6f}" for c in coord)


def _extract_task_from_neighbor(neighbor: GraphNeighbor) -> Optional[str]:
    """Extract task string from neighbor metadata."""
    if neighbor.metadata:
        return neighbor.metadata.get("task") or neighbor.metadata.get("text")
    return _coord_to_str(neighbor.coord)
```

## Component 2: Fix RWR Planner - Wire to GraphClient (Requirement 2)

**File**: `somabrain/somabrain/planner_rwr.py` (REPLACE STUB)


**Current VIBE Violation**:
```python
# VIOLATION: Hardcoded return with FALSE documentation
return []  # Claims "/neighbors endpoint does not exist" - THIS IS A LIE
```

**Fix - Use Existing GraphClient**:
```python
"""Random Walk with Restart Planner - REAL IMPLEMENTATION."""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np

from somabrain.memory.graph_client import GraphClient, GraphNeighbor
from somabrain.metrics.planning import PLAN_GRAPH_UNAVAILABLE

logger = logging.getLogger(__name__)


def rwr_plan(
    task_key: str,
    graph_client: GraphClient,
    start_coord: Tuple[float, ...],
    steps: int = 20,
    restart: float = 0.15,
    max_nodes: int = 100,
    max_items: int = 5,
) -> List[str]:
    """
    Random Walk with Restart planning using EXISTING GraphClient.
    
    This function uses the fully-implemented GraphClient which connects
    to SFM's /graph/neighbors endpoint. NO STUBS, NO MOCKS.
    """
    if graph_client is None:
        PLAN_GRAPH_UNAVAILABLE.inc()
        logger.warning("GraphClient not provided - cannot plan")
        return []
    
    # Build local subgraph using GraphClient.get_neighbors()
    nodes, edges = _build_local_subgraph(graph_client, start_coord, max_nodes)
    
    if len(nodes) < 2:
        logger.debug("Subgraph too small for RWR", node_count=len(nodes))
        return []
    
    # Initialize probability vector
    n = len(nodes)
    node_list = list(nodes.keys())
    start_idx = node_list.index(_coord_to_str(start_coord))
    
    p = np.zeros(n, dtype=np.float64)
    p[start_idx] = 1.0
    
    # Build transition matrix
    T = _build_transition_matrix(nodes, edges, node_list)
    
    # Power iteration with restart
    for _ in range(steps):
        p_new = (1 - restart) * (T @ p)
        p_new[start_idx] += restart
        p = p_new / (np.sum(p_new) + 1e-12)
    
    # Rank nodes by probability (exclude start)
    ranked = sorted(
        [(i, p[i]) for i in range(n) if i != start_idx],
        key=lambda x: (-x[1], node_list[x[0]]),  # Deterministic tie-break
    )
    
    # Extract task strings
    results: List[str] = []
    for idx, prob in ranked[:max_items]:
        coord_str = node_list[idx]
        task_str = nodes[coord_str].get("task") or coord_str
        results.append(task_str)
    
    return results


def _build_local_subgraph(
    graph_client: GraphClient,
    start_coord: Tuple[float, ...],
    max_nodes: int,
) -> Tuple[dict, List[Tuple[str, str, float]]]:
    """Build local subgraph using GraphClient.get_neighbors()."""
    nodes: dict = {}
    edges: List[Tuple[str, str, float]] = []
    queue = [start_coord]
    
    while queue and len(nodes) < max_nodes:
        coord = queue.pop(0)
        coord_str = _coord_to_str(coord)
        
        if coord_str in nodes:
            continue
        
        nodes[coord_str] = {"coord": coord}
        
        # USE EXISTING GraphClient.get_neighbors()
        neighbors = graph_client.get_neighbors(coord, k_hop=1, limit=20)
        
        for neighbor in neighbors:
            neighbor_str = _coord_to_str(neighbor.coord)
            edges.append((coord_str, neighbor_str, neighbor.strength))
            if neighbor_str not in nodes and len(nodes) < max_nodes:
                queue.append(neighbor.coord)
    
    return nodes, edges


def _build_transition_matrix(
    nodes: dict,
    edges: List[Tuple[str, str, float]],
    node_list: List[str],
) -> np.ndarray:
    """Build row-stochastic transition matrix."""
    n = len(node_list)
    node_idx = {node: i for i, node in enumerate(node_list)}
    T = np.zeros((n, n), dtype=np.float64)
    
    for from_node, to_node, strength in edges:
        if from_node in node_idx and to_node in node_idx:
            T[node_idx[to_node], node_idx[from_node]] = strength
    
    # Normalize columns
    col_sums = T.sum(axis=0)
    col_sums[col_sums == 0] = 1.0
    T = T / col_sums
    
    return T


def _coord_to_str(coord: Tuple[float, ...]) -> str:
    """Convert coordinate tuple to string."""
    return ",".join(f"{c:.6f}" for c in coord)
```

## Component 3: Fix Predictor Self-Comparison Bug (Requirement 3)

**File**: `somabrain/somabrain/services/cognitive_loop_service.py`

**Current Bug (line 137)**:
```python
pred = predictor.predict_and_compare(wm_vec, wm_vec)  # WRONG: compares to itself
```

**Fix**:
```python
def eval_step(
    novelty: float,
    wm_vec: np.ndarray,
    previous_focus_vec: Optional[np.ndarray],  # NEW PARAMETER
    cfg,
    predictor,
    neuromods,
    personality_store,
    supervisor: Optional[object],
    amygdala,
    tenant_id: str,
) -> Dict[str, Any]:
    """Evaluate cognitive step with CORRECT prediction comparison."""
    result: Dict[str, Any] = {}
    
    # FIX: Compare previous focus to current focus (NOT wm_vec to itself)
    if previous_focus_vec is None:
        # First step in session - no previous focus
        PREDICT_COMPARE_MISSING_PREV.inc()
        pred_error = 0.0
        result["no_prev_focus"] = True
    else:
        pred = predictor.predict_and_compare(previous_focus_vec, wm_vec)
        pred_error = pred.error
    
    # Rest of eval_step logic...
```

## Component 4: Fix Settings Mismatch (Requirement 4)

**File**: `somabrain/somabrain/services/planning_service.py`

**Current Bug (lines 77-78)**:
```python
steps=int(getattr(cfg, "rwr_steps", 20) or 20),      # WRONG
restart=float(getattr(cfg, "rwr_restart", 0.15) or 0.15),  # WRONG
```

**Fix**:
```python
steps=int(getattr(cfg, "planner_rwr_steps", 20) or 20),
restart=float(getattr(cfg, "planner_rwr_restart", 0.15) or 0.15),
```

## Component 5: Add Missing Planner Settings (Requirement 5)

**File**: `somabrain/common/config/settings/cognitive.py`

**New Settings**:
```python
# Planning kernel settings
use_planner: bool = Field(
    default_factory=lambda: _bool_env("SOMABRAIN_USE_PLANNER", False)
)
use_focus_state: bool = Field(
    default_factory=lambda: _bool_env("SOMABRAIN_USE_FOCUS_STATE", True)
)
plan_max_steps: int = Field(
    default_factory=lambda: _int_env("SOMABRAIN_PLAN_MAX_STEPS", 5)
)
planner_backend: str = Field(
    default_factory=lambda: _str_env("SOMABRAIN_PLANNER_BACKEND", "bfs")
)
plan_time_budget_ms: int = Field(
    default_factory=lambda: _int_env("SOMABRAIN_PLAN_TIME_BUDGET_MS", 50)
)
plan_max_options: int = Field(
    default_factory=lambda: _int_env("SOMABRAIN_PLAN_MAX_OPTIONS", 10)
)
plan_rel_types: str = Field(
    default_factory=lambda: _str_env("SOMABRAIN_PLAN_REL_TYPES", "")
)
focus_decay_gamma: float = Field(
    default_factory=lambda: _float_env("SOMABRAIN_FOCUS_DECAY_GAMMA", 0.90)
)
focus_persist: bool = Field(
    default_factory=lambda: _bool_env("SOMABRAIN_FOCUS_PERSIST", False)
)
focus_links: bool = Field(
    default_factory=lambda: _bool_env("SOMABRAIN_FOCUS_LINKS", False)
)
focus_admit_top_n: int = Field(
    default_factory=lambda: _int_env("SOMABRAIN_FOCUS_ADMIT_TOP_N", 4)
)
```


## Component 6: PlanEngine (Requirement 6)

**File**: `somabrain/somabrain/services/plan_engine.py` (NEW - justified: single entrypoint)

```python
"""Unified Plan Engine - Single entrypoint for all planning."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from somabrain.memory.graph_client import GraphClient
from somabrain.metrics.planning import PLAN_LATENCY, PLAN_EMPTY
from somabrain.planner import plan_from_graph
from somabrain.planner_rwr import rwr_plan

logger = logging.getLogger(__name__)


@dataclass
class PlanRequestContext:
    """Input context for planning."""
    tenant_id: str
    task_key: str
    task_vec: np.ndarray
    start_coord: tuple
    focus_vec: Optional[np.ndarray] = None
    time_budget_ms: int = 50
    max_steps: int = 5
    rel_types: List[str] = field(default_factory=list)
    universe: Optional[str] = None


@dataclass
class CompositePlan:
    """Composite plan output with multiple artifacts."""
    graph_plan: List[str] = field(default_factory=list)
    context_plan: List[str] = field(default_factory=list)
    option_plan: List[str] = field(default_factory=list)
    action_plan: List[str] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    
    def to_legacy_steps(self) -> List[str]:
        """Backward-compatible flat list."""
        if self.graph_plan:
            return self.graph_plan
        if self.context_plan:
            return self.context_plan
        if self.option_plan:
            return self.option_plan
        return self.action_plan


class PlanEngine:
    """Single planning entrypoint using EXISTING infrastructure."""
    
    def __init__(self, cfg, graph_client: Optional[GraphClient] = None):
        self._cfg = cfg
        self._graph = graph_client
    
    def plan(self, ctx: PlanRequestContext) -> CompositePlan:
        """Execute planning with time budget."""
        t0 = time.perf_counter()
        deadline = t0 + (ctx.time_budget_ms / 1000.0)
        
        result = CompositePlan()
        backend = str(getattr(self._cfg, "planner_backend", "bfs")).lower()
        
        try:
            if time.perf_counter() < deadline:
                if backend == "rwr":
                    result.graph_plan = rwr_plan(
                        task_key=ctx.task_key,
                        graph_client=self._graph,
                        start_coord=ctx.start_coord,
                        steps=getattr(self._cfg, "planner_rwr_steps", 20),
                        restart=getattr(self._cfg, "planner_rwr_restart", 0.15),
                        max_items=ctx.max_steps,
                    )
                else:
                    result.graph_plan = plan_from_graph(
                        task_key=ctx.task_key,
                        graph_client=self._graph,
                        start_coord=ctx.start_coord,
                        max_steps=ctx.max_steps,
                        rel_types=ctx.rel_types if ctx.rel_types else None,
                    )
        except Exception as exc:
            logger.warning(f"Planning failed: {exc}")
            result.diagnostics["error"] = str(exc)
        
        result.elapsed_ms = (time.perf_counter() - t0) * 1000
        PLAN_LATENCY.labels(backend=backend).observe(result.elapsed_ms / 1000)
        
        if not result.to_legacy_steps():
            reason = result.diagnostics.get("error", "empty_graph")
            PLAN_EMPTY.labels(reason=reason).inc()
        
        return result
```

## Component 7: FocusState Module (Requirement 7)

**File**: `somabrain/somabrain/focus_state.py` (NEW - justified: canonical WM signal)

```python
"""FocusState - Canonical working-memory focus signal."""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from somabrain.context.context_hrr import HRRContext
from somabrain.memory.graph_client import GraphClient
from somabrain.metrics.planning import FOCUS_UPDATE_LATENCY, FOCUS_PERSIST

logger = logging.getLogger(__name__)


class FocusState:
    """
    Canonical working-memory focus signal using EXISTING HRRContext.
    
    FocusState WRAPS HRRContext (composition, not inheritance).
    HRRContext handles: superposition, decay, cleanup, novelty
    FocusState adds: session tracking, previous/current vectors, persistence
    """
    
    def __init__(
        self,
        hrr_context: HRRContext,
        cfg,
        *,
        session_id: str,
        tenant_id: str,
    ):
        self._hrr = hrr_context  # EXISTING, WORKING
        self._cfg = cfg
        self._session_id = session_id
        self._tenant_id = tenant_id
        self._previous_focus_vec: Optional[np.ndarray] = None
        self._current_focus_vec: Optional[np.ndarray] = None
        self._focus_digest: Optional[str] = None
        self._tick = 0
    
    def update(
        self,
        task_vec: np.ndarray,
        recall_hits: List[Tuple[str, np.ndarray]],
        *,
        timestamp: Optional[float] = None,
    ) -> None:
        """Update focus with task embedding and top-N recall hits."""
        t0 = time.perf_counter()
        
        # Save previous
        self._previous_focus_vec = self._current_focus_vec
        
        # Admit task as primary anchor via EXISTING HRRContext
        self._hrr.admit(f"task_{self._tick}", task_vec, timestamp=timestamp)
        
        # Admit top-N recall hits deterministically (sorted by ID)
        top_n = int(getattr(self._cfg, "focus_admit_top_n", 4))
        sorted_hits = sorted(recall_hits, key=lambda x: x[0])[:top_n]
        for hit_id, hit_vec in sorted_hits:
            self._hrr.admit(hit_id, hit_vec, timestamp=timestamp)
        
        # Update current focus from HRRContext
        self._current_focus_vec = self._hrr.context.copy()
        
        # Compute deterministic digest
        self._focus_digest = self._compute_digest(self._current_focus_vec)
        self._tick += 1
        
        FOCUS_UPDATE_LATENCY.observe(time.perf_counter() - t0)
    
    def _compute_digest(self, vec: np.ndarray) -> str:
        """Deterministic hash of focus vector."""
        quantized = np.round(vec, 4)
        return hashlib.sha256(quantized.tobytes()).hexdigest()[:16]
    
    @property
    def current_focus_vec(self) -> Optional[np.ndarray]:
        return self._current_focus_vec
    
    @property
    def previous_focus_vec(self) -> Optional[np.ndarray]:
        return self._previous_focus_vec
    
    @property
    def focus_digest(self) -> Optional[str]:
        return self._focus_digest
    
    def novelty(self, vec: np.ndarray) -> float:
        """Compute novelty via EXISTING HRRContext."""
        return self._hrr.novelty(vec)
    
    def persist_snapshot(
        self,
        mem_client,
        *,
        store_gate: bool,
        universe: Optional[str] = None,
    ) -> Optional[str]:
        """Persist focus snapshot to memory if gate allows."""
        if not getattr(self._cfg, "focus_persist", False):
            return None
        if not store_gate:
            return None
        if self._current_focus_vec is None:
            return None
        
        try:
            payload = {
                "type": "focus_snapshot",
                "session_id": self._session_id,
                "tick": self._tick,
                "focus_digest": self._focus_digest,
                "timestamp": time.time(),
                # NO raw user text - privacy safe
            }
            
            coord = mem_client.store(
                vec=self._current_focus_vec,
                payload=payload,
                memory_type="episodic",
                universe=universe,
            )
            
            FOCUS_PERSIST.inc()
            return coord
        except Exception as exc:
            logger.warning(f"Focus persist failed (non-fatal): {exc}")
            return None
    
    def create_links(
        self,
        graph_client: Optional[GraphClient],
        current_coord: Optional[str],
        previous_coord: Optional[str],
        used_memory_ids: List[str],
        selected_option_ids: List[str],
    ) -> None:
        """Create focus chain links using EXISTING GraphClient."""
        if not getattr(self._cfg, "focus_links", False):
            return
        if graph_client is None:
            return
        
        # "next" edge between consecutive snapshots
        if previous_coord and current_coord:
            graph_client.create_link(
                from_coord=self._str_to_coord(previous_coord),
                to_coord=self._str_to_coord(current_coord),
                link_type="next",
                strength=1.0,
            )
        
        # "attends_to" edges to used memories
        if current_coord:
            for mem_id in used_memory_ids:
                mem_coord = self._id_to_coord(mem_id)
                if mem_coord:
                    graph_client.create_link(
                        from_coord=self._str_to_coord(current_coord),
                        to_coord=mem_coord,
                        link_type="attends_to",
                        strength=0.8,
                    )
    
    def _str_to_coord(self, coord_str: str) -> Tuple[float, ...]:
        """Convert string to coordinate tuple."""
        return tuple(float(c) for c in coord_str.split(","))
    
    def _id_to_coord(self, mem_id: str) -> Optional[Tuple[float, ...]]:
        """Convert memory ID to coordinate if possible."""
        try:
            return self._str_to_coord(mem_id)
        except (ValueError, AttributeError):
            return None
```


## Component 8: Planning Metrics (Requirement 11)

**File**: `somabrain/somabrain/metrics/planning.py` (NEW - justified: metrics module)

```python
"""Planning and FocusState metrics."""
from prometheus_client import Counter, Histogram

PLAN_LATENCY = Histogram(
    "somabrain_plan_latency_seconds",
    "Planning latency",
    ["backend"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25],
)

PLAN_EMPTY = Counter(
    "somabrain_plan_empty_total",
    "Empty plan results",
    ["reason"],
)

PLAN_GRAPH_UNAVAILABLE = Counter(
    "somabrain_plan_graph_unavailable_total",
    "Graph unavailable for planning",
)

FOCUS_UPDATE_LATENCY = Histogram(
    "somabrain_focus_update_latency_seconds",
    "Focus update latency",
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01],
)

FOCUS_PERSIST = Counter(
    "somabrain_focus_persist_total",
    "Focus snapshots persisted",
)

PREDICT_COMPARE_MISSING_PREV = Counter(
    "somabrain_predict_compare_missing_prev_total",
    "Prediction comparisons with missing previous focus",
)
```

## File Changes Summary

| File | Action | Reason |
|------|--------|--------|
| `planner.py` | REPLACE | Remove stub, wire to GraphClient |
| `planner_rwr.py` | REPLACE | Remove stub, wire to GraphClient |
| `services/cognitive_loop_service.py` | MODIFY | Fix predictor self-comparison bug |
| `services/planning_service.py` | MODIFY | Fix settings mismatch |
| `common/config/settings/cognitive.py` | MODIFY | Add missing planner settings |
| `services/plan_engine.py` | CREATE | Single planning entrypoint |
| `focus_state.py` | CREATE | Canonical WM signal |
| `metrics/planning.py` | CREATE | Planning observability |

## Dependencies (ALL EXISTING, ALL WORKING)

| Component | Location | Status |
|-----------|----------|--------|
| GraphClient | `memory/graph_client.py` | FULLY IMPLEMENTED |
| HRRContext | `context/context_hrr.py` | FULLY IMPLEMENTED |
| SFM /graph/neighbors | SomaFractalMemory | EXISTS, WORKS |
| SFM /graph/link | SomaFractalMemory | EXISTS, WORKS |
| SFM /graph/path | SomaFractalMemory | EXISTS, WORKS |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: No Hardcoded Returns
*For any* call to `plan_from_graph` or `rwr_plan`, the function SHALL NOT contain `return []` as a hardcoded stub.
**Validates: Requirements 1.7, 2.5**

### Property 2: GraphClient Usage
*For any* planning operation, the system SHALL use the existing `GraphClient.get_neighbors()` method (NOT create new HTTP calls).
**Validates: Requirements 1.2, 2.1**

### Property 3: Predictor Comparison Correctness
*For any* cognitive loop evaluation where previous_focus_vec exists, the predictor SHALL compare previous_focus_vec against current wm_vec (NOT wm_vec against itself).
**Validates: Requirement 3.1**

### Property 4: Settings Correctness
*For any* RWR planning operation, the system SHALL read `planner_rwr_steps` and `planner_rwr_restart` (NOT `rwr_steps` and `rwr_restart`).
**Validates: Requirements 4.1, 4.2**

### Property 5: Deterministic Ordering
*For any* set of graph neighbors, sorting by (-strength, coord_string) SHALL produce identical ordering across runs.
**Validates: Requirements 1.5, 2.4**

### Property 6: FocusState Wraps HRRContext
*For any* FocusState instance, it SHALL delegate vector operations to an HRRContext instance (composition, not duplication).
**Validates: Requirement 7.1**

### Property 7: Focus Digest Determinism
*For any* identical sequence of inputs to FocusState.update(), the resulting focus_digest SHALL be identical.
**Validates: Requirement 7.7**

## Error Handling

- GraphClient unavailable → Return empty plan with metric increment (graceful degradation)
- HRRContext failure → Log warning, continue with existing wm_vec
- Persistence failure → Log warning, continue without failing request
- Time budget exceeded → Return partial results with diagnostics

## Testing Strategy

1. **Unit tests** - Test each component with REAL infrastructure (per VIBE rules)
2. **Integration tests** - Full planning flow with real SFM
3. **Property tests** - Verify determinism and correctness properties
4. **VIBE compliance check** - Grep for `return []` stubs, FALSE documentation
