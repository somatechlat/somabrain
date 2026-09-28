# SOMA-BR-SDP-001: SomaBrain Software Development Plan

> **Standard:** ISO/IEC 12207:2017 — Systems and Software Engineering — Software Life Cycle Processes
> **Owner:** SomaTech Engineering

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SomaBrain Software Development Plan |
| Document Identifier | SOMA-BR-SDP-001 |
| Version | 1.0.1 |
| Date | 2026-06-15 |
| Status | Approved |
| Author | SomaTech Engineering |
| Approver | VP Engineering, SomaTech |
| Classification | Internal |
| ISO Reference | ISO/IEC 12207:2017 — Systems and Software Engineering — Software Life Cycle Processes |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-06-15 | SomaTech Engineering | Initial SDP: ISO/IEC 12207 compliant development plan for SomaBrain |
| 1.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-BR-SDP-001` \| Status added as `Approved` (document names an approver). |

### Normative References

| Document ID | Title | Relationship |
|---|---|---|
| SOMA-BR-ARCH-001 | SomaBrain Architecture Document | Architecture baseline governing design decisions |
| SOMA-BR-SRS-001 | SomaBrain Software Requirements Specification | Requirements baseline governing implementation |
| SOMA-BR-SEC-001 | SomaBrain Security Assessment | Security controls governing secure development |
| SOMA-BR-VV-001 | SomaBrain Verification and Validation Plan | V&V plan governing testing activities |
| docs/SRS_FULL.md | SomaBrain Master Technical Specification | Detailed functional specification |
| docs/VIBE_RULES.md | SomaBrain VIBE Coding Standards | Coding conventions enforced during development |
| ISO/IEC 12207:2017 | Software Life Cycle Processes | Governing standard for this document |

---

## Table of Contents

1. [Lifecycle Model](#1-lifecycle-model)
2. [Development Processes](#2-development-processes)
3. [Tools and Infrastructure](#3-tools-and-infrastructure)
4. [Configuration Management](#4-configuration-management)
5. [Rust Core Development](#5-rust-core-development)
6. [Testing Strategy](#6-testing-strategy)
7. [Review and Audit Schedule](#7-review-and-audit-schedule)

---

## 1. Lifecycle Model

### 1.1 Model Selection

SomaBrain follows an **iterative development lifecycle** organized into four phases, aligned with the executable planning model defined in SOMA-BR-EXEC-001. The lifecycle is not strictly waterfall; phases overlap and features may advance through multiple iterations.

### 1.2 Phase Definitions

| Phase | Name | Objective | Entry Criteria | Exit Criteria |
|---|---|---|---|---|
| P1 | **Docs** | Requirements elaboration, architecture design, specification | Business need identified | Requirements baseline approved (SRS) |
| P2 | **Integration** | Service implementation, infrastructure wiring, API contracts | Design approved | Services communicate end-to-end; integration tests pass |
| P3 | **Hardening** | Performance tuning, reliability hardening, security validation | Integration tests pass | SLOs met; security review complete; chaos tests pass |
| P4 | **Validation** | Acceptance testing, production readiness review, deployment | Hardening metrics met | Go/No-Go decision per SOMA-BR-PROD-001 |

### 1.3 Phase Overlap

```
P1 Docs          ████████████
P2 Integration        ████████████████
P3 Hardening                   ████████████████
P4 Validation                           ████████████
                 ────────────────────────────────────→ time
