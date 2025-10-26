## Runbook – Cognitive Threads

Startup (local dual-stack):
- Primary API on 9696 via `scripts/dev_up.sh`
- Isolated branch stack on 9999 via `scripts/dev_up_9999.sh`

Feature flags:
- Integrator: `SOMABRAIN_FF_COG_INTEGRATOR=1`
- Segmentation: `SOMABRAIN_FF_COG_SEGMENTATION=1`
- Orchestrator: `SOMABRAIN_FF_COG_ORCHESTRATOR=1`
- Predictors (optional): `SOMABRAIN_FF_PREDICTOR_STATE|AGENT|ACTION=1`

Segmentation modes:
- Default leader-change mode over `cog.global.frame`
	- Env: `SOMABRAIN_SEGMENT_MODE=leader` (default)
	- Optional dwell gate: `SOMABRAIN_SEGMENT_MAX_DWELL_MS`
- CPD mode over Δerror streams (`cog.state|agent|action.updates`)
	- Env: `SOMABRAIN_SEGMENT_MODE=cpd`
	- Tuning: `SOMABRAIN_CPD_MIN_SAMPLES` (default 20), `SOMABRAIN_CPD_Z` (default 4.0), `SOMABRAIN_CPD_MIN_GAP_MS` (default 1000), `SOMABRAIN_CPD_MIN_STD` (default 0.02)
 - Hazard/HMM mode over Δerror streams
	- Env: `SOMABRAIN_SEGMENT_MODE=hazard`
	- Tuning: `SOMABRAIN_HAZARD_LAMBDA` (default 0.02), `SOMABRAIN_HAZARD_VOL_MULT` (default 3.0), `SOMABRAIN_HAZARD_MIN_SAMPLES` (default 20), `SOMABRAIN_CPD_MIN_GAP_MS` (default 1000)

OPA policy (integrator):
- `SOMABRAIN_OPA_URL=http://somabrain_opa:8181`
- `SOMABRAIN_OPA_POLICY=soma.policy.integrator`

Health and metrics:
- API /health and /metrics on each stack
- Key metrics: `somabrain_integrator_leader_entropy`, `somabrain_outbox_event_e2e_seconds`
 - Segmentation emits: `somabrain_segments_emitted_total{domain,evidence}` and `somabrain_segments_dwell_ms`; all microservices expose `/metrics` when `HEALTH_PORT` is set.

On-call actions:
- Disable a module by unsetting its feature flag (service auto-idles)
- Fallback path: integrator absent → baseline; outbox persists episodic snapshots
