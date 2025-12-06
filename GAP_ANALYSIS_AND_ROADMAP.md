# SomaBrain vs SomaAgent01 Gap Analysis & Roadmap

This document analyzes the gap between the current **SomaBrain** implementation and the requirements of the **SomaAgent01** system, as described in the provided architecture reports.

## 1. Status Overview

*   **SomaBrain (Current Repo)**: This is the cognitive memory runtime (Server). It provides endpoints for memory storage, recall, context evaluation, and adaptation.
*   **SomaAgent01 (Docs)**: This is a client/agent system that consumes SomaBrain services. It includes a WebUI, Celery task queue, and agent logic.

**Current State**: SomaBrain is a robust backend. We are progressively porting the Agent Execution Layer into this repository to support integrated agent workflows.

## 2. Gap Analysis & Progress

| Feature Area | SomaAgent01 Requirement | SomaBrain Current Capability | Status |
| :--- | :--- | :--- | :--- |
| **Settings** | "Settings Chaos" - Consolidate into `src/core/config/cfg`. | **Robust**: Uses `common/config/settings.py` (Pydantic). | ✅ Aligned |
| **Feedback** | Feedback loop with `task_name`, `score`, etc. | **Ready**: `POST /context/feedback` supports feedback. | ✅ Ready |
| **Tasks** | Dynamic Task Registry (Postgres table). | **Implemented**: `TaskRegistry` model, Store, and `/tasks` API. | ✅ Phase 1 Complete |
| **Execution** | Celery Task Queue, Beat, Flower. | **Implemented**: `celery_app.py`, worker, and core tasks. | ✅ Phase 2 Complete |
| **Observability**| Prometheus Metrics for tasks. | **Partial**: Metrics exist for API/Brain. | ⚠️ Pending (Phase 3) |

## 3. Roadmap

### Phase 1: Foundation for Dynamic Tasks (✅ Done)
*   **Database**: Created `task_registry` table using Alembic (PostgreSQL).
*   **API**: Implemented `/tasks` endpoints.

### Phase 2: Agent Execution Layer (✅ Done)
*   **Celery**: Initialized `somabrain.tasks.celery_app` with real Redis broker.
*   **Tasks**: Implemented `somabrain.tasks.core` with `health_check` and `register_task_dynamic`.
*   **Worker**: Created `somabrain.workers.celery_worker` entrypoint.

### Phase 3: Integration & Observability (Next)
*   **Feedback Loop**: Implement task logic that calls `POST /context/feedback` upon completion.
*   **Observability**: Expose Celery metrics (task latency, success/failure rates) to Prometheus.

## 4. Next Steps
1.  Verify Celery execution with a real integration test.
2.  Implement Phase 3 (Observability for Workers).
