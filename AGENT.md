# SomaBrain - Agent Context

> Purpose: Provide a single, accurate reference for agents working on the SomaBrain repo.
> Last updated: 2026-10-04

---

## MANDATORY RULES (every agent, every task)

These override convenience. Source of truth: `docs/VIBE_RULES.md` (SOMA-BR-GUIDE-VIBE-001) and `docs/THE-SOMA-COVENANT.md`.

1. **NO SHIMS. NO FAKES. NO BYPASSES.**
   - No mocks, stubs, placeholders, TODOs, compat facades, re-export shims, temporary hacks, hardcoded returns.
   - No flags that hide unfinished behavior.
   - If it is not real production behavior: **delete it or fully implement it**.
2. **NO BULLSHIT** — no lies, guesses, invented APIs, "it probably works". Say what is true; if it may break, say so.
3. **CHECK FIRST, CODE SECOND** — read architecture and call sites before writing. Request missing files. Do not assume.
4. **REAL IMPLEMENTATIONS ONLY** — production-grade, type-annotated (Covenant Art 23).
5. **DOCUMENTATION = TRUTH** — docs, comments, and math proofs must match the code. Wrong equations in docs are defects. No hype ("perfect/flawless") unless warranted.
6. **COMPLETE CONTEXT** — data flow, callers, callees, dependencies, impact before any edit. Missing context → ASK.
7. **REAL DATA & SERVERS** (Covenant Art 21/24) — verify against real infra. Django ORM + Milvus only (Art 22).
8. **Math must be correct** and **docs must reflect the math**.

### Multi-persona (always)

PhD Software Developer · Analyst · QA · ISO-style Documenter (structure only) · Security Auditor · Performance Engineer · UX · Django Architect.

### Agent fan-out standard

When spawning subagents, **always** include: (1) this rules block, (2) full file paths for the scope, (3) relevant audit/equation context, (4) explicit no-shim/no-fake/no-bypass instruction, (5) acceptance criteria. Never send bare prompts.

---

---

## Quick Summary

SomaBrain is a Django Ninja cognitive runtime. It exposes a REST API, runs
cognitive services (predictors, integrator, memory orchestration), and depends
on external infrastructure (Redis, Kafka, OPA, Postgres, Milvus, Prometheus)
and an external memory HTTP service (SomaFractalMemory or compatible).

---

## Software Modes

- **Deployment posture (implemented):** `SOMABRAIN_MODE` in `somabrain/mode.py`
  (`dev`, `staging`, `production`) controls auth/OPA strictness, required
  backends, and minimum replicas.
- **System software mode (platform requirement):** `StandAlone` vs
  `SomaStackClusterMode` is defined at the platform level (see
  `somaAgent01/docs/srs/SRS-UNIFIED-AAAS.md`). SomaBrain must pair with
  SomaFractalMemory in integrated mode via `SOMABRAIN_MEMORY_HTTP_ENDPOINT`.

---

## Project Structure

```
somabrain/
├── somabrain/                 # Django app + runtime core
│   ├── api/                   # API endpoints
│   ├── services/              # Retrieval, integrator, predictors
│   ├── memory/                # Memory logic and transport
│   ├── settings/              # Env-backed settings (django_core.py, infra.py, etc.)
│   ├── core/mode.py           # Deployment posture profiles
│   └── runtime/modes.py       # Runtime mode definitions
├── services/                  # Non-Django service processes
├── config/                    # Runtime config files
├── docs/                      # Documentation (flat structure)
│   ├── README.md              # Docs index
│   ├── ONBOARDING.md          # Project orientation
│   ├── USER_GUIDE.md          # Usage guide
│   ├── OPS_MANUAL.md          # Ops + runbooks
│   ├── SRS_FULL.md            # Requirements
│   ├── CONTRIBUTING.md        # Contribution guidelines
│   ├── VIBE_RULES.md          # VIBE coding rules
│   └── SomabrainGMD.md        # Mathematical notes
├── tests/                     # Test suites
│   ├── unit/
│   ├── integration/
│   ├── smoke/                 # Manual smoke scripts (not pytest-collected)
│   ├── benchmarks/
│   └── support/
└── infra/standalone/docker-compose.yml  # Local stack
```

---

## Key Runtime Entry Points

