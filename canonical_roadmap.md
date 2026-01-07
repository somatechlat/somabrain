# Somabrain Canonical Roadmap – Sprint Plan (VIBE‑Compliant)

**Version:** 1.0 (Draft) – merged 2025‑11‑25
**Generated on:** 2025‑11‑27

This document translates the **ROAMDP** specifications and the identified **gap analysis** into a concrete, sprint‑based development plan that obeys the **VIBE coding rules** (no stubs, no hard‑coded values, single‑source configuration, full observability, and strict Avro usage).

---
## 📅 Sprint Schedule (14 weeks total)
| Sprint | Duration (weeks) | Focus Area | Key Deliverables (code‑only, no placeholders) |
|-------|------------------|------------|----------------------------------------------|
| **0** | 1 | **Preparation & Context Alignment** | • Confirm repository state (no hidden stubs).<br>• Freeze `main` branch for two weeks.<br>• Add `ENABLE_OAK` flag to `common/config/settings.py`.<br>• Extend `libs/kafka_cog/avro_schemas.py` with `option_created` & `option_updated` schemas.<br>• Update `scripts/ci/forbid_stubs.sh` to forbid any new stub keywords. |
| **1** | 2 | **Infrastructure Provisioning** | • Deploy Milvus cluster (dev & prod) via Helm.<br>• Deploy Keycloak (OIDC) and OPA side‑car with `option.rego` policy.<br>• Verify Prometheus & Grafana dashboards for new Oak metrics (`option_utility_avg`, `option_count`). |
| **2** | 3 | **Core Oak Option Layer** | • Implement `somabrain/oak/option_manager.py` (real `Option` dataclass, utility calculation, EMA model updates, JSON persistence via `memory_client`, Avro publishing).<br>• Implement `somabrain/oak/planner.py` (deterministic Dijkstra search, similarity threshold from `settings.OAK_SIMILARITY_THRESHOLD`, latency ≤ 200 ms for ≤ 500 options).<br>• Add FastAPI routes `/oak/option/create`, `/oak/option/{id}`, `/oak/plan` in `somabrain/app.py` with OPA enforcement. |
| **3** | 2 | **Stateless FastAPI + Milvus Refactor** | • Create `somabrain/milvus_client.py` (strict connection handling, collection creation, binary IVF‑FLAT index, `upsert` & `search` methods).<br>• Refactor `somabrain/memory_client.py` to delegate option persistence to `MilvusClient` (no Redis usage for vectors).<br>• Ensure all numeric constants are read from `settings` (e.g., `settings.MEMORY_DIM`). |
| **4** | 1 | **Migration tooling** | • Write `scripts/migrate_redis_to_milvus.py` (dry‑run checksum verification, tenant‑partitioned inserts, idempotent).<br>• Add unit tests for migration logic (no mocks – use an in‑memory Milvus instance). |
| **5** | 2 | **CI/CD & Canary Deployment** | • Extend `requirements.txt` with `pymilvus`.<br>• Update Dockerfile to install Milvus SDK, remove Redis client.
• GitHub Actions workflow: build image, run full test suite (including Oak), push Helm chart, deploy Canary (10 % traffic). |
| **6** | 2 | **Full Production Rollout** | • Scale Oak‑enabled pods to 100 % traffic.
• Decommission Redis service (verify no connections remain).
• Confirm all metrics (`option_*`, `oak_planner_latency_seconds`) are scraped and alerting rules are active. |
| **7** | 1 | **Post‑Rollout Optimisation** | • Tune Milvus index parameters (`nlist`, `efConstruction`, `ef`).
• Add per‑tenant rate‑limiting rules to `option.rego`.
• Optional hot‑path LRU cache for most‑frequent options (implemented as a thin wrapper around `functools.lru_cache`). |
| **8** | 1 | **Documentation & Handover** | • Update `openapi.yaml` with Oak endpoints.
• Add `docs/technical-manual/oak_integration.md` (architecture, API contract, Avro schema description).
• Export Grafana dashboard JSON (`infra/grafana/oak_dashboard.json`). |

---
## ✅ Compliance Checklist (VIBE Rules)
- **No Stubs / No Hard‑Coded Values** – All numeric thresholds (`OAK_SIMILARITY_THRESHOLD`, `OAK_TAU_MIN`, etc.) are defined in `settings.py`.
- **Single Source of Truth** – Configuration, Avro schemas, and feature flags live in one place.
- **Real Implementations** – Every module (`option_manager`, `planner`, `milvus_client`) contains complete, testable code.
- **Observability** – Prometheus gauges, Grafana dashboards, and structured logs are added alongside each new feature.
- **Security** – OPA policies (`option.rego`) enforce RBAC on every Oak endpoint.
- **Documentation** – OpenAPI spec, markdown runbooks, and Avro schema comments are provided.
- **Testing** – Full unit and integration tests (no mocks) are required before each sprint is marked complete.

---
## 📦 Deliverables per Sprint
| Sprint | Files Added / Modified | Tests Added | Metrics Updated |
|-------|-----------------------|------------|-----------------|
| 0 | `settings.py`, `avro_schemas.py`, `forbid_stubs.sh` | None (baseline) | None |
| 1 | Helm charts (`milvus`, `keycloak`, `opa`), `option.rego` | None (infra) | New Oak metrics placeholders |
| 2 | `oak/option_manager.py`, `oak/planner.py`, FastAPI routes in `app.py` | Unit tests for `Option` and `Planner` | `option_utility_avg`, `option_count`, `oak_planner_latency_seconds` |
| 3 | `milvus_client.py`, refactor `memory_client.py` | Integration tests against a local Milvus container | Milvus‑specific latency metrics |
| 4 | `scripts/migrate_redis_to_milvus.py` | Migration test suite (real Milvus) | Migration‑status metrics |
| 5 | CI workflow, Dockerfile, requirements | CI runs all existing tests + Oak tests | CI‑pipeline metrics |
| 6 | Helm release with 100 % traffic, Redis removal scripts | End‑to‑end smoke test | Production‑ready metrics |
| 7 | Milvus index tuning scripts, OPA rate‑limit updates | Performance benchmark tests | Updated latency histograms |
| 8 | Documentation files, OpenAPI update, Grafana JSON | Documentation lint tests | Dashboard validation |

---
## 📌 Next Immediate Action
Start **Sprint 0**:
1. Open `common/config/settings.py` and add the `ENABLE_OAK` flag and all Oak‑related numeric settings.
2. Add the two Avro schemas to `proto/cog/` and register them in `libs/kafka_cog/avro_schemas.py`.
3. Extend `scripts/ci/forbid_stubs.sh` with the new stub keywords.
4. Commit these changes and run the existing CI to ensure the repository remains clean.

Once those commits are green, we can proceed to Sprint 1 (infrastructure provisioning). All subsequent work will follow the sprint order above, respecting the VIBE coding rules at every step.

---
*End of sprint‑based canonical roadmap.*