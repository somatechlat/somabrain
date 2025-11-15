# SomaAgent01 Fail‑Safe Mode – SomaBrain Unavailable (ROAMDP)

> Canonical design for running SomaAgent01 fully functional on its own
> infrastructure when SomaBrain is unavailable, without fake data or
> simulation, and with automatic sync of all required memories once
> SomaBrain is back.

---

## 1. Summary

- **Goal**: When SomaBrain is down or not ready, SomaAgent01 continues to
  operate normally on its own real infrastructure (LLM, Redis, Postgres,
  Kafka, OPA, etc.), while:
  - Clearly signalling that SomaBrain cognitive features are offline.
  - Never fabricating “no memory” results or mock behaviour.
  - Persisting all memory writes that must eventually reach SomaBrain into
    a durable agent‑side outbox so they can be replayed once SomaBrain
    recovers.
- **User experience**:
  - Users do **not** change their behaviour. They send messages and get
    replies as usual.
  - The **only** visible difference is a status/notification indicator in
    the Web UI near the existing bell icon that reflects SomaBrain
    status (up/degraded/down).

---

## 2. Phase 0 — Detection & Truthful Signalling (Agent‑Side)

### 0.1 SomaBrain Health Classification

Implement an agent‑local `HealthClassifier` that periodically queries the
real SomaBrain API:

- **Source of truth**: `GET /health` on SomaBrain.
- **Derived states**:
  - `soma_brain_status = "up"` when:
    - HTTP 200, and
    - `ok == true`, `ready == true`, and `memory_ok == true` in the
      response.
  - `soma_brain_status = "degraded"` when:
    - HTTP 200, but any readiness condition fails (e.g. `ok == false`,
      `memory_ok == false`, `kafka_ok == false`, `postgres_ok == false`,
      or `opa_ok == false`).
  - `soma_brain_status = "down"` when:
    - Connection errors, timeouts, or non‑2xx responses.

Polling:

- Interval: 3–5 seconds.
- Timeout per health request: 500–1000 ms.

Constraints:

- No mocks: the agent must use the real `/health` response.
- No long‑term caching: if SomaBrain recovers, the classifier must detect
  it quickly.

### 0.2 Agent `/status` Surface

Extend SomaAgent01’s own `/status` (or `/health`) endpoint to include a
machine‑readable view of SomaBrain status:

```json
{
  "service": "soma-agent01",
  "soma_brain": {
    "status": "up | degraded | down",
    "last_change_ts": "2025-11-14T12:34:56Z",
    "reason": "health.ok=false,memory_ok=false,kafka_ok=true,..."
  },
  "overall_status": "ok | degraded"
}
```

Rules:

- `status: "up"` only when SomaBrain reports `ok=true` and `ready=true`
  and `memory_ok=true`.
- `status: "down"` only when the agent cannot reach SomaBrain or gets
  non‑2xx responses.

### 0.3 Metrics & Logging

Add agent‑side observability:

- Label important agent metrics with `soma_brain_status="up|degraded|down"`.
- Log state transitions:
  - `SomaBrain status: up → degraded (reason=memory_ok=false)`
  - `SomaBrain status: degraded → down (reason=connect_error)`
  - `SomaBrain status: down → up (reason=health.ok=true)`

Acceptance criteria:

- `/status` returns an accurate `soma_brain_status` derived from real
  SomaBrain health.
- Metrics reflect this status via labels.
- Logs contain clear messages whenever the status changes.

---

## 3. Phase 1 — Behavioural Gating (No Blanks, No Fakes)

### 1.1 Structured Error Semantics for SomaBrain Calls

Wrap all agent calls to SomaBrain (`recall`, `save_memory`, etc.) in a
strict client:

- On success:
  - Return real results from SomaBrain.
- On failure (connect error, timeout, health indicates `down` or
  `degraded`):
  - Return a structured error object, for example:

    ```json
    {
      "kind": "soma_brain_unavailable",
      "status": "down | degraded",
      "message": "connect timeout / health.ready=false / ...",
      "request_id": "agent-side correlation id",
      "soma_health_snapshot": { "...": "..." }
    }
    ```

No conversion of failures into empty lists or fake “no memory” results.

The conversation worker and other components must:

- Recognise `kind == "soma_brain_unavailable"`.
- Treat this as “SomaBrain is unavailable”, **not** as “there are simply
  no relevant memories”.

### 1.2 Local‑Only Mode (Agent Keeps Working on Real Infra)

Define clear modes:

- `soma_brain_status == "up"`:
  - Agent uses SomaBrain for:
    - Memory recall for richer context.
    - Memory writes for long‑term storage.
  - Agent also uses its own real infrastructure (Redis, Postgres, Kafka,
    OPA, LLM gateway, etc.).

- `soma_brain_status in {"degraded","down"}`:
  - Agent continues to use **all of its own infra**:
    - LLM calls, tools, policies, Redis, Postgres, Kafka, OPA.
  - For **recall**:
    - SomaBrain recall operations either:
      - Return a `soma_brain_unavailable` error, or
      - Are skipped based on the health state (with the reason recorded),
        never replaced with “no memories found”.
  - For **writes**:
    - Writes are captured into a durable agent‑side outbox for later
      replay (see Phase 2).

From the user’s point of view:

- SomaAgent01 remains fully functional.
- Responses may lose some long‑term / cross‑session richness.
- They are not misled: the Web UI shows that SomaBrain is offline.

Acceptance criteria:

- Agent does not crash or hang when SomaBrain is down.
- Agent never silently returns “no memory” because of SomaBrain outages;
  there is always an internal `memory_unavailable` signal.

---

## 4. Phase 2 — Durable Agent‑Side Outbox for Memory Writes

### 2.1 Outbox Design

