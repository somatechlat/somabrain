# SOMA-BR-ARCH-001: SomaBrain Architecture Document

> **Standard:** ISO/IEC 42010:2011 — Systems and Software Engineering — Architecture Description
> **Owner:** SomaTech Architecture Team

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SomaBrain Architecture Document |
| Document Identifier | SOMA-BR-ARCH-001 |
| Version | 2.0.1 |
| Date | 2026-06-15 |
| Status | Approved |
| Author | SomaTech Architecture Team |
| Approver | CTO, SomaTech |
| Classification | Internal |
| ISO Reference | ISO/IEC 42010:2011 — Systems and Software Engineering — Architecture Description |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-01-15 | Architecture Team | Initial architecture baseline |
| 1.1.0 | 2026-03-01 | Architecture Team | Added AAAS deployment mode, Rust core section |
| 1.2.0 | 2026-04-20 | Architecture Team | Expanded integration points, multi-tenancy section |
| 2.0.0 | 2026-06-15 | Architecture Team | Full rewrite: ISO/IEC 42010 compliant, all views updated, Rust core expansion, observability and debt sections added |
| 2.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-BR-ARCH-001` \| Status added as `Approved` (document names an approver). |

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [The Governed Trace Algorithm (GMD)](#2-the-governed-trace-algorithm-gmd)
3. [Deployment Modes](#3-deployment-modes)
4. [Architecture Views](#4-architecture-views)
5. [Core Algorithms](#5-core-algorithms)
6. [Rust Core](#6-rust-core)
7. [Service Layer](#7-service-layer)
8. [Integration Points](#8-integration-points)
9. [Multi-Tenancy](#9-multi-tenancy)
10. [Observability](#10-observability)
11. [Known Technical Debt](#11-known-technical-debt)

---

## 1. Purpose and Scope

### 1.1 Purpose

SomaBrain is a **Hyperdimensional Cognitive Memory System** designed to provide persistent, biologically-inspired memory capabilities for autonomous AI agents. It implements a Governed Trace memory model grounded in hyperdimensional computing (HDC) theory, enabling agents to store, retrieve, and reason over episodic and semantic memories with constant-time complexity.

### 1.2 Scope

This document describes the software architecture of SomaBrain across all architectural viewpoints defined by ISO/IEC 42010:2011. It covers:

- The mathematical foundation (GMD algorithm)
- Dual deployment topologies (Standalone and AAAS)
- Logical, process, and physical architecture views
- Core algorithmic components
- The Rust acceleration core
- Service-layer composition
- Integration boundaries with the SomaStack ecosystem
- Multi-tenancy isolation model
- Observability infrastructure
- Known technical debt

### 1.3 System Context

SomaBrain operates within the **SomaStack** ecosystem:

| Component | Role | Port Range |
|---|---|---|
| SomaBrain | Cognitive memory engine | 9696 (standalone) / 63996 (AAAS) |
| SomaAgent01 | Agent orchestration gateway | 63900 |
| SomaFractalMemory | Distributed long-term storage | 63901 |
| SomaStack AAAS | Admin dashboard UI | — |

### 1.4 Codebase Metrics

| Metric | Value |
|---|---|
| Python LOC | 116,735 |
| Rust LOC | 1,782 |
| Total LOC | 118,517 |
| Test Files | 95 |
| Test Proof Categories | 8 |

---

## 2. The Governed Trace Algorithm (GMD)

### 2.1 Definition

The Governed Trace (GMD) is the core memory update mechanism, inspired by the complementary learning systems theory (McClelland et al., 1995):

$$\mathbf{m}_t = (1 - \eta)\mathbf{m}_{t-1} + \eta\mathbf{b}_t$$

| Symbol | Name | Description |
|---|---|---|
| $\mathbf{m}_t$ | Memory State | Current high-dimensional superposition vector at time $t$ |
| $\mathbf{b}_t$ | Input Vector | New sparse, orthogonal memory trace |
| $\eta$ | Plasticity Gain | Controls update strength; $\eta \in (0, 1)$ |
| $(1-\eta)$ | Decay Factor | Exponential forgetting mechanism |

### 2.2 Mathematical Properties

**Property 1 — Bounded Norm.** If $\|\mathbf{m}_0\| \leq 1$ and $\|\mathbf{b}_t\| \leq 1$ for all $t$, then:

$$\|\mathbf{m}_t\| \leq (1-\eta)\|\mathbf{m}_{t-1}\| + \eta\|\mathbf{b}_t\| \leq 1$$

The memory state remains within the unit hypersphere.

**Property 2 — Exponential Forgetting.** In the absence of new input ($\mathbf{b}_t = \mathbf{0}$):

$$\|\mathbf{m}_t\| = (1-\eta)^t \|\mathbf{m}_0\| \to 0 \text{ as } t \to \infty$$

**Property 3 — Approximate Orthogonality.** In $\mathbb{R}^N$ with $N \gg 1$:

$$\mathbb{E}[\mathbf{x} \cdot \mathbf{y}] \approx 0 \quad \text{for random unit vectors } \mathbf{x}, \mathbf{y}$$

This enables high-capacity associative memory with interference bounded by $O(1/\sqrt{N})$.

**Property 4 — Constant-Time Retrieval.** Similarity search against the superposition state requires a single dot product: $O(N)$ compute, constant in the number of stored traces (given fixed $N$).

### 2.3 Adaptive Plasticity Gain

The plasticity gain $\eta$ is not static. It is modulated by:

- **Neuromodulator levels:** Dopamine increases $\eta$ (enhanced learning); serotonin stabilizes it.
- **Surprise signal:** High prediction error increases $\eta$ temporarily.
- **Salience:** High-importance inputs receive elevated $\eta$.
- **Cognitive preset:** `Stable`, `Plastic`, or `Lateral` presets adjust baseline $\eta$.

---

## 3. Deployment Modes

### 3.1 Standalone Mode

SomaBrain operates as a **single-tenant**, self-contained cognitive memory service.

| Property | Value |
|---|---|
| Port | 9696 |
| Tenancy | Single-tenant |
| Dependencies | PostgreSQL, Redis, Milvus, Kafka (optional), OPA (optional) |
| Memory Backend | Milvus (local) or in-process |
| Auth | Optional JWT; configurable strictness via `SOMABRAIN_MODE` |
| Configuration | `SOMABRAIN_MODE=dev\|staging\|production` |

**Use Case:** Development, evaluation, research, and small-scale production deployments where a single agent or user requires memory services.

### 3.2 AAAS (As-a-Service) Mode

SomaBrain operates as a **multi-tenant** service within the integrated SomaStack cluster.

| Property | Value |
|---|---|
| Port | 63996 |
| Tenancy | Multi-tenant (cryptographic isolation) |
| SomaAgent01 | Port 63900 — agent orchestration, client SDK |
| SomaFractalMemory | Port 63901 — distributed long-term storage, HTTP + optional direct import |
| Memory Backend | Milvus (clustered) + SomaFractalMemory |
| Auth | Mandatory JWT; OPA policy enforcement |
| Configuration | `SOMABRAIN_MODE=production` + AAAS platform flags |

**Use Case:** Production deployments serving multiple agents or users through the SomaStack ecosystem.

### 3.3 Mode Detection

```python
# somabrain/mode.py
# SOMABRAIN_MODE controls deployment posture profiles:
#   dev       → relaxed auth, optional backends
#   staging   → enforced auth, required backends
#   production → strict auth, OPA enforcement, all backends required

