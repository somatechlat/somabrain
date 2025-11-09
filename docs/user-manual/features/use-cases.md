# Use Cases

**Purpose** Map real SomaBrain features to practical scenarios you can reproduce with the published APIs.

**Audience** Teams evaluating whether SomaBrain fits their product requirements.

**Prerequisites** Execute the [Quick Start Tutorial](../quick-start-tutorial.md) so you have a working environment.

---

## 1. Persistent Assistant Memory

**Goal** Store user preferences during a conversation and recall them later.

**Workflow**

1. Call `/remember` with `task="assistant.preferences"` whenever your assistant learns something durable (e.g., preferred language).
2. On subsequent conversations, call `/recall` with a query such as `"user preferences"` and `top_k` set high enough to surface the stored entry.
3. For better prompts, use `/context/evaluate` and feed the response’s `prompt` into your language model.

**Code Points**

- Memory payload schema: `somabrain/schemas.py::MemoryPayload`
- Recall response parsing: `somabrain/schemas.py::RecallResponse`
- Context building: `somabrain/context/builder.py`

---

## 2. Retrieval and Context Building

**Goal** Provide documents and summaries to a downstream model using unified recall.

**Workflow**

1. Ingest knowledge base articles via `/remember/batch`.
2. For each user question, call `/context/evaluate` to obtain:
   - `prompt` – ready-to-send context string.
   - `memories` – structured metadata you can use for citations.
3. Invoke `/context/feedback` with the user rating to refine retrieval weights for future calls.

**Code Points**

- Planner scoring: `somabrain/context/planner.py`
- Adaptation engine: `somabrain/learning/adaptation.py`
- Feedback schema: `somabrain/api/schemas/context.py::FeedbackRequest`

---

## 3. Multi-Tenant Platform

**Goal** Serve multiple customers from one deployment while keeping data and metrics isolated.

**Workflow**

1. Issue each tenant a unique bearer token and pass `X-Tenant-ID` on every request.
2. Monitor per-tenant metrics using the `tenant_id` label in Prometheus (e.g., `somabrain_feedback_total{tenant_id="org_acme"}`).
3. Enforce daily write caps via `SOMABRAIN_QUOTA_DAILY_WRITES` or by extending `QuotaConfig`.

**Code Points**

- Tenant resolution: `somabrain/tenant.py`
- Rate limiting: `somabrain/ratelimit.py`
- Quotas: `somabrain/quotas.py`

---

## 4. Offline Consolidation

**Goal** Summarise or reorganise memories during low-traffic windows.

**Workflow**

1. Trigger `/sleep/run` with `{"nrem": true, "rem": true}` to run consolidation cycles.
2. Inspect the response for generated summaries; the same information is logged by `somabrain.consolidation`.
3. Schedule the call via a job runner or use the built-in cron worker if available in your deployment.

**Code Points**

- Consolidation routines: `somabrain/consolidation.py`
- Hippocampus integration: `somabrain/hippocampus.py`
- Sleep API handler: `somabrain/app.py::sleep_run`

---

## 5. Neuromodulator Experiments

**Goal** Adjust learning speed dynamically in response to external signals (e.g., reinforcement signals from another system).

**Workflow**

1. Fetch the current neuromodulator state: `curl /neuromodulators`.
2. Update dopamine (or other fields) using `POST /neuromodulators`.
3. Submit feedback (`/context/feedback`) and observe how the learning rate changes (`learning_rate` in `/context/adaptation/state`).

**Code Points**

- Neuromodulator storage: `somabrain/neuromodulators.py`
- Dynamic learning rate flag: `SOMABRAIN_LEARNING_RATE_DYNAMIC`
- Adaptation gains and constraints: `somabrain/learning/adaptation.py`

---

## Verifying a Use Case

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Run the relevant API requests | HTTP 200 with payload matching the schemas. |
| 2 | Inspect metrics (`/metrics`) | Tenant-labelled counters increase as expected. |
| 3 | Check Redis or logs | Confirm working memory admissions, adaptation state changes, or consolidation summaries. |

Update this page when new features are promoted from development or when code changes alter the recommended workflow.
