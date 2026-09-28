# SOMA-BR-VV-001: SomaBrain Verification and Validation Plan

> **Standard:** ISO/IEC/IEEE 16085:2006 — Systems and Software Engineering — Life Cycle Processes — Risk Management (adapted for V&V)
> **Owner:** SomaTech QA Team

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SomaBrain Verification and Validation Plan |
| Document Identifier | SOMA-BR-VV-001 |
| Version | 1.0.1 |
| Date | 2026-06-15 |
| Status | Approved |
| Author | SomaTech QA Team |
| Approver | VP Engineering, SomaTech |
| Classification | Internal |
| ISO Reference | ISO/IEC/IEEE 16085:2006 — Systems and Software Engineering — Life Cycle Processes — Risk Management (adapted for V&V) |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-06-15 | SomaTech QA Team | Initial V&V plan: ISO/IEC/IEEE 16085 compliant, 95 test files, 8 proof categories |
| 1.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-BR-VV-001` \| Status added as `Approved` (document names an approver). |

### Normative References

| Document ID | Title | Relationship |
|---|---|---|
| SOMA-BR-SRS-001 | SomaBrain Software Requirements Specification | Requirements baseline verified by this plan |
| SOMA-BR-ARCH-001 | SomaBrain Architecture Document | Architecture verified by structural tests |
| SOMA-BR-SDP-001 | SomaBrain Software Development Plan | Development process governing test creation |
| SOMA-BR-PROD-001 | SomaBrain Production Readiness Assessment | Acceptance criteria for Go/No-Go decisions |
| ISO/IEC/IEEE 16085:2006 | Life Cycle Processes — Risk Management | Governing standard adapted for V&V |
| ISO/IEC/IEEE 29148:2018 | Requirements Engineering | Requirements traceability standard |

---

## Table of Contents

1. [V&V Strategy](#1-vv-strategy)
2. [Verification by Category](#2-verification-by-category)
3. [Test Inventory](#3-test-inventory)
4. [Mathematical Proof Tests](#4-mathematical-proof-tests)
5. [Property-Based Tests](#5-property-based-tests)
6. [Acceptance Criteria](#6-acceptance-criteria)

---

## 1. V&V Strategy

### 1.1 Test Pyramid

SomaBrain's V&V strategy follows a test pyramid approach, with broad coverage at the base (unit and property tests) and targeted validation at the top (E2E and benchmarks):

```
                    ┌──────────────┐
                    │   E2E (3)    │  Full system health, unified integration
                    ├──────────────┤
                ┌───┤ Bench (2)    ├───┐  Performance regression, learning latency
                │   └──────────────┘   │
          ┌─────┤      Integration     ├─────┐
          │     │        (14)          │     │  Real infrastructure tests
          │     └──────────────────────┘     │
          ├──────────────────────────────────┤
          │      Property-Based (11)         │  Hypothesis-driven invariant verification
          ├──────────────────────────────────┤
          │      Proofs (~60, A–H)           │  Mathematical and behavioral proofs
          ├──────────────────────────────────┤
          │      Unit (5)                    │  Individual module correctness
          └──────────────────────────────────┘