# somabrain/runtime/modes.py
# StandAlone vs SomaStackClusterMode determined at platform level
```

---

## 4. Architecture Views

### 4.1 Logical View — Cognitive Loop

The cognitive loop is the central processing pipeline, composed of three interacting subsystems:

#### 4.1.1 Predictors

Diffusion-backed predictive models that generate expectations about incoming data. When input deviates from prediction, the surprise signal modulates plasticity gain.

- **Base:** `somabrain/predictors/base.py`
- **Types:** Linear predictors, diffusion-backed predictors
- **Output:** Prediction vector $\hat{\mathbf{b}}_t$, surprise signal $s_t$

#### 4.1.2 Integrator

The integrator (hub-triplet architecture) fuses signals from multiple sources:

- Sensory input
- Predictor output
- Working memory state
- Neuromodulator levels

**Implementation:** `somabrain/services/integrator_hub_triplet.py`

#### 4.1.3 Segmentation

HMM-based temporal segmentation divides continuous input streams into discrete episodes for memory encoding.

- **Implementation:** `somabrain/services/segmentation_service.py`
- **Algorithm:** Hidden Markov Model with Viterbi decoding
- **Output:** Episode boundaries, segment labels

### 4.2 Logical View — Memory Plane

The memory plane manages three tiers of memory:

| Tier | Component | Capacity | Latency | Persistence |
|---|---|---|---|---|
| Working Memory (WM) | `wm.py` | 64 slots (configurable) | < 2ms | In-process, volatile |
| Long-Term Memory (LTM) | `hippocampus.py` | 12M+ memories | < 15ms | PostgreSQL + Milvus |
| External Memory | SomaFractalMemory | Unbounded | < 50ms | Distributed storage |

**Consolidation Flow:**

```
WM (salience-gated) → Consolidation Queue → Hippocampus (LTM) → SomaFractalMemory (optional)
```

**NREM/REM Cycles:**
- **NREM:** Batch consolidation of high-salience WM items to LTM; pattern extraction.
- **REM:** Associative recombination; creative memory linking; schema integration.

### 4.3 Logical View — Brain Regions

SomaBrain models cortical and subcortical brain regions as functional modules:

| Region | Module | Responsibility |
|---|---|---|
| **Prefrontal Cortex** | `prefrontal.py` | Executive planning, goal maintenance, cognitive switching, inhibition |
| **Thalamus** | Gating logic in WM | Attention gating, signal relay, filtering |
| **Amygdala** | `amygdala.py` | Emotional valence tagging, threat/reward assessment |
| **Hippocampus** | `hippocampus.py` | Episodic encoding, consolidation, spatial-temporal indexing |
| **Basal Ganglia** | `adaptation_engine.py` | Action selection, reward learning, habit formation |

**Neuromodulator Panel:**

| Modulator | Symbol | Baseline | Role |
|---|---|---|---|
| Dopamine | DA | 0.4 | Reward prediction, plasticity gain |
| Serotonin | 5-HT | 0.52 | Mood stabilization, patience |
| Norepinephrine | NE | 0.12 | Alertness, arousal |
| Acetylcholine | ACh | 0.31 | Attention, learning rate |

### 4.4 Process View — Cognitive Pipeline

The cognitive pipeline operates as a series of Kafka topics (`cog.*` namespace):

```
Input → cog.perceive → Predictors → cog.predict
                                    ↓
                          Integrator → cog.integrate
                                    ↓
                          Segmenter → cog.segment
                                    ↓
                          Memory Plane → cog.store
                                    ↓
                          Output / Response
