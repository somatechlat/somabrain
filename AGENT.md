# SomaBrain - Agent Context

> Purpose: Provide a single, accurate reference for agents working on the SomaBrain repo.
> Last updated: 2026-10-09

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
9. **COGNITION ALWAYS ON — 100% FULL CAPACITY (HARD LAW).**
   - SomaBrain boots with every cognitive function ACTIVE. No default-OFF cognitive flags.
   - Hippocampus · amygdala · prefrontal · basal ganglia · neuromodulators · learner · planner · meta-brain · OAK · microcircuits · soft salience · drift monitor · SDR · graph augment · HRR-first · exec controller · memory weighting · entropy cap · dynamic LR · learning loop — ALL ON, and they run on **every** memory cycle (remember/recall/promote), not only `/act`.
   - Feature flags are **kill-switch / emergency-degrade only**. Never ship a half-thinking brain.
   - Returning empty results because a cog flag is off is a **DEFECT**. `{"plan": []}` when planner is disabled is a **LIE**.
   - Enforcement: `settings/cognitive.py` defaults · `runtime/modes.py` ModeConfig · `docs/VIBE_RULES.md` · tests.

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
│   ├── settings/              # Django settings (cognitive, django_core, infra, neuro) + BrainSetting DB overlay
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

## Configuration & Secrets (Law)

> **SETTINGS LAW (binding, every agent, every change):**
> **Settings = Django + `BrainSetting` / agent DB** (administerable).
> **Secrets = Vault ONLY** (Covenant Art 26).
> **No file presets. No env secrets. No `.env` as authority.**
> Violations are defects — see `docs/iso/SOMA-BR-SEC-001.md` §8.

**Covenant Art 26 — Secret Protection:**
> "Production secrets shall reside exclusively in secure vault systems. Storage in code, configuration files, or environment variables is prohibited."

| Plane | Authority | Rule |
|---|---|---|
| **Secrets** | **Vault ONLY** | Never in code, files, `.env`, or environment variables (Art 26) |
| **Settings** | **Django settings + `BrainSetting` (agent DB, administerable)** | No file presets. No env secrets. |

Environment variables are **not** a secrets authority and not the settings authority.
Secrets are read from Vault at runtime. Settings are administered through Django
settings modules (`somabrain/settings/`) and the `BrainSetting` DB overlay
(`somabrain/brain_settings/models.py`).

**Settings** (Django / `BrainSetting` — administerable):

- `SOMABRAIN_MODE` (dev|staging|production)
- `SOMABRAIN_REDIS_URL`, `SOMABRAIN_KAFKA_URL`, `SOMABRAIN_OPA_URL` (topology)
- BrainSetting `memory_http_endpoint` (SFM URL) — read via `managed_get`
- `SOMABRAIN_AUTH_REQUIRED`
- `SOMABRAIN_USE_HRR` (default true), `SOMABRAIN_MATH_BHDC_MIX` (`none|hadamard`)
- `SOMABRAIN_MEMORY_FAST_ACK` (default true → accept `durable_outbox`)
- `SOMABRAIN_JWT_PUBLIC_KEY_PATH`, `SOMABRAIN_JWT_AUDIENCE`, `SOMABRAIN_JWT_ISSUER`

**Secrets** (Vault ONLY — never env, never files):

- `secret/agent/credentials[somabrain_memory_http_token]` — **shared** agent↔brain↔SFM bearer
- `somafractalmemory/database[password]`
- `somabrain/auth[jwt_secret]`
- `SOMABRAIN_PROVENANCE_SECRET` (required only if `SOMABRAIN_REQUIRE_PROVENANCE`)

**Ops truth (read before grepping code):** `docs/iso/SOMA-BR-OPS-RUNBOOK-001.md`
(vault root path, topology keys, dual-store roles, remember proofs).

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
- **DOCUMENT-REGISTER.md** — tracking index for every controlled `docs/**/*.md` (status, version, compliance)
- **SOMA-BR-DOCS-001.md** — document control and traceability procedure

### Living documentation roles (doc governance)

