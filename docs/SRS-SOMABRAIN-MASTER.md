# SomaBrain — Master Technical Specification
## ISO/IEC 25010 Compliant Documentation

| Document ID | SRS-SOMABRAIN-MASTER-001 |
|-------------|--------------------------|
| Version | 1.0.0 |
| Date | 2026-01-02 |
| Status | APPROVED |
| Classification | Internal - Engineering |

---

# TABLE OF CONTENTS

1. [Scope](#1-scope)
2. [Architecture Overview](#2-architecture-overview)
3. [Cognitive Components](#3-cognitive-components)
4. [Mathematical Foundations](#4-mathematical-foundations)
5. [API Reference](#5-api-reference)
6. [Services Layer](#6-services-layer)
7. [Configuration](#7-configuration)
8. [Migration Audit](#8-migration-audit)
9. [Action Items](#9-action-items)

---

# 1. SCOPE

## 1.1 Purpose
Complete technical specification for SomaBrain, the cognitive runtime of the SOMA stack.

## 1.2 System Overview
- **Project:** SomaBrain
- **Framework:** Django 5.1 + Django Ninja 1.3
- **Database:** PostgreSQL via Django ORM
- **Vector Store:** Milvus
- **Message Queue:** Apache Kafka
- **Policy Engine:** OPA (Open Policy Agent)

## 1.3 Compliance Status
| Metric | Value |
|--------|-------|
| SQLAlchemy imports | **0** |
| FastAPI imports | **0** |
| TODO comments | **1** (rate limiting) |
| VIBE Compliance | **99.8%** |
| Total Files | 377 |

---

# 2. ARCHITECTURE OVERVIEW

## 2.1 Project Structure

```
somabrain/
├── somabrain/              # Main Django app (377 files)
│   ├── api/                # Django Ninja API (76 files)
│   ├── services/           # Background services (27 files)
│   ├── memory/             # Memory subsystem (22 files)
│   ├── metrics/            # Prometheus metrics (22 files)
│   ├── aaas/               # Multi-tenant (21 files)
│   ├── brain/              # Cognitive core (5 files)
│   ├── math/               # Mathematical modules (10 files)
│   └── [74 standalone modules]
├── tests/                  # Test suite (80 files)
└── manage.py               # Django entry point
```

## 2.2 Port Namespace

| Service | Port |
|---------|------|
| API | 30101 |
| Redis | 30100 |
| Kafka | 30102 |
| OPA | 30104 |
| Prometheus | 30105 |
| Postgres | 30106 |

---

# 3. COGNITIVE COMPONENTS

## 3.1 Brain Region Modules

| Module | Lines | Biological Analog | Purpose |
|--------|-------|-------------------|---------|
| `neuromodulators.py` | 334 | Neurotransmitters | Dopamine, Serotonin, Noradrenaline, Acetylcholine |
| `wm.py` | 546 | Prefrontal buffer | Working memory, salience, capacity limits |
| `hippocampus.py` | 112 | Hippocampus | Memory consolidation, WM→LTM promotion |
| `amygdala.py` | 260 | Amygdala | Salience scoring, store/act gating |
| `prefrontal.py` | 108 | Prefrontal cortex | Executive control |
| `thalamus.py` | 86 | Thalamus | Sensory gating, attention routing |
| `consolidation.py` | 203 | Sleep cycles | NREM/REM consolidation |

## 3.2 Neuromodulator System

| Neurotransmitter | Range | Default | Function |
|------------------|-------|---------|----------|
| Dopamine | 0.2 - 0.8 | 0.4 | Motivation, error weighting |
| Serotonin | 0.0 - 1.0 | 0.5 | Emotional stability |
| Noradrenaline | 0.0 - 0.1 | 0.0 | Urgency, arousal |
| Acetylcholine | 0.0 - 0.1 | 0.0 | Attention, focus |

## 3.3 Working Memory

**Properties:**
- Vector-based storage with cosine similarity recall
- Fixed capacity with automatic eviction
- Salience: `α×novelty + β×reward + γ×recency`
- WM→LTM promotion when salience ≥ 0.85 for 3+ ticks

---

# 4. MATHEMATICAL FOUNDATIONS

## 4.1 Holographic Reduced Representations (HRR)
**File:** `quantum_pure.py` (159 lines)

```
bind(a, b) = IFFT(FFT(a) × FFT(b))      # Circular convolution
unbind(c, b) = IFFT(FFT(c) / FFT(b))    # Frequency-domain division
superpose(*vecs) = normalize(Σ vecs)    # Additive superposition
```

## 4.2 Cosine Similarity
**File:** `math/similarity.py` (183 lines)

```
cosine(a, b) = (a · b) / (||a|| × ||b||)
```

**Properties (property-tested):**
1. Symmetric: `cosine(a, b) == cosine(b, a)`
2. Self-similarity: `cosine(a, a) == 1.0`
3. Bounded: `-1.0 ≤ cosine(a, b) ≤ 1.0`

## 4.3 Sparse Distributed Representations
**File:** `sdr.py` (252 lines)
- BLAKE2b hashing for deterministic k-active bits
- LSH banding for approximate nearest neighbor

## 4.4 Spectral Algorithms
**File:** `math/lanczos_chebyshev.py` (158 lines)
- Lanczos for spectral interval estimation
- Chebyshev polynomial for heat kernel: `exp(-t × A)`

---

# 5. API REFERENCE

## 5.1 Django Ninja Configuration

```python
# urls.py (9341 bytes)
from ninja import NinjaAPI
api = NinjaAPI(title="SomaBrain Cognitive API", version="1.0.0")
```

## 5.2 Endpoint Categories

| Router | Endpoints | Purpose |
|--------|-----------|---------|
| `/api/v1/memory/` | CRUD | Memory operations |
| `/api/v1/recall/` | Search | Semantic recall |
| `/api/v1/tenants/` | CRUD | Tenant management |
| `/api/v1/health/` | Probes | Liveness/readiness |
| `/api/v1/metrics/` | Prometheus | Metrics export |

---

# 6. SERVICES LAYER

## 6.1 Background Services (27 files)

| Service | Purpose |
|---------|---------|
| `cognitive_loop_service.py` | eval_step() - core loop |
| `integrator_hub_triplet.py` | Tripartite belief fusion |
| `memory_service.py` | Memory orchestration |
| `recall_service.py` | Semantic search |

## 6.2 IntegratorHub - Belief Fusion

**Leader Selection Formula:**
```python
weights = {d: math.exp(-alpha × error) for d, error in domain_errors.items()}
leader = softmax_select(weights, temperature)
```

---

# 7. CONFIGURATION

## 7.1 Environment Variables

| Variable | Purpose |
|----------|---------|
| `SOMABRAIN_MODE` | dev/staging/production |
| `SOMABRAIN_POSTGRES_DSN` | Database connection |
| `SOMABRAIN_REDIS_URL` | Cache connection |
| `SOMABRAIN_KAFKA_URL` | Event bus |
| `SOMABRAIN_OPA_URL` | Policy engine |
| `SOMABRAIN_MEMORY_HTTP_ENDPOINT` | SomaFractalMemory URL |

---

# 8. MIGRATION AUDIT

## 8.1 Compliance Matrix

| Category | Files | SQLAlchemy | FastAPI | TODOs | Score |
|----------|-------|------------|---------|-------|-------|
| somabrain/* | 377 | 0 | 0 | 1 | 99.7% |
| services/* | 27 | 0 | 0 | 0 | 100% |
| **TOTAL** | **404** | **0** | **0** | **1** | **99.8%** |

## 8.2 Single TODO Found

| File | Line | Content | Priority |
|------|------|---------|----------|
| `api/endpoints/auth.py` | 134 | "rate limiting (TODO)" | LOW |

---

# 9. ACTION ITEMS

| ID | Item | Priority | Effort |
|----|------|----------|--------|
| REQ-001 | Implement rate limiting | LOW | 0.5 days |

**Total Effort: 0.5 days**

---

**END OF DOCUMENT**

*SRS-SOMABRAIN-MASTER-001 v1.0.0*