```

**Kafka Topics (5):**

| Topic | Purpose |
|---|---|
| `cog.perceive` | Raw sensory input ingestion |
| `cog.predict` | Predictor outputs and surprise signals |
| `cog.integrate` | Fused cognitive state |
| `cog.segment` | Episode boundaries and segment metadata |
| `cog.store` | Memory commit events |

### 4.5 Process View — Retrieval Pipeline

The retrieval pipeline (`somabrain/services/retrieval_pipeline.py`) executes parallel retrieval across four strategies:

1. **Vector Retriever:** Milvus cosine similarity search over HDC-encoded memories
2. **Working Memory Retriever:** Direct scan of WM slots by salience
3. **Graph Retriever:** Knowledge graph traversal for associative recall
4. **Lexical Retriever:** Full-text search with BM25 scoring

Results are merged, deduplicated, and ranked by composite score.

### 4.6 Process View — Adaptation Engine

The adaptation engine (`somabrain/services/`) implements temporal-difference (TD) learning for continuous model improvement:

- **UCB1 Attention:** Upper Confidence Bound for exploration/exploitation in memory retrieval
- **TD Learning:** $\delta_t = r_t + \gamma V(s_{t+1}) - V(s_t)$ for reward-modulated updates
- **Drift Detection:** Monitors input distribution shifts; triggers recalibration

### 4.7 Physical View

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer / Ingress                   │
│                   (TLS termination, routing)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  Django + Ninja API Layer                     │
│            somabrain/api/v1.py  (port 9696/63996)            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  /memory/*   │  │   /admin/*   │  │   /health/*      │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Service Layer                              │
│  retrieval_pipeline │ memory_service │ integrator_hub_triplet│
│  learner_online │ segmentation_service │ orchestrator_service│
│  calibration_service │ adaptation_engine                     │
└──────────┬──────────┬──────────┬──────────┬─────────────────┘
           │          │          │          │
    ┌──────▼───┐ ┌────▼────┐ ┌──▼───┐ ┌───▼────┐
    │PostgreSQL│ │  Redis  │ │Milvus│ │ Kafka  │
    │  (ORM +  │ │ (cache, │ │(HNSW │ │(event  │
    │  state)  │ │ sessions│ │index)│ │stream) │
    └──────────┘ └─────────┘ └──────┘ └────────┘
           │
    ┌──────▼──────────┐
    │  Rust Core       │
    │  (PyO3 bindings) │
    │  bhdc, mathcore, │
    │  neuro, predict, │
    │  adaptation      │
    └─────────────────┘
```

