# Memory Operations Runbook

**Purpose**: Guide operators through ANN rebuilds, cutover workflows, and enabling the learning loop in backend-enforced environments.

**Audience**: Platform engineers and on-call responders.

**Prerequisites**: Access to the SomaBrain control plane (config API or Kong gateway), Prometheus dashboards, and authentication tokens with config-admin privileges.

---

## ANN Rebuild (`/memory/admin/rebuild-ann`)

- **When to run**: After large ingestion bursts, index configuration changes, or corruption alerts.
- **Endpoint**: `POST /memory/admin/rebuild-ann`
- **Payload**:
  ```json
  {
    "tenant": "acme",
    "namespace": "wm"
  }
  ```
- **Procedure**:
  1. Confirm the tenant namespace exists (`GET /memory/metrics?tenant=...&namespace=...`).
  2. Trigger rebuild via FastAPI, Kong, or `curl`.
  3. Watch Prometheus for:
     - `somabrain_ann_rebuild_total{tenant="...",namespace="..."}` increase.
     - `somabrain_ann_rebuild_seconds_bucket` to ensure durations stay below SLO (<2 s p95).
  4. Verify recall health by issuing a recall query or running `pytest tests/test_memory_api.py::test_memory_admin_rebuild_ann`.
- **Alerts**: `AnnRebuildDurationHigh`, `AnnRebuildBurst` fire if rebuilds drift.

---

## Cutover Lifecycle (`/config/cutover/*`)

- **Goal**: Promote candidate namespaces using blue/green gating.
- **Endpoints**:
  - `POST /config/cutover/open`
  - `POST /config/cutover/metrics`
  - `POST /config/cutover/approve`
  - `POST /config/cutover/execute`
  - `POST /config/cutover/cancel`
- **Happy-path sequence**:
  1. **Open plan**:
     ```json
     {
       "tenant": "acme",
       "from_namespace": "wm@v1",
       "to_namespace": "wm@v2"
     }
     ```
  2. **Shadow validation**: periodically POST metrics gathered from staging traffic.
     ```json
     {
       "tenant": "acme",
       "namespace": "wm@v2",
       "top1_accuracy": 0.93,
       "margin": 0.14,
       "latency_p95_ms": 78.0
     }
     ```
  3. Inspect plan readiness (`ready: true`) or review notes on the response.
  4. **Approve** once metrics meet targets.
  5. **Execute** to promote `wm@v2`.
- **Rollbacks**: call `/config/cutover/cancel` with a reason; re-open once mitigated.
- **Observability**:
  - Monitor `somabrain_controller_changes_total` for supervisor activity post-cutover.
  - Track `somabrain_config_version` gauge per tenant/namespace.
  - Record actions in incident tooling (plan responses include timestamps and notes).

---

## Learning Loop Feature Flag

- **Flag**: `Config.learning_loop_enabled` (or `SOMABRAIN_LEARNING_LOOP_ENABLED=1` environment override).
- **Workflow**:
  1. **Pre-check**: Ensure production metrics are stable; the supervisor should not be in an alert state.
  2. **Enable**:
     - Via config API:
       ```bash
       curl -X PATCH \
         -H "Content-Type: application/json" \
         -H "X-Actor: ops" \
         "https://gateway/config/memory?tenant=acme&namespace=wm" \
         -d '{"learning_loop_enabled": true}'
       ```
     - Or set environment variable and restart if using static config.
  3. **Validate**:
     - Run `scripts/export_learning_corpus.py --limit 10 samples.jsonl` to confirm guard no longer blocks exports.
     - Monitor `somabrain_eta`/`somabrain_sparsity` gauges for drifts.
     - Ensure `scripts/prove_enhancement.py` passes against baseline before enabling automatic ingestion.
  4. **Disable** (if needed): repeat the PATCH with `false` or unset the environment variable and restart.
- **Audit**: Document flag changes in the runbook log and export metadata (see `scripts/export_learning_corpus.py` output).

---

## Verification Checklist

- [ ] ANN rebuild counters increment after `/memory/admin/rebuild-ann`.
- [ ] Cutover plan transitions: `draft → ready → approved → executed`.
- [ ] Learning loop exports succeed and metadata captures commit/config identifiers.
- [ ] Alerts remain green (`SupervisorAdjustmentSpike`, `AnnRebuildDurationHigh`, `AnnRebuildBurst`).
