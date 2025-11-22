# Somabrain Sleep System - ROAMDP Implementation Plan

## Sprint Architecture Overview

### Sprint 1: Foundation (Week 1)
**Goal**: Core sleep state management
- Sleep mode enumeration and state machine
- Basic parameter scheduling mathematics
- Tenant isolation framework

### Sprint 2: Utility Sleep (Week 2)
**Goal**: Utility sleep API implementation
- `/api/util/sleep` endpoint
- OPA policy integration
- Prometheus metrics

### Sprint 3: Cognitive Sleep (Week 3)
**Goal**: Cognitive sleep mode with CB integration
- `/api/brain/sleep_mode` endpoint
- Circuit breaker state mapping
- TTL auto-wake implementation

### Sprint 4: Testing & Integration (Week 4)
**Goal**: Comprehensive testing and production readiness
- E2E testing suite
- Performance benchmarks
- Operational runbooks

## Parallel Sprint Structure

### Sprint 1A: Core State Management
- SleepState enum and state machine
- Parameter mathematics
- Configuration validation

### Sprint 1B: Tenant Framework
- Per-tenant sleep storage
- JWT tenant extraction
- OPA policy rules

### Sprint 2A: Utility API
- FastAPI endpoint implementation
- Async task management
- Graceful shutdown handling

### Sprint 2B: Metrics & Monitoring
- Prometheus metrics integration
- JSON logging framework
- Health check extensions

### Sprint 3A: Cognitive API
- Sleep mode transitions
- Circuit breaker integration
- TTL scheduling

### Sprint 3B: Policy Engine
- OPA policy rules
- Rate limiting
- Security validation

### Sprint 4A: Testing Suite
- Unit tests for mathematics
- Integration tests for endpoints
- Load testing

### Sprint 4B: Documentation
- API documentation
- Operational runbooks
- Migration guides

## Implementation Order

### Phase 1: Core (Parallel Development)
```
Sprint 1A: Core State Management
├── SleepState enum
├── Parameter schedules
└── State machine logic

Sprint 1B: Tenant Framework
├── Per-tenant storage
├── JWT validation
└── OPA policies
```

### Phase 2: APIs (Parallel Development)
```
Sprint 2A: Utility Sleep API
├── POST /api/util/sleep
├── Async/Sync modes
└── Cancellation support

Sprint 2B: Cognitive Sleep API
├── POST /api/brain/sleep_mode
├── Circuit breaker integration
└── Parameter scheduling
```

### Phase 3: Testing & Production
```
Sprint 3A: Integration Testing
├── E2E test suite
├── Load testing
└── Chaos engineering

Sprint 3B: Documentation
├── API docs
├── Runbooks
└── Migration guides
```

## Current Implementation Gap
- `/api/util/sleep` and `/api/brain/sleep_mode` exist in the codebase, but the `/api/brain/sleep_policy` endpoint described in the plan is not implemented anywhere yet, so the cognitive policy layer (with OPA/JWT/rate-limit enforcement) remains outstanding.

## Success Criteria

### Sprint 1: Core Foundation
- [ ] SleepState enum with all 4 modes
- [ ] Parameter mathematics implemented
- [ ] Tenant isolation working
- [ ] 95% unit test coverage

### Sprint 2: Utility Sleep
- [ ] /api/util/sleep endpoint working
- [ ] OPA policies enforced
- [ ] Prometheus metrics collected
- [ ] Async cancellation tested

### Sprint 3: Cognitive Sleep
- [ ] /api/brain/sleep_mode endpoint working
- [ ] Circuit breaker integration tested
- [ ] TTL auto-wake implemented
- [ ] Security validation complete

### Sprint 4: Production Ready
- [ ] All tests passing
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] Migration guide ready

## ROAMDP Compliance

### Per-Tenant Circuit Breakers
- Each tenant has independent sleep state
- Circuit breaker events trigger per-tenant sleep modes
- Isolated resource consumption

### HTTP-First Architecture
- All sleep APIs use HTTP endpoints
- No local file storage for state
- Database-backed state persistence

### Parameter Scheduling
- Mathematical correctness guaranteed
- Monotonic and bounded parameters
- Reversible state transitions

### Zero Legacy Code
- Clean implementation following ROAMDP principles
- No fallback mechanisms
- Deterministic behavior