---

## 5. Core Algorithms

### 5.1 BHDC Encoding

**File:** `rust_core/src/bhdc.rs`

Binary Hyperdimensional Computing encoding transforms input features into high-dimensional binary vectors. Uses Walsh-Hadamard transforms for efficient binding and permutation operations.

- **Dimension:** Configurable (default 8,192)
- **Density:** 2% sparse activation
- **Operations:** Bind ($\circledast$), bundle ($\oplus$), permute ($\rho$), similarity ($\cos$)

### 5.2 HRR Context Engine

**File:** `somabrain/context_hrr.py`

Holographic Reduced Representations (Plate, 2003) for compositional structure encoding:

- `encode(x) → ℝ^8192`: Map features to hypervector
- `bind(a, b) → a ⊛ b`: Circular convolution binding
- `unbind(c, a) → b`: Approximate inverse binding

### 5.3 Cosine Similarity

**File:** `somabrain/math/similarity.py`

Vector similarity computation optimized for high-dimensional sparse vectors:

$$\text{sim}(\mathbf{a}, \mathbf{b}) = \frac{\mathbf{a} \cdot \mathbf{b}}{\|\mathbf{a}\| \|\mathbf{b}\|}$$

### 5.4 Fast Walsh-Hadamard Transform (FWHT)

Used by BHDC for $O(N \log N)$ binding operations in lieu of $O(N^2)$ circular convolution.

### 5.5 HMM Segmentation

**File:** `somabrain/services/segmentation_service.py`

Hidden Markov Model with Viterbi decoding for temporal episode segmentation:

- States: Episode types (episodic, semantic, procedural)
- Observations: Feature vectors from cognitive pipeline
- Transitions: Learned from experience via Baum-Welch

### 5.6 UCB1 Attention

Upper Confidence Bound algorithm applied to memory slot selection:

$$\text{UCB1}(i) = \bar{x}_i + \sqrt{\frac{2 \ln N}{n_i}}$$

Balances exploitation of high-salience memories with exploration of under-retrieved ones.

### 5.7 Diffusion-Backed Predictors

Predictive models that generate forward-looking expectations using diffusion processes. Enable surprise-driven plasticity modulation.

### 5.8 Adaptation Engine with TD Learning

**File:** `somabrain/services/adaptation_engine.py`

Temporal-difference learning for continuous cognitive parameter adjustment:

