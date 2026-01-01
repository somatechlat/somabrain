# Outbox Backlog & Memory Circuit Playbook

## Detection

- `OutboxPendingHigh` (warning) – `memory_outbox_pending > 50` for 10m per tenant.
- `OutboxPendingCritical` (critical) – `memory_outbox_pending > 100` for 5m per tenant.
- `MemoryCircuitStuckOpen` / `MemoryCircuitCritical` – circuit breaker open ≥90%/99% over 5m/2m.
- Telemetry: `memory_outbox_replay_total`, `memory_outbox_failed_seen_total`.

## Immediate Actions

1. Confirm which tenant(s) are impacted from the alert labels (`tenant_id`).
2. Use the CLI helper to inspect queues:
   ```bash
   scripts/outbox_admin.py --token $SOMABRAIN_API_TOKEN list --tenant TENANT --status pending
   scripts/outbox_admin.py tail --tenant TENANT --status failed
   scripts/outbox_admin.py check --max-pending 100
   ```
3. If specific events are stuck, replay them:
   ```bash
   scripts/outbox_admin.py replay EVENT_ID1 EVENT_ID2 ...
   ```
4. Check downstream systems (Kafka/Memory HTTP) for errors. A circuit breaker alert usually means the memory service is failing – inspect `somabrain_app` logs and the `/health` endpoint of the external memory runtime.

## Remediation

- **Backlog caused by downstream failure:** keep the circuit breaker open (do not manually reset) until the memory service is healthy. Once healthy, replay failed events and monitor `memory_outbox_pending` trend.
- **Tenant-specific surge:** consider temporarily disabling the feature flag/canary causing the surge (`scripts/outbox_admin.py check` followed by `/admin/features`).
- **Persistent failed events:** use `/admin/outbox` or the CLI to inspect payloads for malformed data; fix upstream writers before replaying.

## Verification

- Confirm `memory_outbox_pending{tenant_id="..."}` trending to zero.
- Circuit gauges (`memory_circuit_state`) should return to 0 within a few minutes.
- `scripts/outbox_admin.py check` should exit 0.

## Escalation

- On `OutboxPendingCritical` or `MemoryCircuitCritical`, page the on-call for the external memory service and the owning tenant team.
- Attach CLI output and relevant logs to the incident ticket for postmortem.