Introduce an agent‑local outbox for SomaBrain‑bound memory writes:

- **Storage**:
  - Real DB table or Kafka topic; **no in‑process or transient lists**.
- **Schema** (conceptual):
  - `id`: integer PK.
  - `tenant_id`: string.
  - `dedupe_key`: string (stable idempotency key).
  - `payload`: JSON.
  - `status`: `"pending" | "sent" | "failed"`.
  - `retries`: integer.
  - `last_error`: optional string.
  - `created_at`: timestamp.
- Constraints:
  - Unique constraint on `(tenant_id, dedupe_key)` to avoid duplicate
    writes under retry conditions.
  - Index on `(status, tenant_id, created_at)` for efficient scanning.

### 2.2 Write Path

For every memory write that *must* eventually reach SomaBrain:

1. Insert an event into the agent outbox transactionally.
2. If `soma_brain_status == "up"`:
   - Attempt the real SomaBrain `save_memory` HTTP call.
   - On success:
     - Mark the event as `status="sent"`.
   - On failure:
     - Leave `status="pending"` or set to `"failed"`, and record
       `last_error`.
3. If `soma_brain_status != "up"`:
   - Do not attempt the SomaBrain call.
   - Leave `status="pending"`.

This ensures no writes are lost and avoids fake success paths.

### 2.3 Replay Worker

Implement an agent‑side replay worker:

- Periodically scans the outbox for `pending` (and optionally `failed`)
  events.
- Only attempts replays when `soma_brain_status == "up"`.
- For each event:
  - Calls the real SomaBrain `save_memory` endpoint.
  - On success:
    - Update `status="sent"`.
  - On failure:
    - Increment `retries`, update `last_error`, and leave the event
      non‑sent for future attempts.

### 2.4 Metrics & Logging

- Metrics:
  - `somaagent_outbox_pending_total{tenant_id}`.
  - `somaagent_outbox_sent_total{tenant_id}`.
  - `somaagent_outbox_failed_total{tenant_id}`.
  - `somaagent_outbox_replayed_total{tenant_id}`.
- Logs:
  - `Enqueued memory write for agent outbox (tenant=..., dedupe=...)`.
  - `Replay succeeded for N events (tenant=...)`.
  - `Replay failed: <exception>` with reason.

Acceptance criteria:

- During a SomaBrain outage, all memory writes from SomaAgent01 are
  captured in the outbox.
- After SomaBrain recovers, these writes are eventually visible in
  SomaBrain via real HTTP API calls, with no fake data.

---

## 5. Phase 3 — Web UI Indicator Near Bell Icon

> NOTE: The frontend implementation lives in the Web UI repository. This
> phase describes the backend contract and desired UI behaviour.

### 3.1 Discover Existing UI Indicator

In the Web UI codebase:

- Locate the bell icon and any existing status/notification badge.
- Document:
  - Current meanings of colours/states.
  - Which API(s) provide status for those badges.

This ensures the SomaBrain indicator does not conflict with existing
semantic use (e.g., incident alerts, unread notifications).

### 3.2 SomaBrain Status Indicator Specification

Frontend behaviour:

- Poll SomaAgent01’s `/status` endpoint periodically (or subscribe if
  there is a push channel).
- Read:

  ```json
  { "soma_brain": { "status": "up|degraded|down" } }
  ```

- Display a distinct indicator near the existing bell icon:
  - `up`:
    - No extra badge, or a subtle green brain dot if desired.
  - `degraded`:
    - Amber dot / outline around the bell, distinct from existing alert
      statuses.
  - `down`:
    - Clear red indication (e.g., a small red triangle or brain icon) to
      signal that SomaBrain cognitive features are currently offline.

Requirements:

- The indicator must *only* reflect real values from `/status`. No
  synthetic logic in the UI.
- Tooltips or help text should explain:
  - “SomaBrain cognitive memory: available / partially available /
  unavailable. Agent is still operational on local infrastructure.”

Acceptance criteria:

- When SomaBrain is up/degraded/down (as reported by the backend),
  the UI indicator reflects the corresponding state without changing any
  user controls or flows.

---

## 6. Phase 4 — Combined Observability & Rollout

### 4.1 Dashboards

Create dashboards that combine:

- SomaBrain metrics (`memory_ok`, `ready`, `kafka_ok`, `postgres_ok`,
  `opa_ok`, etc.).
- SomaAgent01 metrics:
  - Labels with `soma_brain_status`.
  - Outbox pending/replayed/failed counters.
- Web UI status:
  - Optional logs showing `/status` polling outcomes.

### 4.2 Runbooks

Document operational flows:

- “SomaBrain down, agent up”:
  - Confirm SomaBrain `/health` and infra.
  - Observe agent outbox depth (writes buffered).
  - Make decisions on whether to continue with local‑only mode or restrict
    memory‑dependent features.

- “SomaBrain degraded”:
  - Follow SomaBrain’s own ROAMDP/runbooks for underlying issues.
  - Expect agent `soma_brain_status="degraded"` until SomaBrain’s
    `/health` returns fully ready.

### 4.3 No Mocks Policy

Reinforce:

- No mock SomaBrain inside SomaAgent01.
- No fake memories or “offline brain” substitutes.
- All behaviour is based on:
  - Real SomaBrain responses when available.
  - Real agent‑side storage and infra when SomaBrain is not available.

---

## 7. Notes

- This ROAMDP does **not** add any requirements on user interaction beyond
  the status indicator; all other behaviour is transparent to users.
- It assumes SomaBrain’s `/health` endpoint remains the canonical source
  of readiness truth.
- Implementation for SomaAgent01 lives in its own codebase; this document
  describes the cross‑service contracts and agent‑side behaviour required
  to keep the system honest, durable, and fail‑safe.

