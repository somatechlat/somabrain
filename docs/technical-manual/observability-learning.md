# Learning Observability & OPA Shadow

This document describes the core metrics, dashboards, and alert rules for the
learning loop and integrator, including OPA gating and shadow routing.

## Metrics

Core stream + policy:
- `somabrain_integrator_tau` – Current softmax temperature (tau) applied by integrator.
- `somabrain_integrator_leader_entropy{tenant}` – Normalized entropy of domain weights per tenant (0 degenerate → 1 uniform).
- `somabrain_integrator_frames_total` / `somabrain_integrator_updates_total` – Frame publishes & belief update consumption volumes.

Shadow & routing:
- `somabrain_integrator_shadow_total` – Count of frames duplicated to shadow topic.
- `somabrain_integrator_shadow_ratio` – Observed ratio of shadowed frames (cumulative fraction, not EMA).

OPA gating:
- `somabrain_integrator_opa_latency_seconds` – Histogram of OPA decision latency.
- `somabrain_integrator_opa_allow_total` / `somabrain_integrator_opa_deny_total` – Decision counts.
- `somabrain_integrator_opa_veto_ratio` – Rolling ratio denies / (allow+deny) maintained locally for cheap alerting.

Planning KPIs:
- `somabrain_planning_latency_seconds{backend}` – Per‑backend planning latency distribution.
- `somabrain_planning_latency_p99` – Approximate rolling p99 planning latency (derived client‑side from a bounded sample buffer).

Learning regret KPIs:
- `somabrain_learning_regret{tenant_id}` – Histogram of per‑tenant regret samples (regret = 1 - confidence for current next‑event pipeline).
- `somabrain_learning_regret_ewma{tenant_id}` – Smoothed EWMA regret (α=0.15) – primary stability SLO signal.
- `soma_next_event_regret` – Raw instantaneous regret gauge from last NextEvent (legacy single‑value view).

Predictor emissions:
- `somabrain_predictor_latency_seconds` / `somabrain_predictor_latency_seconds_by{provider}` – Latency distribution.
- `somabrain_predictor_fallback_total` – Fallback / error path counts.

Additional adaptation & exploration (see metrics module for full list):
- `somabrain_learning_retrieval_*` weights (α, β, γ, τ)
- `somabrain_learning_effective_lr`, `somabrain_learning_wm_length`
- `somabrain_learning_regret_*` (as above)

## KPI Targets (Initial SLO Draft)

These provisional thresholds mirror the canonical roadmap acceptance criteria and drive Prometheus alert rules (`alerts.yml`). Adjust during canary hardening.

| KPI | Metric | Target (steady state) | Alert Trigger |
|-----|--------|-----------------------|---------------|
| Planning latency p99 | `somabrain_planning_latency_p99` | ≤ 22ms (stretch) | > 40ms for 10m (`PlanningLatencyP99High`) |
| OPA veto ratio | `somabrain_integrator_opa_veto_ratio` | ≤ 0.05 | > 0.10 for 10m (`OpaVetoRatioElevated`) |
| Regret EWMA | `somabrain_learning_regret_ewma` | ≤ 0.05 | > 0.08 for 15m (`LearningRegretEwmaHigh`) |
| Shadow sampling | `somabrain_integrator_shadow_ratio` | Matches configured ratio ±1% | (No alert yet) |
| Frame continuity | `somabrain_integrator_frames_total` | >0 rate | 0 for 5m (`CogGlobalFrameAbsent`) |

Rationale:
- Regret EWMA tight band (<0.05) indicates stable policy & predictor calibration; spikes signal drift or exploration misconfiguration.
- OPA veto ratio >10% usually indicates either policy over‑restriction or upstream quality degradation (high error / inconsistent metadata).
- Planning latency p99 protects user‑visible planning & retrieval derived tasks; 40ms soft alert leaves margin below user SLO budgets.

## Metric Collection & Derivation Notes

- `somabrain_planning_latency_p99` is computed in‑process from the rolling sample buffer (max 1000 points) to avoid PromQL quantile inaccuracies on sparse tails.
- `somabrain_learning_regret_ewma` uses α=0.15 (≈ 1/α ≈ 6–7 sample window half‑life) balancing responsiveness vs. noise. Alert window (15m) ensures sustained degradation not transient spikes.
- `somabrain_integrator_opa_veto_ratio` maintained locally so alerts do not require complex range vector math under low decision volumes.

## Dashboards & Alerts

While Grafana assets are intentionally removed from the repo, recommended panels:
1. Planning Latency: Overlay histogram (backend=bfs,rwr) + p99 gauge.
2. Regret: Histogram of `somabrain_learning_regret` + EWMA time‑series line.
3. OPA: Veto ratio & decision latency heatmap.
4. Shadow Routing: Shadow ratio vs configured flag; leader entropy distribution.

Alert rules (see `alerts.yml`) already cover: planning p99 latency, OPA veto ratio, regret EWMA, frame absence. Extend later for drift (e.g. leader entropy collapse) if needed.

## Topic Seeding

Run `scripts/seed_topics.py` to create learning and shadow topics with sensible
retention defaults, including `cog.next.events` and `cog.integrator.context.shadow`.

## Operational Runbook Pointers

- Rollback thresholds copied in `docs/operational/rollback.md` for quick flag based disable.
- During canary: tighten planning p99 trigger toward 25ms once baseline variance characterized.
- Consider adding a soft pre‑alert for regret EWMA >0.07 (info severity) after observing production variance.

## Shadow Routing

Set `SOMABRAIN_SHADOW_RATIO` (or legacy `SHADOW_RATIO`) to a value in [0,1].
A fraction of global frames are duplicated to the `cog.integrator.context.shadow`
topic for evaluation while the primary frame is still published to
`cog.global.frame`. The ratio is tracked via `somabrain_integrator_shadow_ratio`.

## OPA Gating

Environment:

- `SOMABRAIN_OPA_URL`: Base URL for OPA (e.g., `http://opa:8181`).
- `SOMABRAIN_OPA_POLICY`: Data path (e.g., `soma.policy.integrator`).
- OPA posture: Fail-closed by default; latency and deny counters are instrumented.

Integrator sends candidate leader, weights and event to OPA and increments
allow/deny counters. Deny with fail-closed drops the frame; otherwise the frame
is published with `opa=deny` in its rationale.

## Dashboards & Alerts

Grafana is not included in development by default. If your environment provides
Grafana, you can visualize Prometheus metrics using your own dashboards. Alerting
can be configured in your Prometheus stack to watch the metrics listed above.

## Topic Seeding

Run `scripts/seed_topics.py` to create learning and shadow topics with sensible
retention defaults, including `cog.next.events` and `cog.integrator.context.shadow`.
