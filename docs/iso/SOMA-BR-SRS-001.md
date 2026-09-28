# SOMA-BR-SRS-001: SomaBrain Software Requirements Specification

> **Standard:** ISO/IEC/IEEE 29148:2018 — Systems and Software Engineering — Life Cycle Processes — Requirements Engineering
> **Owner:** SomaTech Engineering

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SomaBrain Software Requirements Specification |
| Document Identifier | SOMA-BR-SRS-001 |
| Version | 1.0.1 |
| Date | 2026-06-15 |
| Status | Approved |
| Author | SomaTech Engineering |
| Approver | VP Engineering, SomaTech |
| Classification | Internal |
| ISO Reference | ISO/IEC/IEEE 29148:2018 — Systems and Software Engineering — Life Cycle Processes — Requirements Engineering |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-06-15 | SomaTech Engineering | Initial SRS: ISO/IEC/IEEE 29148 compliant requirements baseline for SomaBrain |
| 1.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-BR-SRS-001` \| Status added as `Approved` (document names an approver). |

### Normative References

| Document ID | Title | Relationship |
|---|---|---|
| SOMA-BR-ARCH-001 | SomaBrain Architecture Document | Defines the architectural context for all requirements herein |
| SOMA-BR-SEC-001 | SomaBrain Security Assessment | Defines security requirements referenced by REQ-BR-* |
| SOMA-BR-PROD-001 | SomaBrain Production Readiness Assessment | Defines production readiness criteria for requirement acceptance |
| SRS-SOMABRAIN-MASTER-001 | SomaBrain Master Technical Specification (`docs/SRS_FULL.md`) | Detailed functional specification; this document formalizes its requirements with traceable IDs |
| ISO/IEC/IEEE 29148:2018 | Requirements Engineering | Governing standard for this document |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Functional Requirements](#2-functional-requirements)
3. [Non-Functional Requirements](#3-non-functional-requirements)
4. [Interface Requirements](#4-interface-requirements)
5. [Constraints](#5-constraints)
6. [Requirements Traceability Matrix](#6-requirements-traceability-matrix)
7. [Cross-Reference to SRS_FULL.md](#7-cross-reference-to-srs_fullmd)

---

## 1. Introduction

### 1.1 Purpose

This document specifies the software requirements for **SomaBrain**, a Hyperdimensional Cognitive Memory System. SomaBrain provides persistent, biologically-inspired memory capabilities for autonomous AI agents, implementing a Governed Trace memory model grounded in hyperdimensional computing (HDC) theory.

This SRS conforms to ISO/IEC/IEEE 29148:2018 and serves as the authoritative requirements baseline for development, testing, and acceptance activities.

### 1.2 Scope

SomaBrain is a full-stack cognitive memory engine comprising:

- **116,735 lines** of Python code (Django 5.1 + Django Ninja 1.3)
- **1,782 lines** of Rust code (via PyO3/maturin for performance-critical paths)
- **95 test files** across 8 proof categories
- **Dual deployment modes:** Standalone (port 9696) and AAAS (port 63996)

This SRS covers all functional and non-functional requirements for the SomaBrain component within the SomaStack ecosystem (SomaAgent01, SomaFractalMemory).

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|---|---|
| **GMD** | Governed Trace — the core memory update algorithm: **m**_t = (1−η)**m**_{t−1} + η**b**_t |
| **HDC** | Hyperdimensional Computing — computing paradigm using high-dimensional vectors |
| **HRR** | Holographic Reduced Representations — compositional structure encoding method |
| **BHDC** | Binary Hyperdimensional Computing — binary variant of HDC with FWHT acceleration |
| **FWHT** | Fast Walsh-Hadamard Transform — O(N log N) binding operation |
| **WM** | Working Memory — short-term, salience-gated memory buffer |
| **LTM** | Long-Term Memory — persistent memory store in PostgreSQL + Milvus |
| **AAAS** | As-a-Service — multi-tenant deployment mode within SomaStack |
| **SFM** | SomaFractalMemory — distributed long-term memory component |
| **TD Learning** | Temporal-Difference Learning — reinforcement learning for cognitive parameter adjustment |
| **NREM** | Non-Rapid Eye Movement — sleep phase for batch consolidation |
| **REM** | Rapid Eye Movement — sleep phase for associative recombination |
| **HNSW** | Hierarchical Navigable Small World — approximate nearest-neighbor index in Milvus |
| **OPA** | Open Policy Agent — policy-as-code authorization engine |
| **UCB1** | Upper Confidence Bound — exploration/exploitation algorithm for memory slot selection |

### 1.4 System Context

SomaBrain operates as the cognitive memory engine within the SomaStack:

| Component | Role | Port (Standalone) | Port (AAAS) |
|---|---|---|---|
| SomaBrain | Cognitive memory engine | 9696 | 63996 |
| SomaAgent01 | Agent orchestration gateway | 20020 | 63900 |
| SomaFractalMemory | Distributed long-term storage | 10101 | 63901 |

---

## 2. Functional Requirements

### 2.1 REQ-BR-MEM: Memory Operations

Requirements for the core memory subsystem (store, recall, consolidate, forget).

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| REQ-BR-MEM-001 | The system SHALL accept memory content via `POST /api/v1/memory/store` and encode it into an 8,192-dimensional hypervector using BHDC encoding. | Critical | `tests/proofs/category_b/test_memory_roundtrip.py` |
| REQ-BR-MEM-002 | The system SHALL retrieve memories via `POST /api/v1/memory/recall` by computing cosine similarity between the query vector and stored superposition vectors, returning results ranked by similarity score. | Critical | `tests/proofs/category_a/test_similarity_math.py` |
| REQ-BR-MEM-003 | The system SHALL apply the GMD update rule **m**_t = (1−η)**m**_{t−1} + η**b**_t for all memory state updates, where η is the adaptive plasticity gain. | Critical | `tests/proofs/category_a/test_salience_math.py` |
| REQ-BR-MEM-004 | The system SHALL maintain the memory state vector within the unit hypersphere (‖**m**_t‖ ≤ 1) at all times. | Critical | `tests/proofs/category_a/test_hrr_math.py` |
| REQ-BR-MEM-005 | The system SHALL consolidate high-salience working memory items to long-term memory (PostgreSQL + Milvus) during NREM consolidation cycles. | High | `tests/proofs/category_b/test_ltm_search.py` |
| REQ-BR-MEM-006 | The system SHALL support memory forgetting via exponential decay in the absence of new input, with ‖**m**_t‖ = (1−η)^t · ‖**m**_0‖. | Medium | `tests/proofs/category_a/test_salience_math.py` |
| REQ-BR-MEM-007 | The system SHALL persist consolidated memories to Milvus with HNSW indexing and to PostgreSQL via Django ORM, providing both vector similarity and relational query capabilities. | Critical | `tests/integration/test_milvus_integration.py` |
| REQ-BR-MEM-008 | The system SHALL provide memory provenance tracking with operation hash, tenant ID, timestamp, parent hash, and constitution signature for every memory mutation. | High | `tests/proofs/category_e/test_outbox_replay.py` |

### 2.2 REQ-BR-COG: Cognitive Pipeline

Requirements for the cognitive processing pipeline (predict, integrate, segment, learn).

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| REQ-BR-COG-001 | The system SHALL execute a cognitive pipeline consisting of predict → integrate → segment → store, orchestrated via Kafka topics (`cog.perceive`, `cog.predict`, `cog.integrate`, `cog.segment`, `cog.store`). | Critical | `tests/proofs/category_c/test_context.py` |
| REQ-BR-COG-002 | The system SHALL generate prediction vectors using diffusion-backed predictors, producing a surprise signal when input deviates from prediction by more than a configurable threshold. | High | `tests/proofs/category_a/test_predictor_math.py` |
| REQ-BR-COG-003 | The system SHALL integrate signals from sensory input, predictor output, working memory state, and neuromodulator levels via the hub-triplet integrator (`somabrain/services/integrator_hub_triplet.py`). | High | `tests/proofs/category_c/test_context.py` |
| REQ-BR-COG-004 | The system SHALL segment continuous input streams into discrete episodes using HMM-based temporal segmentation with Viterbi decoding (`somabrain/services/segmentation_service.py`). | Medium | `tests/proofs/category_c/test_context.py` |
| REQ-BR-COG-005 | The system SHALL modulate the plasticity gain η based on neuromodulator levels (DA, 5-HT, NE, ACh), surprise signal, and cognitive preset (Stable, Plastic, Lateral). | High | `tests/proofs/category_c/test_neuromodulators.py` |
| REQ-BR-COG-006 | The system SHALL support synchronous fallback execution of the cognitive pipeline when Kafka is unavailable, with degraded but functional operation. | Medium | `tests/proofs/category_f/test_degraded_mode.py` |

### 2.3 REQ-BR-WM: Working Memory

Requirements for the working memory subsystem.

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| REQ-BR-WM-001 | The system SHALL maintain a working memory buffer with a configurable capacity (default: 64 slots) in `somabrain/wm.py`. | High | `tests/proofs/category_b/test_wm_capacity.py` |
| REQ-BR-WM-002 | The system SHALL enforce salience-based gating for working memory admission, rejecting items below a configurable salience threshold. | High | `tests/proofs/category_b/test_wm_capacity.py` |
| REQ-BR-WM-003 | The system SHALL implement LRU-eviction with salience boosting when working memory capacity is reached, evicting the least-recently-used, lowest-salience item. | High | `tests/proofs/category_b/test_wm_capacity.py` |
| REQ-BR-WM-004 | The system SHALL support direct working memory recall by slot index and by salience-ranked scan, both returning results in < 2ms (p95). | High | `tests/proofs/category_b/test_memory_roundtrip.py` |
| REQ-BR-WM-005 | The system SHALL promote high-salience working memory items to long-term memory during consolidation, preserving the GMD-encoded hypervector representation. | Critical | `tests/proofs/category_a/test_wm_promotion.py` |

### 2.4 REQ-BR-NEURO: Neuromodulators

Requirements for the neuromodulator simulation system.

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| REQ-BR-NEURO-001 | The system SHALL simulate four neuromodulators — Dopamine (DA, baseline 0.4), Serotonin (5-HT, baseline 0.52), Norepinephrine (NE, baseline 0.12), and Acetylcholine (ACh, baseline 0.31) — in `somabrain/neuromodulators.py`. | High | `tests/proofs/category_c/test_neuromodulators.py` |
| REQ-BR-NEURO-002 | The system SHALL modulate the plasticity gain η based on Dopamine level (increased DA → higher η) and stabilize it based on Serotonin level. | High | `tests/proofs/category_c/test_neuromodulators.py` |
| REQ-BR-NEURO-003 | The system SHALL expose neuromodulator levels via Prometheus metrics (`soma_neuro_dopamine_level`, etc.) and allow external adjustment via `PUT /v1/neuromodulators`. | Medium | `tests/proofs/category_c/test_neuromodulators.py` |
| REQ-BR-NEURO-004 | The system SHALL constrain neuromodulator levels within configurable bounds, preventing extreme drift through the calibration service (`somabrain/services/calibration_service.py`). | Medium | `tests/proofs/category_c/test_neuromodulators.py` |

### 2.5 REQ-BR-LRN: Learning and Adaptation

Requirements for the learning and adaptation subsystem.

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| REQ-BR-LRN-001 | The system SHALL implement temporal-difference (TD) learning with the update rule δ_t = r_t + γV(s_{t+1}) − V(s_t) and Δw = α · δ_t · ∇_w V(s_t). | High | `tests/proofs/category_c/test_learning.py` |
| REQ-BR-LRN-002 | The system SHALL accept external reward signals via `POST /v1/learning/reward` to drive TD learning updates. | High | `tests/integration/test_learning_proof.py` |
| REQ-BR-LRN-003 | The system SHALL apply UCB1 attention (Upper Confidence Bound) for memory slot selection, balancing exploitation of high-salience memories with exploration of under-retrieved ones. | Medium | `tests/proofs/category_c/test_planning.py` |
| REQ-BR-LRN-004 | The system SHALL detect input distribution drift and trigger recalibration via `somabrain/services/calibration_service.py`. | Medium | `tests/proofs/category_c/test_learning.py` |
| REQ-BR-LRN-005 | The system SHALL modulate learning rate α and discount factor γ based on neuromodulator levels, with higher Dopamine increasing α and higher Serotonin decreasing γ. | High | `tests/proofs/category_c/test_learning.py` |

### 2.6 REQ-BR-PLAN: Planning

Requirements for the executive planning subsystem.

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| REQ-BR-PLAN-001 | The system SHALL implement graph-informed breadth-first search (BFS) for memory retrieval, traversing the knowledge graph to discover associatively linked memories. | Medium | `tests/proofs/category_c/test_planning.py` |
| REQ-BR-PLAN-002 | The system SHALL implement option selection via the prefrontal cortex module (`somabrain/prefrontal.py`), supporting goal maintenance, cognitive switching, and inhibition. | Medium | `tests/proofs/category_c/test_planning.py` |
| REQ-BR-PLAN-003 | The system SHALL expose planning state via context evaluation at `POST /v1/context/evaluate`, returning the current cognitive state and recommended actions. | Medium | `tests/proofs/category_c/test_context.py` |

### 2.7 REQ-BR-MATH: Mathematical Foundations

Requirements for the mathematical computation layer.

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| REQ-BR-MATH-001 | The system SHALL implement Holographic Reduced Representations (HRR) with circular convolution binding (a ⊛ b), approximate inverse unbinding, and hypervector encode/decode operations in `somabrain/context_hrr.py`. | Critical | `tests/proofs/category_a/test_hrr_math.py` |
| REQ-BR-MATH-002 | The system SHALL implement Binary Hyperdimensional Computing (BHDC) encoding in `rust_core/src/bhdc.rs` using Fast Walsh-Hadamard Transform (FWHT) for O(N log N) binding operations, with configurable dimension (default 8,192) and density (default 2%). | Critical | `tests/proofs/category_a/test_hrr_math.py` |
| REQ-BR-MATH-003 | The system SHALL compute cosine similarity between hypervectors with results bounded in [−1, 1], optimized for high-dimensional sparse vectors in `somabrain/math/similarity.py` (Python) and `rust_core/src/mathcore.rs` (Rust). | Critical | `tests/proofs/category_a/test_similarity_math.py` |
| REQ-BR-MATH-004 | The system SHALL guarantee approximate orthogonality of random hypervectors in R^N with interference bounded by O(1/√N), enabling high-capacity associative memory. | High | `tests/proofs/category_a/test_hrr_math.py` |

### 2.8 REQ-BR-SLEEP: Sleep and Consolidation

Requirements for the sleep-inspired consolidation cycles.

| ID | Requirement | Priority | Verification |
|---|---|---|---|
| REQ-BR-SLEEP-001 | The system SHALL implement NREM consolidation cycles that batch-transfer high-salience working memory items to long-term memory, performing pattern extraction and deduplication. | High | `tests/proofs/category_b/test_ltm_search.py` |
| REQ-BR-SLEEP-002 | The system SHALL implement REM consolidation cycles that perform associative recombination, creative memory linking, and schema integration across long-term memory entries. | Medium | `tests/proofs/category_b/test_fusion.py` |
| REQ-BR-SLEEP-003 | The system SHALL execute consolidation cycles on configurable schedules, with NREM triggered by working memory pressure or timer, and REM triggered by accumulated NREM cycles. | Medium | `tests/proofs/category_b/test_wm_persistence.py` |

---

## 3. Non-Functional Requirements

### 3.1 Performance

| ID | Requirement | Target | Verification |
|---|---|---|---|
| NFR-PERF-001 | Memory store latency (p95) | ≤ 8ms | `tests/benchmarks/test_learning_latency.py` |
| NFR-PERF-002 | Vector recall latency (p95) | ≤ 15ms | `tests/proofs/category_g/test_latency_slo.py` |
| NFR-PERF-003 | Working memory update latency (p95) | ≤ 2ms | `tests/proofs/category_g/test_latency_slo.py` |
| NFR-PERF-004 | Memory store throughput | ≥ 12,000 ops/sec | `tests/proofs/category_g/test_throughput.py` |
| NFR-PERF-005 | Vector recall throughput | ≥ 5,000 ops/sec | `tests/proofs/category_g/test_throughput.py` |
| NFR-PERF-006 | Consolidation cycle throughput | ≥ 10,000 memories per cycle | `tests/proofs/category_b/test_ltm_search.py` |

### 3.2 Reliability

| ID | Requirement | Target | Verification |
|---|---|---|---|
| NFR-REL-001 | The system SHALL maintain memory state integrity across process restarts via PostgreSQL and Milvus persistence. | Zero data loss | `tests/proofs/category_b/test_wm_persistence.py` |
| NFR-REL-002 | The system SHALL implement per-tenant circuit breakers in AAAS mode, preventing cascading failures between tenants. | No cross-tenant impact | `tests/proofs/category_f/test_circuit_state_machine.py` |
| NFR-REL-003 | The system SHALL gracefully degrade when optional dependencies (Kafka, OPA, SomaFractalMemory) are unavailable. | Core functionality preserved | `tests/proofs/category_f/test_degraded_mode.py` |
| NFR-REL-004 | The system SHALL use the transactional outbox pattern for reliable event publishing, ensuring no dual-write inconsistency. | Zero event loss | `tests/proofs/category_e/test_outbox_replay.py` |
| NFR-REL-005 | The system SHALL support horizontal scaling in AAAS mode via stateless Django pods behind a load balancer. | Linear throughput scaling | `tests/proofs/category_g/test_throughput.py` |

### 3.3 Scalability

| ID | Requirement | Target | Verification |
|---|---|---|---|
| NFR-SCAL-001 | The system SHALL support ≥ 12 million stored memories per tenant with sub-15ms recall latency. | Per tenant | `tests/integration/test_recall_quality.py` |
| NFR-SCAL-002 | The system SHALL support ≥ 50 concurrent tenants in AAAS mode with independent memory isolation. | Multi-tenant | `tests/proofs/category_d/test_memory_isolation.py` |
| NFR-SCAL-003 | The system SHALL support Milvus clustered deployment for AAAS mode, with per-tenant collection isolation. | Production scale | `tests/integration/test_milvus_integration.py` |

---

## 4. Interface Requirements

### 4.1 SomaAgent01 Interface

| ID | Requirement | Details |
|---|---|---|
| INT-001 | SomaBrain SHALL accept requests from SomaAgent01 via HTTP/1.1 + Server-Sent Events on port 63996 (AAAS) or 9696 (standalone). | Auth: Bearer token (`SOMA_API_TOKEN`) |
| INT-002 | SomaBrain SHALL expose endpoints `POST /api/v1/memory/store`, `POST /api/v1/memory/recall`, `POST /v1/context/evaluate`, `PUT /v1/neuromodulators`, `POST /v1/learning/reward`. | Django Ninja API |
| INT-003 | SomaBrain SHALL respond to health checks at `GET /health` and `GET /health/ready`. | Readiness and liveness probes |

### 4.2 SomaFractalMemory Interface

| ID | Requirement | Details |
|---|---|---|
| INT-004 | SomaBrain SHALL write consolidated memories to SomaFractalMemory via HTTP REST API (`POST /memories`, `POST /memories/search`). | Auth: Bearer token (sbk_* prefix) |
| INT-005 | SomaBrain SHALL traverse the SomaFractalMemory knowledge graph via `POST /graph/link` and `GET /graph/neighbors`. | Graph-informed retrieval |
| INT-006 | SomaBrain SHALL operate in degraded mode when SomaFractalMemory is unavailable, queuing writes for later replay. | `SOMABRAIN_MEMORY_DEGRADE_QUEUE=1` |

### 4.3 Kafka Interface

| ID | Requirement | Details |
|---|---|---|
| INT-007 | SomaBrain SHALL produce and consume events on 5 Kafka topics (`cog.perceive`, `cog.predict`, `cog.integrate`, `cog.segment`, `cog.store`) using Avro serialization with schema registry. | 17 Avro schemas |
| INT-008 | SomaBrain SHALL use the transactional outbox pattern to ensure atomicity between PostgreSQL writes and Kafka event publishing. | Zero dual-write gap |

### 4.4 Milvus Interface

| ID | Requirement | Details |
|---|---|---|
| INT-009 | SomaBrain SHALL store and query hypervectors in Milvus using HNSW indices with cosine similarity distance metric. | Per-tenant collections in AAAS |
| INT-010 | SomaBrain SHALL support both Milvus local (standalone) and clustered (AAAS) deployment configurations. | Port 19530 |

### 4.5 PostgreSQL Interface

| ID | Requirement | Details |
|---|---|---|
| INT-011 | SomaBrain SHALL persist all relational data via Django ORM to PostgreSQL 15+. No SQLAlchemy imports are permitted. | Django-only ORM constraint |
| INT-012 | SomaBrain SHALL support PostgreSQL replication for read scaling in production deployments. | Primary + replicas |

### 4.6 Redis Interface

| ID | Requirement | Details |
|---|---|---|
| INT-013 | SomaBrain SHALL use Redis for caching, session storage, and per-tenant key-prefixed working memory state (`tenant:{id}:*`). | Redis 7+ |
| INT-014 | SomaBrain SHALL support Redis TLS for cluster mode deployments. | Production AAAS |

---

## 5. Constraints

### 5.1 Technology Constraints

| ID | Constraint | Rationale |
|---|---|---|
| CON-001 | SomaBrain SHALL use Django ORM exclusively for database access. SQLAlchemy is explicitly prohibited (0 imports enforced). | Architecture consistency; per SRS_FULL.md compliance status |
| CON-002 | SomaBrain SHALL use Django Ninja (not FastAPI) for the API layer. FastAPI is explicitly prohibited (0 imports enforced). | Framework alignment with Django ecosystem |
| CON-003 | SomaBrain SHALL target Python 3.12 as the primary runtime. | Pinned dependency per pyproject.toml |
| CON-004 | Performance-critical algorithms SHALL be implemented in Rust and exposed via PyO3/maturin bindings, with pure Python fallbacks. | 10-100× acceleration for hot paths |
| CON-005 | Production code SHALL contain zero TODO or FIXME markers. All work items must be tracked in the issue tracker. | VIBE coding discipline |

### 5.2 Process Constraints

| ID | Constraint | Rationale |
|---|---|---|
| CON-006 | All code changes SHALL pass pre-commit hooks (Black, Ruff, mypy) before commit. | Quality gate |
| CON-007 | All new requirements SHALL be assigned a unique REQ-BR-* identifier and added to the traceability matrix. | ISO/IEC/IEEE 29148 compliance |
| CON-008 | Configuration parameters SHALL use environment variables (not hardcoded values) and be documented in `.env.example`. | 12-factor app compliance |

---

## 6. Requirements Traceability Matrix

### 6.1 Summary

| Requirement Group | Count | Critical | High | Medium | Test Coverage |
|---|---|---|---|---|---|
| REQ-BR-MEM (Memory) | 8 | 4 | 3 | 1 | 100% |
| REQ-BR-COG (Cognitive) | 6 | 1 | 3 | 2 | 100% |
| REQ-BR-WM (Working Memory) | 5 | 1 | 4 | 0 | 100% |
| REQ-BR-NEURO (Neuromodulators) | 4 | 0 | 2 | 2 | 100% |
| REQ-BR-LRN (Learning) | 5 | 0 | 3 | 2 | 100% |
| REQ-BR-PLAN (Planning) | 3 | 0 | 0 | 3 | 100% |
| REQ-BR-MATH (Mathematics) | 4 | 3 | 1 | 0 | 100% |
| REQ-BR-SLEEP (Consolidation) | 3 | 0 | 1 | 2 | 100% |
| **Functional Total** | **38** | **9** | **17** | **12** | **100%** |
| NFR-PERF (Performance) | 6 | — | — | — | 100% |
| NFR-REL (Reliability) | 5 | — | — | — | 100% |
| NFR-SCAL (Scalability) | 3 | — | — | — | 100% |
| **Non-Functional Total** | **14** | — | — | — | **100%** |
| INT-* (Interfaces) | 14 | — | — | — | 100% |
| CON-* (Constraints) | 8 | — | — | — | Enforced |
| **GRAND TOTAL** | **74** | — | — | — | — |

### 6.2 Requirement-to-Test Mapping

| Requirement | Primary Test File(s) | Test Type |
|---|---|---|
| REQ-BR-MEM-001 | `proofs/category_b/test_memory_roundtrip.py` | Proof |
| REQ-BR-MEM-002 | `proofs/category_a/test_similarity_math.py` | Proof |
| REQ-BR-MEM-003 | `proofs/category_a/test_salience_math.py` | Proof |
| REQ-BR-MEM-004 | `proofs/category_a/test_hrr_math.py` | Proof |
| REQ-BR-MEM-005 | `proofs/category_b/test_ltm_search.py` | Proof |
| REQ-BR-MEM-006 | `proofs/category_a/test_salience_math.py` | Proof |
| REQ-BR-MEM-007 | `integration/test_milvus_integration.py` | Integration |
| REQ-BR-MEM-008 | `proofs/category_e/test_outbox_replay.py` | Proof |
| REQ-BR-COG-001 | `proofs/category_c/test_context.py` | Proof |
| REQ-BR-COG-002 | `proofs/category_a/test_predictor_math.py` | Proof |
| REQ-BR-COG-003 | `proofs/category_c/test_context.py` | Proof |
| REQ-BR-COG-004 | `proofs/category_c/test_context.py` | Proof |
| REQ-BR-COG-005 | `proofs/category_c/test_neuromodulators.py` | Proof |
| REQ-BR-COG-006 | `proofs/category_f/test_degraded_mode.py` | Proof |
| REQ-BR-WM-001 | `proofs/category_b/test_wm_capacity.py` | Proof |
| REQ-BR-WM-002 | `proofs/category_b/test_wm_capacity.py` | Proof |
| REQ-BR-WM-003 | `proofs/category_b/test_wm_capacity.py` | Proof |
| REQ-BR-WM-004 | `proofs/category_b/test_memory_roundtrip.py` | Proof |
| REQ-BR-WM-005 | `proofs/category_a/test_wm_promotion.py` | Proof |
| REQ-BR-NEURO-001..004 | `proofs/category_c/test_neuromodulators.py` | Proof |
| REQ-BR-LRN-001 | `proofs/category_c/test_learning.py` | Proof |
| REQ-BR-LRN-002 | `integration/test_learning_proof.py` | Integration |
| REQ-BR-LRN-003 | `proofs/category_c/test_planning.py` | Proof |
| REQ-BR-LRN-004 | `proofs/category_c/test_learning.py` | Proof |
| REQ-BR-LRN-005 | `proofs/category_c/test_learning.py` | Proof |
| REQ-BR-PLAN-001..003 | `proofs/category_c/test_planning.py` | Proof |
| REQ-BR-MATH-001 | `proofs/category_a/test_hrr_math.py` | Proof |
| REQ-BR-MATH-002 | `proofs/category_a/test_hrr_math.py` | Proof |
| REQ-BR-MATH-003 | `proofs/category_a/test_similarity_math.py` | Proof |
| REQ-BR-MATH-004 | `proofs/category_a/test_hrr_math.py` | Proof |
| REQ-BR-SLEEP-001 | `proofs/category_b/test_ltm_search.py` | Proof |
| REQ-BR-SLEEP-002 | `proofs/category_b/test_fusion.py` | Proof |
| REQ-BR-SLEEP-003 | `proofs/category_b/test_wm_persistence.py` | Proof |

---

## 7. Cross-Reference to SRS_FULL.md

This SRS (SOMA-BR-SRS-001) formalizes the requirements defined in the master technical specification (`docs/SRS_FULL.md`, document ID SRS-SOMABRAIN-MASTER-001). The following table maps sections of the master SRS to their corresponding requirement groups in this document:

| SRS_FULL.md Section | This Document | Notes |
|---|---|---|
| §3 Cognitive Components (Brain Region Modules) | REQ-BR-MEM, REQ-BR-WM, REQ-BR-NEURO | Brain-region mapping to functional requirements |
| §3.2 Neuromodulator System | REQ-BR-NEURO | DA, 5-HT, NE, ACh baselines and bounds |
| §4 Mathematical Foundations | REQ-BR-MATH | GMD, HRR, BHDC, cosine similarity, FWHT |
| §5 API Reference | INT-001 through INT-014 | Django Ninja endpoint contracts |
| §6 Services Layer | REQ-BR-COG, REQ-BR-LRN, REQ-BR-PLAN | Service-level requirements |
| §7 Configuration | CON-005, CON-008 | Environment-driven configuration |

For detailed API specifications, configuration parameters, and implementation notes, refer to `docs/SRS_FULL.md`. This SRS takes precedence for requirement-level decisions; the master SRS provides implementation-level detail.

---

*End of document. This Software Requirements Specification conforms to the process and content requirements defined by ISO/IEC/IEEE 29148:2018.*
