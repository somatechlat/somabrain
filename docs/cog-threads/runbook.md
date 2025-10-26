## Runbook – Cognitive Threads

Startup (local dual-stack):
- Primary API on 9696 via `scripts/dev_up.sh`
- Isolated branch stack on 9999 via `scripts/dev_up_9999.sh`

Feature flags:
- Integrator: `SOMABRAIN_FF_COG_INTEGRATOR=1`
- Segmentation: `SOMABRAIN_FF_COG_SEGMENTATION=1`
- Orchestrator: `SOMABRAIN_FF_COG_ORCHESTRATOR=1`
- Predictors (optional): `SOMABRAIN_FF_PREDICTOR_STATE|AGENT|ACTION=1`

OPA policy (integrator):
- `SOMABRAIN_OPA_URL=http://somabrain_opa:8181`
- `SOMABRAIN_OPA_POLICY=soma.policy.integrator`

Health and metrics:
- API /health and /metrics on each stack
- Key metrics: `somabrain_integrator_leader_entropy`, `somabrain_outbox_event_e2e_seconds`

On-call actions:
- Disable a module by unsetting its feature flag (service auto-idles)
- Fallback path: integrator absent → baseline; outbox persists episodic snapshots