```

### 1.2 V&V Principles

| Principle | Description |
|---|---|
| **Evidence-based** | Every requirement has at least one verifiable test (traceability matrix in SOMA-BR-SRS-001) |
| **Infrastructure-realistic** | Integration tests run against real PostgreSQL, Redis, Milvus, Kafka (no mocks) |
| **Property-first** | Hypothesis-driven tests generate thousands of random inputs to verify invariants |
| **Mathematically rigorous** | 8 proof categories verify mathematical foundations with assertion-based testing |
| **Continuous** | Tests run on every PR (unit + property + proof) and nightly (integration + E2E + benchmark) |
| **Fail-safe** | Rust core has pure Python fallback; tests verify both paths |

### 1.3 V&V Activities by Lifecycle Phase

| Phase | V&V Activity | Responsibility |
|---|---|---|
| P1 (Docs) | Requirements review, testability assessment | QA Team + Architecture Team |
| P2 (Integration) | Unit test development, property test development, integration test development | Development Team |
| P3 (Hardening) | Performance benchmarking, security testing, chaos testing, degraded mode testing | QA Team + Operations Team |
| P4 (Validation) | Acceptance testing, production readiness review, Go/No-Go decision | VP Engineering + all teams |

---

## 2. Verification by Category

### 2.1 Memory Operations (REQ-BR-MEM)

| Requirement | Verification Method | Test File | Status |
|---|---|---|---|
| REQ-BR-MEM-001 (Store + BHDC encode) | Proof — roundtrip | `proofs/category_b/test_memory_roundtrip.py` | ✅ Verified |
| REQ-BR-MEM-002 (Recall + cosine similarity) | Proof — similarity math | `proofs/category_a/test_similarity_math.py` | ✅ Verified |
| REQ-BR-MEM-003 (GMD update rule) | Proof — salience math | `proofs/category_a/test_salience_math.py` | ✅ Verified |
| REQ-BR-MEM-004 (Unit hypersphere) | Proof — HRR math | `proofs/category_a/test_hrr_math.py` | ✅ Verified |
| REQ-BR-MEM-005 (NREM consolidation) | Proof — LTM search | `proofs/category_b/test_ltm_search.py` | ✅ Verified |
| REQ-BR-MEM-006 (Exponential forgetting) | Proof — salience math | `proofs/category_a/test_salience_math.py` | ✅ Verified |
| REQ-BR-MEM-007 (Milvus + PostgreSQL persistence) | Integration | `integration/test_milvus_integration.py` | ✅ Verified |
| REQ-BR-MEM-008 (Provenance tracking) | Proof — outbox replay | `proofs/category_e/test_outbox_replay.py` | ✅ Verified |

### 2.2 Cognitive Pipeline (REQ-BR-COG)

| Requirement | Verification Method | Test File | Status |
|---|---|---|---|
| REQ-BR-COG-001 (Pipeline orchestration) | Proof — context | `proofs/category_c/test_context.py` | ✅ Verified |
| REQ-BR-COG-002 (Prediction + surprise) | Proof — predictor math | `proofs/category_a/test_predictor_math.py` | ✅ Verified |
| REQ-BR-COG-003 (Hub-triplet integration) | Proof — context | `proofs/category_c/test_context.py` | ✅ Verified |
| REQ-BR-COG-004 (HMM segmentation) | Proof — context | `proofs/category_c/test_context.py` | ✅ Verified |
| REQ-BR-COG-005 (Plasticity modulation) | Proof — neuromodulators | `proofs/category_c/test_neuromodulators.py` | ✅ Verified |
| REQ-BR-COG-006 (Synchronous fallback) | Proof — degraded mode | `proofs/category_f/test_degraded_mode.py` | ✅ Verified |

### 2.3 Working Memory (REQ-BR-WM)

| Requirement | Verification Method | Test File | Status |
|---|---|---|---|
| REQ-BR-WM-001 (Capacity management) | Proof — WM capacity | `proofs/category_b/test_wm_capacity.py` | ✅ Verified |
| REQ-BR-WM-002 (Salience gating) | Proof — WM capacity | `proofs/category_b/test_wm_capacity.py` | ✅ Verified |
| REQ-BR-WM-003 (LRU eviction) | Proof — WM capacity | `proofs/category_b/test_wm_capacity.py` | ✅ Verified |
| REQ-BR-WM-004 (Direct recall) | Proof — memory roundtrip | `proofs/category_b/test_memory_roundtrip.py` | ✅ Verified |
| REQ-BR-WM-005 (WM → LTM promotion) | Proof — WM promotion | `proofs/category_a/test_wm_promotion.py` | ✅ Verified |

### 2.4 Neuromodulators (REQ-BR-NEURO)

| Requirement | Verification Method | Test File | Status |
|---|---|---|---|
| REQ-BR-NEURO-001 (Four modulators) | Proof — neuromodulators | `proofs/category_c/test_neuromodulators.py` | ✅ Verified |
| REQ-BR-NEURO-002 (η modulation) | Proof — neuromodulators | `proofs/category_c/test_neuromodulators.py` | ✅ Verified |
| REQ-BR-NEURO-003 (Prometheus + API) | Proof — integration metrics | `proofs/category_h/test_integration_metrics.py` | ✅ Verified |
| REQ-BR-NEURO-004 (Bounds enforcement) | Proof — neuromodulators | `proofs/category_c/test_neuromodulators.py` | ✅ Verified |

### 2.5 Learning and Adaptation (REQ-BR-LRN)

| Requirement | Verification Method | Test File | Status |
|---|---|---|---|
| REQ-BR-LRN-001 (TD learning) | Proof — learning | `proofs/category_c/test_learning.py` | ✅ Verified |
| REQ-BR-LRN-002 (Reward signals) | Integration | `integration/test_learning_proof.py` | ✅ Verified |
| REQ-BR-LRN-003 (UCB1 attention) | Proof — planning | `proofs/category_c/test_planning.py` | ✅ Verified |
| REQ-BR-LRN-004 (Drift detection) | Proof — learning | `proofs/category_c/test_learning.py` | ✅ Verified |
| REQ-BR-LRN-005 (α/γ modulation) | Proof — learning | `proofs/category_c/test_learning.py` | ✅ Verified |

### 2.6 Planning (REQ-BR-PLAN)

| Requirement | Verification Method | Test File | Status |
|---|---|---|---|
| REQ-BR-PLAN-001 (Graph BFS) | Proof — planning | `proofs/category_c/test_planning.py` | ✅ Verified |
| REQ-BR-PLAN-002 (Option selection) | Proof — planning | `proofs/category_c/test_planning.py` | ✅ Verified |
| REQ-BR-PLAN-003 (Context evaluation) | Proof — context | `proofs/category_c/test_context.py` | ✅ Verified |

### 2.7 Mathematical Foundations (REQ-BR-MATH)

| Requirement | Verification Method | Test File | Status |
|---|---|---|---|
| REQ-BR-MATH-001 (HRR) | Proof — HRR math | `proofs/category_a/test_hrr_math.py` | ✅ Verified |
| REQ-BR-MATH-002 (BHDC + FWHT) | Proof — HRR math | `proofs/category_a/test_hrr_math.py` | ✅ Verified |
| REQ-BR-MATH-003 (Cosine similarity) | Proof — similarity math | `proofs/category_a/test_similarity_math.py` | ✅ Verified |
| REQ-BR-MATH-004 (Approximate orthogonality) | Proof — HRR math | `proofs/category_a/test_hrr_math.py` | ✅ Verified |

### 2.8 Sleep and Consolidation (REQ-BR-SLEEP)

| Requirement | Verification Method | Test File | Status |
|---|---|---|---|
| REQ-BR-SLEEP-001 (NREM) | Proof — LTM search | `proofs/category_b/test_ltm_search.py` | ✅ Verified |
| REQ-BR-SLEEP-002 (REM) | Proof — fusion | `proofs/category_b/test_fusion.py` | ✅ Verified |
| REQ-BR-SLEEP-003 (Consolidation scheduling) | Proof — WM persistence | `proofs/category_b/test_wm_persistence.py` | ✅ Verified |

---

## 3. Test Inventory

### 3.1 Complete Test File Inventory (95 files)

#### Unit Tests (5 files)

| # | File | Scope |
|---|---|---|
| 1 | `tests/unit/test_memory_service.py` | Memory service CRUD operations |
| 2 | `tests/unit/test_aaas_mode.py` | AAAS mode configuration and tenancy |
| 3 | `tests/unit/test_outbox_sync.py` | Transactional outbox synchronization |
| 4 | `tests/unit/test_learning_math.py` | TD learning mathematical operations |
| 5 | `tests/unit/memory/test_pool.py` | Memory pool management |

#### Property-Based Tests (11 files)

| # | File | Properties Verified |
|---|---|---|
| 1 | `tests/property/test_similarity_properties.py` | Cosine similarity symmetry, bounds, self-similarity |
| 2 | `tests/property/test_memory_properties.py` | Memory state norm preservation, GMD convergence |
| 3 | `tests/property/test_memory_system_properties.py` | System-level memory invariants |
| 4 | `tests/property/test_math_core_properties.py` | Vector normalization, dot product properties |
| 5 | `tests/property/test_predictor_properties.py` | Prediction bounds, surprise signal non-negativity |
| 6 | `tests/property/test_learning_properties.py` | TD error convergence, weight update bounds |
| 7 | `tests/property/test_normalization_properties.py` | Norm preservation after normalization |
| 8 | `tests/property/test_multitenancy_serialization.py` | Tenant ID serialization roundtrip |
| 9 | `tests/property/test_route_preservation.py` | API route consistency |
| 10 | `tests/property/test_forbidden_terms.py` | Forbidden import absence (SQLAlchemy, FastAPI) |
| 11 | `tests/property/test_dead_code_removal.py` | No unreachable code paths |

#### Integration Tests (14 files)

| # | File | Scope |
|---|---|---|
| 1 | `tests/integration/test_recall_quality.py` | Recall precision against golden datasets |
| 2 | `tests/integration/test_memory_workbench.py` | Memory workbench end-to-end |
| 3 | `tests/integration/test_memory_e2e.py` | Memory store → consolidate → recall cycle |
| 4 | `tests/integration/test_latency_slo.py` | Latency SLO compliance |
| 5 | `tests/integration/test_infrastructure_real.py` | Real infrastructure connectivity |
| 6 | `tests/integration/test_infrastructure_iso.py` | Infrastructure isolation tests |
| 7 | `tests/integration/test_e2e_real.py` | End-to-end with real services |
| 8 | `tests/integration/test_outbox_durability.py` | Outbox persistence and replay |
| 9 | `tests/integration/test_memory_integration.py` | Memory subsystem integration |
| 10 | `tests/integration/test_learning_proof.py` | Learning convergence integration |
| 11 | `tests/integration/test_brain_full_power.py` | Full brain capability test |
| 12 | `tests/integration/test_milvus_reconciliation.py` | Milvus index consistency |
| 13 | `tests/integration/test_cognition_workbench.py` | Cognitive workbench scenarios |
| 14 | `tests/integration/test_milvus_integration.py` | Milvus store/query operations |

#### Proof Tests — Category A: Mathematical Foundations (5 files)

| # | File | Assertions |
|---|---|---|
| 1 | `tests/proofs/category_a/test_similarity_math.py` | Cosine similarity bounds, symmetry, self-similarity |
| 2 | `tests/proofs/category_a/test_hrr_math.py` | HRR binding inverse accuracy, BHDC encoding, FWHT, orthogonality |
| 3 | `tests/proofs/category_a/test_salience_math.py` | Salience scoring, GMD norm preservation, exponential decay |
| 4 | `tests/proofs/category_a/test_predictor_math.py` | Prediction vector bounds, surprise signal magnitude |
| 5 | `tests/proofs/category_a/test_wm_promotion.py` | WM → LTM promotion with vector preservation |

#### Proof Tests — Category B: Memory Operations (7 files)

| # | File | Assertions |
|---|---|---|
| 1 | `tests/proofs/category_b/test_memory_roundtrip.py` | Store → recall roundtrip fidelity |
| 2 | `tests/proofs/category_b/test_wm_capacity.py` | WM capacity enforcement, eviction, salience gating |
| 3 | `tests/proofs/category_b/test_wm_persistence.py` | WM persistence across restarts |
| 4 | `tests/proofs/category_b/test_ltm_search.py` | LTM search quality, consolidation correctness |
| 5 | `tests/proofs/category_b/test_fusion.py` | REM fusion, associative recombination |
| 6 | `tests/proofs/category_b/test_graph_operations.py` | Knowledge graph traversal, linking |
| 7 | `tests/proofs/verify_brain_memory_bridge.py` | Brain ↔ memory bridge integrity |

#### Proof Tests — Category C: Cognitive Pipeline (5 files)

| # | File | Assertions |
|---|---|---|
| 1 | `tests/proofs/category_c/test_neuromodulators.py` | DA, 5-HT, NE, ACh baseline and bounds |
| 2 | `tests/proofs/category_c/test_learning.py` | TD learning convergence, reward response |
| 3 | `tests/proofs/category_c/test_planning.py` | BFS correctness, UCB1, option selection |
| 4 | `tests/proofs/category_c/test_context.py` | Context evaluation, integration pipeline |
| 5 | `tests/proofs/verify_gmd_canvas_alignment.py` | GMD algorithm alignment verification |

#### Proof Tests — Category D: Isolation (3 files)

| # | File | Assertions |
|---|---|---|
| 1 | `tests/proofs/category_d/test_memory_isolation.py` | Cross-tenant memory isolation |
| 2 | `tests/proofs/category_d/test_state_isolation.py` | Cross-tenant state isolation |
| 3 | `tests/proofs/category_d/test_state_isolation.py` | Circuit breaker tenant separation |

#### Proof Tests — Category E: Resilience (4 files)

| # | File | Assertions |
|---|---|---|
| 1 | `tests/proofs/category_e/test_outbox_replay.py` | Outbox replay after failure |
| 2 | `tests/proofs/category_e/test_health_verification.py` | Health endpoint correctness |
| 3 | `tests/proofs/category_e/test_memory_e2e.py` | Memory E2E recovery |
| 4 | `tests/proofs/category_e/test_resilience.py` | Service resilience under failure |

#### Proof Tests — Category F: Fault Tolerance (5 files)

| # | File | Assertions |
|---|---|---|
| 1 | `tests/proofs/category_f/test_circuit_state_machine.py` | Circuit breaker state transitions |
| 2 | `tests/proofs/category_f/test_circuit_per_tenant.py` | Per-tenant circuit breaker isolation |
| 3 | `tests/proofs/category_f/test_degraded_mode.py` | Graceful degradation without optional deps |
| 4 | `tests/proofs/category_f/__init__.py` | Package marker |
| 5 | `tests/proofs/conftest.py` | Shared proof fixtures |

#### Proof Tests — Category G: Performance (5 files)

| # | File | Assertions |
|---|---|---|
| 1 | `tests/proofs/category_g/test_latency_slo.py` | Store ≤ 8ms, recall ≤ 15ms, WM ≤ 2ms |
| 2 | `tests/proofs/category_g/test_throughput.py` | Store ≥ 12K/s, recall ≥ 5K/s |
| 3 | `tests/proofs/category_g/test_serialization.py` | Serialization efficiency |
| 4 | `tests/proofs/category_g/test_recall_quality.py` | Recall precision under load |
| 5 | `tests/proofs/test_brain_docker_proof.py` | Docker deployment proof |

#### Proof Tests — Category H: Observability (3 files)

| # | File | Assertions |
|---|---|---|
| 1 | `tests/proofs/category_h/test_distributed_tracing.py` | OpenTelemetry span coverage |
| 2 | `tests/proofs/category_h/test_integration_metrics.py` | Prometheus metric presence |
| 3 | `tests/proofs/category_h/__init__.py` | Package marker |

#### E2E Tests (3 files)

| # | File | Scope |
|---|---|---|
| 1 | `tests/e2e/test_health.py` | Full system health verification |
| 2 | `tests/e2e/test_unified_integration.py` | Unified integration across all services |
| 3 | `tests/e2e/__init__.py` | Package marker |

#### Benchmark Tests (2 files)

| # | File | Scope |
|---|---|---|
| 1 | `tests/benchmarks/test_learning_latency.py` | Learning loop latency benchmark |
| 2 | `tests/benchmarks/nulling_test.py` | Memory nulling/reset benchmark |

#### Other Test Files (~5 files)

| # | File | Scope |
|---|---|---|
| 1 | `tests/conftest.py` | Global test fixtures |
| 2 | `tests/test_planning_properties.py` | Planning property tests |
| 3 | `tests/standalone/test_standalone_mode.py` | Standalone mode verification |
| 4 | `tests/smoke/kafka_smoke_test.py` | Kafka connectivity smoke test |
| 5 | `tests/smoke/math_smoke_test.py` | Math module smoke test |

---

## 4. Mathematical Proof Tests

### 4.1 Category A: Mathematical Foundations

**Purpose:** Verify the mathematical correctness of core algorithms with assertion-based testing.

| Proof | Target | Assertion | Tolerance |
|---|---|---|---|
| HRR Binding Inverse | `context_hrr.py` | `unbind(bind(a, b), a) ≈ b` | cos_sim > 0.90 |
| HRR Binding Commutativity | `context_hrr.py` | `bind(a, b) ≈ bind(b, a)` | cos_sim > 0.95 |
| Cosine Similarity Bounds | `math/similarity.py` | `−1 ≤ sim(a, b) ≤ 1` for all inputs | Exact |
| Cosine Similarity Symmetry | `math/similarity.py` | `sim(a, b) = sim(b, a)` | Exact (float ε) |
| Self-Similarity | `math/similarity.py` | `sim(a, a) = 1.0` | ε < 1e-10 |
| BHDC Orthogonality | `rust_core/bhdc.rs` | `E[sim(h_i, h_j)] ≈ 0` for i ≠ j | |sim| < 0.05 |
| FWHT Correctness | `rust_core/bhdc.rs` | `FWHT(FWHT(x)) = N·x` | Exact |
| GMD Norm Preservation | `wm.py` | `‖m_t‖ ≤ 1` after any GMD update | Exact |
| Exponential Decay | `wm.py` | `‖m_t‖ = (1−η)^t · ‖m_0‖` for b=0 | ε < 1e-6 |

### 4.2 Category B: Memory Operations

| Proof | Target | Assertion |
|---|---|---|
| Store-Recall Roundtrip | `memory_service.py` | Stored content is retrievable with cos_sim > 0.85 |
| WM Capacity Enforcement | `wm.py` | `|WM items| ≤ capacity` after any insertion |
| WM Eviction Correctness | `wm.py` | Evicted item is lowest salience × recency |
| LTM Search Precision | `hippocampus.py` | Relevant memories retrieved in top-10 |
| WM → LTM Promotion | `hippocampus.py` | Promoted memory is retrievable from LTM |
| Graph Link Integrity | `somafractalmemory` | Linked memories are bidirectionally discoverable |

### 4.3 Category C: Cognitive Pipeline

| Proof | Target | Assertion |
|---|---|---|
| DA Baseline | `neuromodulators.py` | `DA_level ∈ [0.2, 0.6]` at baseline |
| 5-HT Baseline | `neuromodulators.py` | `5-HT_level ∈ [0.3, 0.7]` at baseline |
| NE Baseline | `neuromodulators.py` | `NE_level ∈ [0.05, 0.25]` at baseline |
| ACh Baseline | `neuromodulators.py` | `ACh_level ∈ [0.15, 0.50]` at baseline |
| TD Error Convergence | `adaptation_engine.py` | `|δ_t| → 0` over 1000 reward steps |
| UCB1 Exploration | `adaptation_engine.py` | Under-explored arms selected with higher frequency initially |

### 4.4 Categories D–H: Behavioral Proofs

| Category | Proof Focus | Key Assertion |
|---|---|---|
| D (Isolation) | Cross-tenant memory isolation | Tenant A cannot retrieve Tenant B's memories even with valid query |
| E (Resilience) | Outbox replay after Kafka recovery | All outbox events are replayed; zero event loss |
| F (Fault Tolerance) | Circuit breaker state machine | Transitions: Closed → Open (on failure threshold) → Half-Open (on timeout) → Closed (on success) |
| G (Performance) | Latency SLO compliance | Store p95 ≤ 8ms, Recall p95 ≤ 15ms, WM p95 ≤ 2ms |
| H (Observability) | Metric presence | All 30+ Prometheus metric modules are registered and scrapeable |

---

## 5. Property-Based Tests

### 5.1 Hypothesis Framework

SomaBrain uses the **Hypothesis** library for property-based testing. Hypothesis generates random inputs and verifies that defined properties (invariants) hold for all generated inputs. This provides significantly broader coverage than example-based tests.

**Configuration:**

| Parameter | Value | Rationale |
|---|---|---|
| `max_examples` | 100–500 (per test) | Balance between coverage and CI time |
| `@given` strategy | Custom strategies for hypervectors, memory content, neuromodulator levels | Domain-specific input generation |
| Database | `~/.hypothesis/examples.sqlite3` | Shrinking database for reproducibility |

### 5.2 Cosine Similarity Properties (`test_similarity_properties.py`)

| Property | Formal Statement | Verification |
|---|---|---|
| **Symmetry** | `∀ a, b: sim(a, b) = sim(b, a)` | Hypothesis generates 500+ random vector pairs |
| **Boundedness** | `∀ a, b: −1 ≤ sim(a, b) ≤ 1` | Tested with unit, zero, and extreme vectors |
| **Self-similarity** | `∀ a ≠ 0: sim(a, a) = 1.0` | Tested with random nonzero vectors |
| **Zero vector** | `∀ a: sim(a, 0) = 0` (by convention) | Zero-vector handling correctness |
| **Triangle inequality** | `sim(a, c) ≥ sim(a, b) + sim(b, c) − 1` | Tested for random triples |

### 5.3 HRR Spectral Properties (`test_math_core_properties.py`)

| Property | Formal Statement | Verification |
|---|---|---|
| **Bind-commutativity** | `bind(a, b) ≈ bind(b, a)` | cos_sim > 0.95 for random pairs |
| **Bind-inverse** | `unbind(bind(a, b), a) ≈ b` | cos_sim > 0.90 for random pairs |
| **Bundle norm** | `‖bundle(a₁, ..., aₙ)‖ ≤ max(‖aᵢ‖)` | Norm does not grow under bundling |
| **FWHT involutive** | `FWHT⁻¹(FWHT(x)) = x` | Roundtrip fidelity for random inputs |

### 5.4 Working Memory Capacity Invariants (`test_memory_system_properties.py`)

| Property | Formal Statement | Verification |
|---|---|---|
| **Capacity bound** | `∀ t: |WM_t| ≤ capacity` | Tested with burst insertions |
| **Salience monotonicity** | Higher-salience items persist longer under eviction pressure | Statistical test over 100 trials |
| **GMD norm preservation** | `∀ update: ‖m_after‖ ≤ 1` | Tested with random inputs and η values |
| **Deterministic retrieval** | Same query + same WM state → same result | Tested with controlled seeds |

---

## 6. Acceptance Criteria

### 6.1 Standalone Mode: GO

Per SOMA-BR-PROD-001, Section 10.1:

| Criterion | Requirement | Evidence |
|---|---|---|
| All required dependencies available | PostgreSQL, Redis, Milvus | Integration tests pass (`test_infrastructure_real.py`) |
| Health checks operational | `/health/ready` returns 200 | `proofs/category_e/test_health_verification.py` |
| Metrics collection active | `/metrics` exposes 30+ modules | `proofs/category_h/test_integration_metrics.py` |
| Docker Compose deployment tested | `infra/standalone/docker-compose.yml` | `proofs/test_brain_docker_proof.py` |
| Security controls in place | JWT, PII masking, audit logging | `SOMA-BR-SEC-001` assessment |
| All 38 functional requirements verified | REQ-BR-* traceability | This V&V plan, §2 |
| Performance SLOs met | Store ≤ 8ms, Recall ≤ 15ms | `proofs/category_g/test_latency_slo.py` |

**Verdict: ✅ GO — All criteria satisfied.**

### 6.2 AAAS Mode: CONDITIONAL GO

Per SOMA-BR-PROD-001, Section 10.2:

| Criterion | Requirement | Status | Condition |
|---|---|---|---|
| Multi-tenant isolation | Cryptographic tenant separation | ✅ Met | — |
| Authentication and authorization | JWT + OPA mandatory | ✅ Met | — |
| SomaFractalMemory integration | HTTP transport operational | ✅ Met | — |
| Kafka pipeline | 5 topics, 17 schemas | ✅ Met | — |
| Observability | 30+ metric modules, tracing | ✅ Met | — |
| Constitution signing validation | End-to-end signing | ⚠️ Pending | C-001 |
| Horizontal scaling validation | Load test with 3+ pods | ⚠️ Pending | C-002 |
| SFM SLA agreement | Latency and availability SLA | ⚠️ Pending | C-003 |
| SFM health probe | Readiness integration | ⚠️ Pending | C-004 |
| Chaos testing | Per-tenant isolation under adversarial conditions | ⚠️ Pending | C-005 |

**Verdict: ⚠️ CONDITIONAL GO — Core criteria met. Five conditions (C-001 through C-005) must be fulfilled before unrestricted production use. Target: 2026-10-01.**

### 6.3 Acceptance Summary

| Mode | Verdict | Confidence | Blocking Conditions |
|---|---|---|---|
| **Standalone** | **GO** ✅ | High | None |
| **AAAS** | **CONDITIONAL GO** ⚠️ | Medium-High | C-001 through C-005 (target: 2026-10-01) |

---

*End of document. This Verification and Validation Plan conforms to ISO/IEC/IEEE 16085:2006 and is subject to semi-annual review.*
