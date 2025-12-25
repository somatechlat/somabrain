# User Manual

**Purpose** Explain how to interact with SomaBrain’s public API to store memories, recall context, and drive cognitive workflows.

**Audience** Product developers, application engineers, and operators who call the SomaBrain API directly.

**Prerequisites** A running SomaBrain stack (see [Installation](installation.md)), familiarity with HTTP/JSON, and a tenant credential issued by your platform administrator.

---

## What SomaBrain Provides

SomaBrain is a FastAPI service that exposes cognitive memory and planning primitives. The production binary defined in `somabrain/app.py` wires together:

- `/remember` for episodic memory ingestion handled by `somabrain.services.memory_service.MemoryService`.
- `/recall` for semantic retrieval backed by working memory (`somabrain.mt_wm.MultiTenantWM`) and long‑term storage via the external memory HTTP service.
- `/context/evaluate` and `/context/feedback` for end‑to‑end reasoning loops that exercise the BHDC `QuantumLayer`, `ContextBuilder`, `ContextPlanner`, and `AdaptationEngine`.
- Optional flows such as `/act`, `/plan/suggest`, and `/sleep/run` that are enabled when the full stack is running.

All endpoints are authenticated, tenant‑scoped, and observable with Prometheus metrics emitted from the same runtime.

---

## Quick Navigation

- [Installation](installation.md) – Bring up the Docker stack (API + Redis + Kafka + OPA + Prometheus + Postgres).
- [Quick Start Tutorial](quick-start-tutorial.md) – Issue your first `remember → recall → feedback` sequence.
- [Features](features/) – Detailed guides for each API:
  - [Memory Operations](features/memory-operations.md) – `/remember`, `/recall`, cleanup and quotas.
  - [Cognitive Reasoning](features/cognitive-reasoning.md) – `/context/evaluate`, `/context/feedback`, neuromodulators.
  - [API Integration](features/api-integration.md) – Headers, error handling, rate limits.
  - [Multi-tenant Usage](features/multi-tenant-usage.md) – Tenant isolation, namespaces, quotas.
- [FAQ](faq.md) – Troubleshooting common client issues.

---

## How to Use This Manual

1. Confirm the stack is running (`docker compose ps` and `/health` response) using the [Installation](installation.md) checklist.
2. Follow the [Quick Start Tutorial](quick-start-tutorial.md) to store a memory and verify retrieval with real JSON samples taken from the running API.
3. Deep‑dive into the [Features](features/) section for specialised workflows:
   - Memory ingestion & recall (payload schemas from `somabrain/schemas.py`).
   - Planning and adaptation (grounded in `somabrain/context` and `somabrain/learning` modules).
   - Multi‑tenant isolation and quotas.
4. Keep the [FAQ](faq.md) and the [Technical Manual](../technical-manual/index.md) handy for operational and diagnostic tasks.

Each page includes prerequisites, verification steps, and references so you can audit the behaviour you see against the live codebase.

---

**Related Manuals**

- [Technical Manual](../technical-manual/index.md) – Deployment, observability, runbooks.
- [Development Manual](../development-manual/index.md) – Contributing code and running tests.
- [Onboarding Manual](../onboarding-manual/index.md) – Project orientation for new contributors.