| Role | Canonical sources | Update when |
|---|---|---|
| **Constitution** | `AGENT.md` · `docs/VIBE_RULES.md` · `docs/THE-SOMA-COVENANT.md` | Binding rules, law, or covenant change |
| **Map** | `docs/iso/SOMA-BR-ARCH-001.md` | Architecture, components, or data flow change |
| **Status** | `docs/iso/SOMA-BR-DEBT-001.md` · `docs/iso/SOMA-BR-PLAN-MASTER-001.md` | Debt, waves, or plan state change |
| **History** | `docs/plans/a2a/LEDGER.md` · `docs/iso/SOMA-BR-DEBT-001.md` | Commits, waves, proofs, audits (append-only ledger + debt rows) |

Do not invent parallel "source of truth" documents. If it is not in this table and not in `docs/iso/DOCUMENT-REGISTER.md`, it is not controlled documentation.

---

## Configuration Tuning (Meta-Controller)

SomaBrain applies named cognitive presets (`stable`, `plastic`, `lateral`) per tenant via `somabrain/services/parameter_supervisor.py` → `somabrain/admin/core/presets.py`. The administerable surface is **BrainSetting** (75 registry keys in `somabrain/brain_settings/models.py` as of 2026-10-09) plus Django settings modules — not "300+ parameters".

```python
from somabrain.services.parameter_supervisor import ParameterSupervisor
await ParameterSupervisor(config_svc).apply_preset(tenant="t1", preset_name="plastic")
```

Config map (truth): `docs/iso/SOMA-BR-CONFIG-API-TEST-001.md`.

## Runtime truth (2026-10-09)

**Operator law — zero optional paths (2026-10-09):** `optional_setting()` / `optional_url()` deleted from `settings/resolve.py`. Only `require_setting` / `require_url` / `require_tenant` / `require_namespace` remain. `MemoryClient` is HTTP-only (direct mode deleted). `SOMA_API_TOKEN` is required. Health/URLs use `require_url` for OPA/MinIO/Schema-Registry — no soft "not configured".

**Fail-closed memory:** `memory/hybrid.py` deleted. `utils.fetch_by_coord`, `milvus_ann.search`, `payloads_for_coords` raise on outage. `remember_bulk` partial fallback raises with failed indexes. Client outbox `IntegrityError` is an idempotent replay (H3); `aremember_background` raises (H4); `mark_sent` warns (M5). Ranking: dim mismatch raises; unscorable + `query_vec` refuses inventing 0.0.

**One auth builder (R5):** `somabrain/memory/sfm_auth.py` `build_sfm_request_headers` is the only Brain→SFM header builder (both HTTP surfaces).

**Layer vocabulary:** `wm` | `ltm` | `both` only (`api/memory/helpers.normalize_layer`). No `all` alias. Namespace is not a layer.

**Tenant fail-closed:** SFM store/retrieve/delete/search/graph, learning (`learner_online`/`learner_dlq`/`memory_events`), WM, and `graph_ops` require a tenant — no default. `predictor_gamma` in `BRAIN_DEFAULTS` at `-0.5` (bounds `[-1.0, 1.0]`).

**DEBT-008 CLOSED / DEBT-010 CLOSED:** Rust sole adaptation-math authority; `check_entropy_cap` sharpens (α,β,γ) only.

- **Rust core `somabrain_rs` is the sole adaptation-math authority** (DEBT-008 closed). `learning/adaptation/rust_math.py` delegates to `somabrain_rs`; missing module → `RuntimeError` (no Python gain-law twin). BHDC / Wiener / neuromod also live in `rust_core`. `cargo test` 17/17.
- **Brain learns from memory/agent interactions** (APM): recall hit/miss, store, promote, forget, `/context/feedback` move weights. Proven unit + live.
- **HRR/QuantumLayer is additive** on embed path (`SOMABRAIN_USE_HRR` default true via `require_setting`, provider `hrr`, JL→768 seam). Tiny embed is used only when `SOMABRAIN_USE_HRR` is explicitly `False`; init failure raises (no silent Tiny fallback).
- **Settings law:** Django + BrainSetting/agent DB (administerable). **Secrets: Vault only** (Covenant Art 26). No env secrets. No file presets.
- **Prune/decay knobs** (BrainSetting): `memory_decay_rate`, `wm_prune_threshold`, `ltm_prune_threshold`, `max_wm_items`, `max_ltm_items_per_tenant`.