- API router: `somabrain/api/v1.py`
- Settings/env: `somabrain/settings/django_core.py`, `somabrain/settings/infra.py`
- Mode profiles: `somabrain/core/mode.py`, `somabrain/runtime/modes.py`
- Retrieval pipeline: `somabrain/services/retrieval_pipeline.py`
- Integrator hub: `somabrain/services/integrator_hub_triplet.py`
- Predictors: `somabrain/predictors/base.py`

---

## Core Environment Variables

From `somabrain/settings.py`:

- `SOMABRAIN_MODE` (dev|staging|production)
- `SOMABRAIN_POSTGRES_DSN`
- `SOMABRAIN_REDIS_URL`
- `SOMABRAIN_KAFKA_URL`
- `SOMABRAIN_OPA_URL`
- `SOMABRAIN_MEMORY_HTTP_ENDPOINT`
- `SOMABRAIN_MEMORY_HTTP_TOKEN`
- `SOMABRAIN_AUTH_REQUIRED`
- `SOMABRAIN_API_TOKEN`
- `SOMABRAIN_JWT_SECRET`
- `SOMABRAIN_JWT_PUBLIC_KEY_PATH`
- `SOMABRAIN_JWT_AUDIENCE`
- `SOMABRAIN_JWT_ISSUER`

---

## Ports (Docker Compose Defaults)

- API: 30101 (host and container)
- Redis: 30100
- Kafka: 30102
- OPA: 30104
- Prometheus: 30105
- Postgres: 30106
- Postgres exporter: 30107
- Kafka exporter: 30103
- Schema registry: 30108

---

## SomaStack Hierarchy

```
SomaStack/
├── shared/             # Port 49000-49099 (Keycloak, etc.)
├── SomaFractalMemory/  # Port 21000-21099
├── SomaBrain/          # Port 30000-30199 ← THIS REPO
└── SomaAgent01/        # Port 20000-20199
```

---

## Development with Tilt

```bash
# Start infrastructure
colima start
minikube start

# Deploy SomaStack (includes SomaBrain)
cd somaAgent01
tilt up --port 10351

# SomaStack Tilt Dashboard
open http://localhost:10351
```

---

## Testing Notes

- Tests require real infrastructure; no mocks in integration suites.
- `tests/smoke/` scripts are manual smoke checks and are ignored by pytest.
- `tests/integration/` covers real-service integration (Kafka, Milvus, memory HTTP).

---

## Key Documentation

- VIBE Coding Rules: `docs/VIBE_RULES.md`
- Docs index: `docs/README.md`
- Onboarding: `docs/ONBOARDING.md`
- User Guide: `docs/USER_GUIDE.md`
- OPS Manual: `docs/OPS_MANUAL.md`
- SRS: `docs/SRS_FULL.md`

### ISO Documentation Suite (v2.0.0)

ISO-compliant documentation in `docs/iso/`:

- **SOMA-BR-ARCH-001.md** (ISO/IEC 42010) — Architecture: GMD algorithm, deployment modes, views, Rust core, services, integrations, multi-tenancy, observability, known debt
- **SOMA-BR-AUDIT-001.md** (ISO 19011) — Audit: Executive scorecard (Arch A-, Code B+, Tests A-, Docs A-, Security B+), strengths, weaknesses, recommendations
- **SOMA-BR-SEC-001.md** (ISO/IEC 27001) — Security: JWT, OPA, constitution signing, TLS, Vault, per-tenant isolation, threat model
- **SOMA-BR-RISK-001.md** (ISO 31000) — Risk Register: complexity debt, SFM dependency, Kafka availability, Milvus scaling, calibration drift
- **SOMA-BR-PROD-001.md** (ISO/IEC 25010) — Production Readiness: scorecard (3.96/5.00), standalone GO, AAAS CONDITIONAL GO, K8s status, Helm charts

---

## Configuration Tuning (Meta-Controller)

SomaBrain exposes **Cognitive Presets** to manage its 300+ parameters without manual tuning.

*   **Stable** (Default): Reliable, factual. Low plasticity.
*   **Plastic**: High learning rate, high dopamine. Best for rapid adaptation.
*   **Lateral**: High temperature, high entropy. Best for creative tasks.

**Usage:**

```python
from somabrain.services.parameter_supervisor import ParameterSupervisor
await ParameterSupervisor(config_svc).apply_preset(tenant="t1", preset_name="plastic")
```

See `docs/technical/configuration_optimization.md` for the full strategy.