```

Phases overlap intentionally: documentation evolves alongside integration, and hardening begins before all integration work completes.

### 1.4 Current Status

| Phase | Status | Notes |
|---|---|---|
| P1 Docs | **Complete** | SRS, architecture, security, risk, audit documents all at v2.0.0 |
| P2 Integration | **Complete** | All services operational; 95 test files passing |
| P3 Hardening | **In Progress** | Standalone mode hardened; AAAS validation ongoing |
| P4 Validation | **Pending** | Conditional Go per SOMA-BR-PROD-001 |

---

## 2. Development Processes

### 2.1 Requirements Process

| Activity | Source | Process |
|---|---|---|
| Requirements elicitation | SomaTech stakeholders, SomaStack ecosystem needs | Interviews, architecture reviews, RFC process |
| Requirements specification | SOMA-BR-SRS-001 | Formal REQ-BR-* IDs with traceability |
| Requirements validation | `docs/SRS_FULL.md` | Technical review against implementation |
| Requirements change control | Git pull requests | Changes require architecture team approval |

### 2.2 Design Process

| Activity | Source | Process |
|---|---|---|
| Architecture design | SOMA-BR-ARCH-001 | ISO/IEC 42010 viewpoint-based architecture |
| Detailed design | Code-level docstrings and inline comments | Module-level design as part of implementation |
| Design review | Architecture team | Pull request review for structural changes |
| Design patterns | Brain-region metaphor, service layer, cognitive presets | Consistent patterns across codebase |

### 2.3 Implementation Process

| Activity | Standard | Enforcement |
|---|---|---|
| Coding conventions | `docs/VIBE_RULES.md` | Pre-commit hooks (Black, Ruff, mypy) |
| Zero TODO/FIXME | VIBE Rule: no deferred work in production code | Automated scan in CI |
| Django-only ORM | No SQLAlchemy imports | Automated import check in CI |
| Django Ninja API | No FastAPI imports | Automated import check in CI |
| Python 3.12 | Pinned runtime version | pyproject.toml, Dockerfile |
| Type annotations | Full type annotations on public APIs | mypy strict mode |
| Code review | All changes require at least one approval | Git branch protection |

### 2.4 Testing Process

| Test Level | Count | Framework | Purpose |
|---|---|---|---|
| Unit tests | 5 files | pytest | Individual module correctness |
| Property-based tests | 11 files | pytest + Hypothesis | Invariant verification with random inputs |
| Integration tests | 14 files | pytest + real services | End-to-end service interaction |
| Proof tests | ~60 files (8 categories) | pytest | Mathematical and behavioral proofs |
| Benchmark tests | 2 files | pytest + custom harness | Performance regression detection |
| E2E tests | 3 files | pytest | Full system health and integration |

---

## 3. Tools and Infrastructure

### 3.1 Development Stack

| Category | Tool | Version | Purpose |
|---|---|---|---|
| **Language** | Python | 3.12 | Primary implementation language |
| **Framework** | Django | 5.1 | Web framework, ORM, middleware |
| **API** | Django Ninja | 1.3 | API layer (schema-first, OpenAPI) |
| **Accelerator** | Rust | 1.75+ | Performance-critical algorithms via PyO3 |
| **Rust Bindings** | PyO3 | 0.20+ | Python ↔ Rust interop |
| **Rust Build** | maturin | 1.4+ | Build and package Rust extensions |
| **Database** | PostgreSQL | 15+ | Relational persistence (Django ORM) |
| **Cache** | Redis | 7+ | Caching, sessions, working memory state |
| **Vector Store** | Milvus | 2.3+ | HNSW-indexed vector similarity |
| **Message Queue** | Apache Kafka | 3.x+ | Cognitive event pipeline (5 topics) |
| **Schema Registry** | Confluent | 7.x+ | Avro schema management (17 schemas) |
| **Policy Engine** | OPA | 0.50+ | Policy-as-code authorization |
| **Secrets** | HashiCorp Vault | 1.x+ | Dynamic secrets, key rotation |

### 3.2 Quality Tools

| Category | Tool | Purpose |
|---|---|---|
| **Formatting** | Black | Deterministic Python code formatting |
| **Linting** | Ruff | Fast Python linting (replaces flake8, isort, etc.) |
| **Type Checking** | mypy | Static type analysis |
| **Type Checking** | pyright | Additional type checking (Microsoft) |
| **Testing** | pytest | Test runner and assertions |
| **Property Testing** | Hypothesis | Property-based test generation |
| **Pre-commit** | pre-commit | Git hook management |

### 3.3 Deployment and Operations

| Category | Tool | Purpose |
|---|---|---|
| **Containerization** | Docker | Application packaging |
| **Orchestration** | Kubernetes (K8s) | Container orchestration (AAAS mode) |
| **Package Manager** | Helm | K8s application packaging |
| **Local Dev** | Tilt | Development-time K8s workflow |
| **Monitoring** | Prometheus | Metrics collection (30+ metric modules) |
| **Visualization** | Grafana | Metrics dashboards |
| **Tracing** | OpenTelemetry | Distributed tracing (Jaeger, OTLP, Zipkin) |

---

## 4. Configuration Management

### 4.1 Version Control

| Aspect | Policy |
|---|---|
| **VCS** | Git (GitHub) |
| **Branching** | Feature branches from main; merge via pull request |
| **Branch Protection** | Main branch requires PR approval, passing CI, and no merge conflicts |
| **Tagging** | Semantic version tags (`v0.2.0`, etc.) |
| **Commit Messages** | Conventional Commits format |

### 4.2 Semantic Versioning

SomaBrain follows Semantic Versioning 2.0.0:

| Component | Version | Meaning |
|---|---|---|
| **Major** (X.0.0) | Breaking changes | Incompatible API changes |
| **Minor** (0.X.0) | New features | Backward compatible additions |
| **Patch** (0.0.X) | Bug fixes | Backward compatible fixes |

Current version: **0.2.0**

### 4.3 Pre-commit Hooks

| Hook | Tool | Enforcement |
|---|---|---|
| Code formatting | Black | Auto-format on commit |
| Import sorting | Ruff (isort) | Auto-sort on commit |
| Linting | Ruff (flake8 rules) | Block commit on violations |
| Type checking | mypy | Block commit on type errors |
| VIBE compliance | Custom checks | Block commit on TODO/FIXME markers |

### 4.4 Environment Configuration

| Variable Class | Examples | Management |
|---|---|---|
| **Runtime** | `SOMABRAIN_MODE`, `SOMABRAIN_AUTH_REQUIRED` | `.env` file + K8s ConfigMap |
| **Secrets** | `SOMABRAIN_POSTGRES_DSN`, `SOMABRAIN_JWT_SECRET` | Vault or K8s Secrets |
| **Integration** | `SOMABRAIN_MEMORY_HTTP_ENDPOINT`, `SOMABRAIN_KAFKA_BROKERS` | `.env` file + K8s ConfigMap |
| **Observability** | `SOMABRAIN_OTEL_EXPORTER_*` | `.env` file + K8s ConfigMap |

---

## 5. Rust Core Development

### 5.1 Overview

The Rust core provides performance-critical computation via PyO3 bindings, totaling **1,782 LOC** across 5 modules. The Rust core is built with maturin and exposed as a Python extension module.

### 5.2 Build System

| Aspect | Tool/Configuration |
|---|---|
| **Build Tool** | maturin (PEP 517 build backend for Rust extensions) |
| **Manifest** | `rust_core/Cargo.toml` |
| **Python Bindings** | PyO3 0.20+ |
| **Output** | `somabrain.rust_core` Python module |
| **Fallback** | Pure Python implementations when Rust extension unavailable |

### 5.3 Module Inventory

| Module | File | LOC | Responsibility |
|---|---|---|---|
| **BHDC** | `rust_core/src/bhdc.rs` | ~450 | Binary HDC encoding, FWHT, sparse vector operations |
| **MathCore** | `rust_core/src/mathcore.rs` | ~380 | Cosine similarity, vector normalization, batch operations |
| **Neuro** | `rust_core/src/neuro.rs` | ~320 | Neuromodulator simulation, synaptic plasticity rules |
| **Prediction** | `rust_core/src/prediction.rs` | ~310 | Linear predictors, diffusion prediction, surprise computation |
| **Adaptation** | `rust_core/src/adaptation.rs` | ~322 | TD learning, UCB1, drift detection, parameter updates |

### 5.4 Development Workflow

```
1. Implement algorithm in Rust (rust_core/src/*.rs)
2. Define PyO3 bindings (#[pyfunction], #[pyclass])
3. Build with maturin develop (local) or maturin build --release (CI)
4. Import in Python: from somabrain.rust_core import *
5. Write property-based tests in Python (Hypothesis)
6. Write Rust unit tests (#[cfg(test)])
7. Benchmark against pure Python fallback
```

### 5.5 Rust-Python Interface Contract

| Rust Function | Python Interface | Input | Output |
|---|---|---|---|
| `bhdc_encode` | `somabrain.rust_core.bhdc_encode` | Feature vector, dimension, density | Binary hypervector |
| `bhdc_similarity` | `somabrain.rust_core.bhdc_similarity` | Two binary hypervectors | Cosine similarity (float) |
| `fwht_transform` | `somabrain.rust_core.fwht` | Input vector | Walsh-Hadamard transform |
| `cosine_similarity_batch` | `somabrain.rust_core.cosine_batch` | Query vector, matrix | Similarity scores array |
| `td_update` | `somabrain.rust_core.td_update` | Reward, V(s), V(s'), α, γ | TD error δ, weight update Δw |

---

## 6. Testing Strategy

### 6.1 Test Pyramid

```
                    ┌──────────┐
                    │  E2E (3) │
                    ├──────────┤
                ┌───┤ Bench(2) ├───┐
                │   └──────────┘   │
          ┌─────┤                  ├─────┐
          │ Integration (14)       │     │
          └─────┤                  ├─────┘
                │  Property (11)   │
                └──────┤  ├───────┘
                       │  │
                ┌──────┤  ├───────┐
                │   Unit (5)      │
                └─────────────────┘
                │   Proofs (~60)  │
                └─────────────────┘
```

### 6.2 Test Inventory by Category

| Category | File Count | Framework | Directory |
|---|---|---|---|
| Unit | 5 | pytest | `tests/unit/` |
| Property-based | 11 | pytest + Hypothesis | `tests/property/` |
| Integration | 14 | pytest + real services | `tests/integration/` |
| E2E | 3 | pytest | `tests/e2e/` |
| Benchmark | 2 | pytest + custom | `tests/benchmarks/` |
| Proof — Category A (Math) | 5 | pytest | `tests/proofs/category_a/` |
| Proof — Category B (Memory) | 7 | pytest | `tests/proofs/category_b/` |
| Proof — Category C (Cognitive) | 5 | pytest | `tests/proofs/category_c/` |
| Proof — Category D (Isolation) | 3 | pytest | `tests/proofs/category_d/` |
| Proof — Category E (Resilience) | 4 | pytest | `tests/proofs/category_e/` |
| Proof — Category F (Fault Tolerance) | 5 | pytest | `tests/proofs/category_f/` |
| Proof — Category G (Performance) | 5 | pytest | `tests/proofs/category_g/` |
| Proof — Category H (Observability) | 3 | pytest | `tests/proofs/category_h/` |
| Support/Conftest | 5 | — | `tests/`, `tests/support/`, `tests/fixtures/` |
| **Total** | **~95** | — | — |

### 6.3 Mathematical Proof Categories (A–H)

| Category | Name | Assertion Type | Example |
|---|---|---|---|
| **A** | Mathematical Foundations | Invariant assertions | HRR binding inverse accuracy, cosine bounds, WM norm preservation |
| **B** | Memory Operations | Roundtrip and capacity | Memory store-recall roundtrip, WM capacity enforcement, LTM search quality |
| **C** | Cognitive Pipeline | Behavioral proofs | Neuromodulator bounds, learning convergence, planning correctness |
| **D** | Isolation | Cross-tenant invariants | Memory isolation, state isolation between tenants |
| **E** | Resilience | Failure recovery | Outbox replay, health verification, memory E2E recovery |
| **F** | Fault Tolerance | Degraded mode | Circuit breaker state machine, per-tenant circuits, degraded mode operation |
| **G** | Performance | SLO compliance | Latency SLOs, throughput targets, serialization efficiency |
| **H** | Observability | Metric presence | Distributed tracing spans, integration metric coverage |

### 6.4 Property-Based Testing (Hypothesis)

11 property-based test files verify invariants with randomly generated inputs:

| Test File | Properties Verified |
|---|---|
| `test_similarity_properties.py` | Cosine similarity symmetry, bounds [−1,1], self-similarity = 1 |
| `test_memory_properties.py` | Memory state norm preservation, GMD convergence |
| `test_memory_system_properties.py` | System-level memory invariants |
| `test_math_core_properties.py` | Vector normalization, dot product commutativity |
| `test_predictor_properties.py` | Prediction vector bounds, surprise signal non-negativity |
| `test_learning_properties.py` | TD error convergence, weight update bounds |
| `test_normalization_properties.py` | Norm preservation after normalization |
| `test_multitenancy_serialization.py` | Tenant ID preservation through serialization |
| `test_route_preservation.py` | API route consistency across configurations |
| `test_forbidden_terms.py` | Absence of forbidden imports (SQLAlchemy, FastAPI) |
| `test_dead_code_removal.py` | No unreachable code paths |

### 6.5 Test Execution Matrix

| Test Type | Local | CI | Nightly | Pre-Release |
|---|---|---|---|---|
| Unit | ✅ | ✅ | ✅ | ✅ |
| Property-based | ✅ | ✅ | ✅ | ✅ |
| Integration | ⚠️ (needs infra) | ✅ | ✅ | ✅ |
| E2E | ⚠️ (needs infra) | ✅ | ✅ | ✅ |
| Benchmark | Manual | ❌ | ✅ | ✅ |
| Proofs | ✅ | ✅ | ✅ | ✅ |

---

## 7. Review and Audit Schedule

### 7.1 Review Types

| Review Type | Frequency | Scope | Participants |
|---|---|---|---|
| **Code Review** | Every PR | All code changes | Author + 1 reviewer |
| **Architecture Review** | Quarterly | Structural changes, new modules | Architecture team |
| **Security Review** | Semi-annually | Security controls, auth, isolation | Security team + Architecture team |
| **ISO Compliance Audit** | Annually | Full ISO document suite | QA team + external auditor |
| **Production Readiness Review** | Per release | Go/No-Go assessment | VP Engineering + all teams |

### 7.2 Audit Calendar (2026)

| Date | Activity | Document |
|---|---|---|
| 2026-06-15 | ISO compliance audit (current) | All SOMA-BR-* documents |
| 2026-09-15 | Risk register review | SOMA-BR-RISK-001 |
| 2026-09-15 | Architecture document review | SOMA-BR-ARCH-001 |
| 2026-12-15 | Full ISO re-audit | All SOMA-BR-* documents |
| 2026-12-15 | Security re-assessment | SOMA-BR-SEC-001 |

### 7.3 Quality Gates

| Gate | Trigger | Criteria | Decision Authority |
|---|---|---|---|
| **Code Merge** | Pull request | All CI checks pass; 1+ approval | Tech lead |
| **Feature Complete** | Phase P2 exit | All REQ-BR-* implemented; integration tests pass | Architecture team |
| **Hardened** | Phase P3 exit | SLOs met; security review complete; chaos tests pass | Operations team |
| **Release** | Phase P4 exit | Go/No-Go per SOMA-BR-PROD-001 | VP Engineering |

---

*End of document. This Software Development Plan conforms to the process definitions of ISO/IEC 12207:2017.*