$$\delta_t = r_t + \gamma V(s_{t+1}) - V(s_t)$$
$$\Delta w = \alpha \cdot \delta_t \cdot \nabla_w V(s_t)$$

Parameters (learning rate $\alpha$, discount factor $\gamma$) are modulated by neuromodulator levels.

---

## 6. Rust Core

### 6.1 Overview

The Rust core provides performance-critical computation via PyO3 bindings, totaling **1,782 LOC** across 5 modules.

### 6.2 Module Inventory

| Module | File | LOC | Responsibility |
|---|---|---|---|
| BHDC | `rust_core/src/bhdc.rs` | ~450 | Binary HDC encoding, FWHT, sparse vector operations |
| MathCore | `rust_core/src/mathcore.rs` | ~380 | Cosine similarity, vector normalization, batch operations |
| Neuro | `rust_core/src/neuro.rs` | ~320 | Neuromodulator simulation, synaptic plasticity rules |
| Prediction | `rust_core/src/prediction.rs` | ~310 | Linear predictors, diffusion prediction, surprise computation |
| Adaptation | `rust_core/src/adaptation.rs` | ~322 | TD learning, UCB1, drift detection, parameter updates |

### 6.3 PyO3 Integration

```python
# Example: BHDC encoding via Rust
from somabrain.rust_core import bhdc_encode, bhdc_similarity

vector = bhdc_encode(features, dimension=8192, density=0.02)
score = bhdc_similarity(vector_a, vector_b)
```

The Python service layer calls Rust functions transparently. Fallback to pure Python implementations exists when the Rust extension is unavailable.

---

## 7. Service Layer

### 7.1 Service Inventory

| Service | File | Purpose |
|---|---|---|
| Retrieval Pipeline | `somabrain/services/retrieval_pipeline.py` | Multi-strategy parallel memory retrieval |
| Memory Service | `somabrain/services/memory_service.py` | CRUD operations on memory stores |
| Integrator Hub | `somabrain/services/integrator_hub_triplet.py` | Hub-triplet signal fusion |
| Online Learner | `somabrain/services/learner_online.py` | Continuous learning from feedback |
| Segmentation Service | `somabrain/services/segmentation_service.py` | HMM-based episode segmentation |
| Orchestrator Service | `somabrain/services/orchestrator_service.py` | Pipeline coordination and scheduling |
| Calibration Service | `somabrain/services/calibration_service.py` | Neuromodulator and parameter calibration |
| Adaptation Engine | `somabrain/services/adaptation_engine.py` | TD learning and UCB1 attention |
| Parameter Supervisor | `somabrain/services/parameter_supervisor.py` | Cognitive preset management |

### 7.2 Cognitive Presets

Three presets govern the 300+ tunable parameters:

| Preset | Plasticity | Dopamine | Temperature | Use Case |
|---|---|---|---|---|
| **Stable** | Low | Baseline | Low | Reliable, factual retrieval |
| **Plastic** | High | Elevated | Medium | Rapid adaptation, learning |
| **Lateral** | Medium | Baseline | High | Creative, exploratory tasks |

---

## 8. Integration Points

### 8.1 SomaFractalMemory (Port 63901)

| Aspect | Details |
|---|---|
| Protocol | HTTP REST API |
| Transport | `SOMABRAIN_MEMORY_HTTP_ENDPOINT` environment variable |
| Auth | Bearer token via `SOMABRAIN_MEMORY_HTTP_TOKEN` |
| Optional | Direct Python import for in-process access |
| Use Case | Long-term distributed memory persistence, cross-agent memory sharing |

### 8.2 SomaAgent01 (Port 63900)

| Aspect | Details |
|---|---|
| Protocol | Client SDK (Python) |
| Direction | SomaAgent01 → SomaBrain (request/response) |
| Auth | JWT tokens issued by SomaAgent01 |
| Use Case | Agent orchestration, memory query routing |

### 8.3 Kafka (Event Streaming)

**5 Topics, 17 Avro Schemas:**

