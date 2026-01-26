# SomaBrain - Agent Context

> Purpose: Provide a single, accurate reference for agents working on the SomaBrain repo.
> Last updated: 2026-01-01

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
│   ├── settings.py            # Env-backed settings
│   └── mode.py                # Deployment posture profiles
├── services/                  # Non-Django service processes
├── config/                    # Runtime config files
├── docs/                      # Documentation
│   ├── README.md              # Docs index
│   ├── overview.md            # Product overview
│   ├── development/           # Dev manual + VIBE rules
│   ├── technical/             # Technical manual
│   ├── user/                  # User manual
│   ├── onboarding/            # Onboarding
│   ├── operations/            # Ops + runbooks
│   └── srs/                    # Requirements
├── tests/                     # Test suites
│   ├── unit/
│   ├── integration/
│   ├── smoke/                 # Manual smoke scripts (not pytest-collected)
│   ├── benchmarks/
│   └── support/
└── docker-compose.yml          # Local stack
```

---

## Key Runtime Entry Points

- API router: `somabrain/api/v1.py`
- Settings/env: `somabrain/settings.py`
- Mode profiles: `somabrain/mode.py`
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

- API: host 30101 -> container 9696
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

- VIBE Coding Rules: `docs/development/VIBE_CODING_RULES.md`
- Docs index: `docs/README.md`
- Overview: `docs/overview.md`
- Deployment: `docs/deployment/`
- Technical manual: `docs/technical/`
- Runbooks: `docs/operations/`

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
