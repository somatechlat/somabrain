# SomaBrain vs SomaAgent01 Gap Analysis & Roadmap

This document analyzes the gap between the current **SomaBrain** implementation and the requirements of the **SomaAgent01** system, as described in the provided architecture reports.

## 1. Status Overview

*   **SomaBrain (Current Repo)**: This is the cognitive memory runtime (Server). It provides endpoints for memory storage, recall, context evaluation, and adaptation.
*   **SomaAgent01 (Docs)**: This is a client/agent system that consumes SomaBrain services. It includes a WebUI, Celery task queue, and agent logic.

**Current State**: SomaBrain is a robust backend, but it currently lacks the specific infrastructure to *host* the Agent's execution logic (tasks, registry) if the intention is to merge them. The Agent's code (Celery tasks, config wrappers) is missing from this repository.

## 2. Gap Analysis

| Feature Area | SomaAgent01 Requirement | SomaBrain Current Capability | Gap / Action Required |
| :--- | :--- | :--- | :--- |
| **Settings** | "Settings Chaos" - Consolidate into `src/core/config/cfg`. | **Robust**: Uses `common/config/settings.py` (Pydantic). | **Aligned**: The Brain side is already consolidated. The Agent side (if brought here) needs to use this. |
| **Feedback** | Feedback loop with `task_name`, `score`, etc. | **Ready**: `POST /context/feedback` supports feedback and adaptation. | **Gap (Agent-side)**: No code here *sends* this feedback yet. The endpoint exists and works. |
| **Tasks** | Dynamic Task Registry (Postgres table). | **Missing**: No `task_registry` table or API. | **Gap**: Need to add `task_registry` table via Alembic and an API to manage it. |
| **Execution** | Celery Task Queue, Beat, Flower. | **Missing**: No Celery infrastructure. | **Gap**: Need to add `celery_app.py`, worker entrypoints, and task definitions. |
| **Observability**| Prometheus Metrics for tasks. | **Partial**: Metrics exist for API/Brain. | **Gap**: Need to add task-level metrics if we implement the task queue here. |

## 3. Roadmap

To support the SomaAgent01 requirements within this repository, we propose the following roadmap:

### Phase 1: Foundation for Dynamic Tasks
*   **Database**: Create a `task_registry` table using Alembic (PostgreSQL). This will store task definitions, schemas, and versioning.
*   **API**: Implement `POST /tasks/register` and `GET /tasks` endpoints in SomaBrain to allow agents to register their capabilities.

### Phase 2: Agent Execution Layer (Optional but Recommended)
*   **Celery**: Initialize a Celery application within `somabrain` to handle background tasks.
*   **Worker**: Create a worker entrypoint that can execute the "Core Tasks" mentioned in the report.

### Phase 3: Integration
*   **Feedback Loop**: Implement the logic (e.g., in a worker) that executes a task and immediately calls `POST /context/feedback` to close the learning loop.
*   **Observability**: Expose Celery metrics to the existing Prometheus endpoint.

## 4. Immediate Next Steps (Proposed)
1.  **Approval**: Confirm if you want to proceed with **Phase 1 (Task Registry)** in this repo.
2.  **Implementation**:
    *   Create Alembic migration for `task_registry`.
    *   Create `somabrain/schemas/task.py` (Pydantic models).
    *   Create `somabrain/api/task_route.py` (API endpoints).
