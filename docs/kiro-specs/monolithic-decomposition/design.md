# Design Document - Monolithic File Decomposition

## Overview

This design document outlines the architecture and approach for decomposing monolithic files in the SomaBrain codebase. The decomposition follows a modular extraction pattern that preserves backward compatibility while improving maintainability.

## Architecture

### Target File Analysis

| File | Current Lines | Target Lines | Extraction Strategy |
|------|---------------|--------------|---------------------|
| `somabrain/app.py` | 4052 | <800 | Router extraction, class extraction, helper extraction |
| `somabrain/memory_client.py` | 2216 | <500 | Transport/client separation |
| `somabrain/metrics_original.py` | 1698 | <500 | Domain-based metric grouping |
| `somabrain/api/memory_api.py` | 1615 | <500 | Endpoint grouping, model extraction |
| `somabrain/learning/adaptation.py` | 1071 | <500 | Engine/config separation |
| `somabrain/schemas.py` | 1003 | <500 | Domain-based schema grouping |

### Extraction Principles

1. **Single Responsibility**: Each extracted module handles one concern
2. **Backward Compatibility**: Re-export from original location via `__init__.py`
3. **Lazy Imports**: Use function-level imports to avoid circular dependencies
4. **DI Container**: Register singletons with `somabrain/core/container.py`
5. **Settings Integration**: All configuration via centralized Settings

## Components and Interfaces

### 1. app.py Decomposition

```
somabrain/
├── app.py                    # Main FastAPI app, startup/shutdown, <800 lines
├── routers/
│   ├── __init__.py
│   ├── admin.py              # Already exists - admin endpoints
│   ├── health.py             # Health/diagnostics endpoints (extract)
│   ├── memory_ops.py         # remember/recall/delete endpoints (extract)
│   ├── cognitive.py          # plan/act/neuromodulators endpoints (extract)
│   └── oak.py                # OAK option endpoints (extract)
├── services/
│   ├── unified_brain.py      # UnifiedBrainCore class (extract)
│   ├── complexity_detector.py # ComplexityDetector class (extract)
│   └── fractal_intelligence.py # AutoScalingFractalIntelligence (extract)
├── helpers/
│   ├── __init__.py
│   ├── scoring.py            # _score_memory_candidate, _apply_diversity_reranking
│   ├── payload.py            # _extract_text_from_candidate, _normalize_payload_timestamps
│   └── wm_support.py         # _build_wm_support_index, _collect_candidate_keys
└── lifecycle/
    ├── __init__.py
    ├── startup.py            # _startup_mode_banner, _init_* functions
    └── watchdog.py           # _health_watchdog_coroutine, memory watchdog
```

### 2. memory_client.py Decomposition

```
somabrain/memory/
├── __init__.py               # Re-exports MemoryClient, RecallHit
├── transport.py              # MemoryHTTPTransport class
├── client.py                 # MemoryClient class (<500 lines)
├── normalization.py          # _stable_coord, _parse_coord_string
├── filtering.py              # _filter_payloads_by_keyword, _extract_memory_coord
└── types.py                  # RecallHit dataclass
```

### 3. metrics_original.py Decomposition

```
somabrain/metrics/
├── __init__.py               # Re-exports all metrics (backward compat)
├── interface.py              # Already exists - Protocol definitions
├── core.py                   # Base metric factories (_counter, _gauge, etc.)
├── learning.py               # Learning/adaptation metrics
├── memory.py                 # Memory operation metrics
├── outbox.py                 # Outbox/circuit breaker metrics
├── health.py                 # Health/diagnostic metrics
└── middleware.py             # timing_middleware, metrics_endpoint
```

### 4. Secondary Files Decomposition

#### api/memory_api.py → api/memory/
```
somabrain/api/memory/
├── __init__.py               # Router export
├── router.py                 # Main router, <300 lines
├── models.py                 # Pydantic models (MemoryWriteRequest, etc.)
├── handlers.py               # Endpoint handlers
└── helpers.py                # _compose_memory_payload, _serialize_coord
```

#### learning/adaptation.py → learning/
```
somabrain/learning/
├── __init__.py
├── adaptation.py             # AdaptationEngine class (<500 lines)
├── config.py                 # AdaptationConfig, gain/bound dataclasses
├── overrides.py              # TenantOverridesCache (already extracted to DI)
└── feedback.py               # Feedback processing logic
```

#### schemas.py → schemas/
```
somabrain/schemas/
├── __init__.py               # Re-exports all schemas
├── core.py                   # Base schemas, common types
├── memory.py                 # Memory-related schemas
├── cognitive.py              # Cognitive/planning schemas
├── health.py                 # Health/diagnostic schemas
└── admin.py                  # Admin/outbox schemas
```

## Data Models

No new data models are introduced. Existing models are reorganized into domain-specific modules while maintaining their structure.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Import Backward Compatibility
*For any* existing import statement in the codebase, after decomposition the import SHALL resolve to the same object as before decomposition.
**Validates: Requirements 1.4, 2.3, 3.4**

### Property 2: API Route Preservation
*For any* HTTP endpoint defined before decomposition, the same route, method, and response format SHALL be available after decomposition.
**Validates: Requirements 1.2, 6.1**

### Property 3: Test Suite Stability
*For any* test that passed before decomposition, the same test SHALL pass after decomposition without modification.
**Validates: Requirements 5.1, 5.2**

### Property 4: No Circular Imports
*For any* module in the decomposed structure, importing that module SHALL complete without triggering lazy import fallbacks or import errors.
**Validates: Requirements 4.1, 5.4**

### Property 5: Line Count Compliance
*For any* file in the decomposed structure, the line count SHALL be less than 500 lines (with documented exceptions for app.py at <800).
**Validates: Requirements 1.1, 2.1, 3.1, 6.1-6.4**

## Error Handling

- All extracted modules SHALL use structured logging via `logging.getLogger(__name__)`
- Import errors SHALL be caught and logged at DEBUG level with fallback behavior
- Configuration errors SHALL raise `ValueError` with descriptive messages
- Runtime errors SHALL propagate to callers without silent swallowing

## Testing Strategy

### Unit Testing
- Each extracted module SHALL have corresponding unit tests
- Tests SHALL verify the module's public API matches the original
- Tests SHALL verify error handling behavior

### Property-Based Testing
- Property tests SHALL verify import backward compatibility
- Property tests SHALL verify API route preservation
- Property tests SHALL verify line count compliance

### Integration Testing
- Full application startup SHALL be tested after each extraction phase
- All existing integration tests SHALL pass without modification