| Topic | Avro Schemas | Description |
|---|---|---|
| `cog.perceive` | 4 | Raw input, features, metadata, context |
| `cog.predict` | 3 | Prediction, surprise signal, confidence |
| `cog.integrate` | 4 | Fused state, components, weights, drift |
| `cog.segment` | 3 | Episode boundary, segment type, transition |
| `cog.store` | 3 | Memory commit, confirmation, index update |

Schema registry: Port 30108 (Docker compose default).

---

## 9. Multi-Tenancy

### 9.1 Isolation Model

SomaBrain implements cryptographic tenant isolation in AAAS mode:

| Mechanism | Description |
|---|---|
| **Tenant ID Extraction** | From JWT claims; validated per request |
| **Memory Isolation** | Per-tenant Milvus collections and Redis key prefixes |
| **Circuit Breakers** | Per-tenant circuit breakers prevent one tenant's failures from cascading |
| **Quotas** | Per-tenant rate limits, memory capacity limits, API call quotas |
| **Constitution Signing** | Tenant operations signed with tenant-specific keys |

### 9.2 Resource Governance

```
Tenant Request → JWT Validation → Tenant ID Extraction
                                  ↓
                    Per-Tenant Circuit Breaker Check
                                  ↓
                    Per-Tenant Quota Enforcement
                                  ↓
                    Namespace-Scoped Memory Access
                                  ↓
                    Response (tenant-filtered)
```

---

## 10. Observability

### 10.1 Metrics (Prometheus)

SomaBrain exposes **30+ Prometheus metric modules** covering:

| Category | Example Metrics |
|---|---|
| API Performance | `soma_api_request_duration_seconds`, `soma_api_requests_total` |
| Memory Operations | `soma_memory_store_duration_seconds`, `soma_memory_recall_hits_total` |
| Cognitive Pipeline | `soma_cog_predictor_surprise`, `soma_cog_integrator_drift` |
| Neuromodulators | `soma_neuro_dopamine_level`, `soma_neuro_serotonin_level` |
| Infrastructure | `soma_kafka_lag`, `soma_milvus_query_duration`, `soma_redis_hit_ratio` |
| Tenancy | `soma_tenant_requests_total`, `soma_tenant_circuit_breaker_state` |
| Rust Core | `soma_rust_bhdc_encode_duration`, `soma_rust_similarity_duration` |

**Default scrape endpoint:** `/metrics` on the API port.

### 10.2 Distributed Tracing (OpenTelemetry)

- **Tracer:** OpenTelemetry SDK with configurable exporter (Jaeger, OTLP, Zipkin)
- **Propagation:** W3C TraceContext headers
- **Span Coverage:** API requests, memory operations, Kafka produce/consume, Milvus queries, Rust core calls
- **Configuration:** `SOMABRAIN_OTEL_EXPORTER_*` environment variables

### 10.3 Logging

- **Format:** Structured JSON (production), human-readable (development)
- **PII Masking:** Automatic detection and redaction in log output
- **Audit Trail:** All memory mutations logged with tenant ID, timestamp, operation hash

---

## 11. Known Technical Debt

### 11.1 Codebase Complexity

- **116,735 Python LOC** represents significant cognitive load for onboarding and review.
- Some modules have accumulated organic growth patterns that benefit from refactoring.
- Mitigation: Progressive modularization; this architecture document serves as a navigation aid.

### 11.2 Audit Report Overlap

- Multiple audit reports (security, architecture, production readiness) share overlapping sections.
- Mitigation: This document serves as the single architectural reference; audit reports reference back.

### 11.3 Documentation Gaps

- No automated API documentation generation (Sphinx/MkDocs) currently integrated into CI.
- VIBE coding rules enforcement mechanism is defined but enforcement automation is unclear.
- Mitigation: Track as action items in the production readiness assessment.

### 11.4 Configuration Sprawl

- 300+ tunable parameters; cognitive presets mitigate but do not eliminate complexity.
- Mitigation: Parameter Supervisor with preset-based governance.

---

*End of document. This architecture description conforms to the viewpoint structure defined by ISO/IEC 42010:2011.*
