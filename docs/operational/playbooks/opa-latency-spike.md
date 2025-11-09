# Playbook: OPA Latency Spike

- Symptoms: Elevated `somabrain_integrator_opa_latency_seconds` histogram; alert (to add) or degraded frame publish latency; rising veto ratio.
- Checks:
  - Network path to OPA; recent policy changes.
  - OPA server saturation metrics (external exporter).
- Actions:
  - Raise OPA timeout threshold only if minimal; otherwise fallback to permissive mode (fail-open) temporarily.
  - Cache last allow decision per tenant for short window.
- Rollback: set `SOMA_OPA_FAIL_CLOSED=0` until stability returns.
- Reference: `integrator_hub.py` `_opa_decide`.
