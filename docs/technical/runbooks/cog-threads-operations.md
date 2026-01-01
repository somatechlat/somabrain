# Cognitive Threads Runbook (Predictors, Integrator, Segmentation)

This runbook covers day-two operations for the cognitive threads: the three Predictor services (state, agent, action), the Integrator Hub, and related Kafka topics and metrics.

## Components & Contracts

- Services
  - predictor-state, predictor-agent, predictor-action
    - Emit BeliefUpdate records to cog.state.updates, cog.agent.updates, cog.action.updates
    - Optional SOMA compatibility: soma.belief.{state,agent,action}
  - Integrator Hub
    - Consumes BeliefUpdate topics, publishes GlobalFrame to cog.global.frame
    - Optional SOMA context: soma.integrator.context

- Schemas (Avro preferred, JSON fallback)
  - belief_update, belief_update_soma, global_frame, integrator_context

- Key defaults
  - Predictors ON by default: SOMABRAIN_FF_PREDICTOR_STATE=1, SOMABRAIN_FF_PREDICTOR_AGENT=1, SOMABRAIN_FF_PREDICTOR_ACTION=1
  - Integrator confidence enforcement ON by default: SOMABRAIN_INTEGRATOR_ENFORCE_CONF=1
  - Confidence mapping: c = exp(-alpha * delta_error), alpha = SOMABRAIN_INTEGRATOR_ALPHA (default 2.0)

## Health & Readiness

- Predictor services
  - Set HEALTH_PORT to expose HTTP health on 0.0.0.0:$HEALTH_PORT
  - Endpoints: /healthz (OK) and /metrics (Prometheus) if shared metrics module is available

- Integrator Hub
  - Set HEALTH_PORT to expose HTTP health: /healthz and /metrics

- Basic health checklist
  - Kafka reachable: SOMABRAIN_KAFKA_URL resolves and broker responds
  - Topics exist: cog.state.updates, cog.agent.updates, cog.action.updates, cog.global.frame (and SOMA topics if enabled)
  - Health endpoints return 200 OK
  - Metrics endpoint returns Prometheus text

## Configuration (prod highlights)

- Predictors
  - Graph files (recommended): SOMABRAIN_GRAPH_FILE_STATE|AGENT|ACTION (or SOMABRAIN_GRAPH_FILE)
    - JSON formats: {"adjacency": [[...]]} or {"laplacian": [[...]]}
  - Heat method and parameters: SOMA_HEAT_METHOD=chebyshev|lanczos; SOMABRAIN_DIFFUSION_T; SOMABRAIN_CONF_ALPHA; SOMABRAIN_CHEB_K; SOMABRAIN_LANCZOS_M

- Integrator
  - Enforce confidence normalization: SOMABRAIN_INTEGRATOR_ENFORCE_CONF=1 (default)
  - Alpha (confidence mapping): SOMABRAIN_INTEGRATOR_ALPHA=2.0
  - Softmax temperature: dynamic via cog.config.updates exploration_temp
  - OPA (required): SOMABRAIN_OPA_URL, SOMABRAIN_OPA_POLICY (fail-closed enforced)

## Observability

- Predictor metrics
  - somabrain_predictor_error{domain} — MSE per update (histogram)
  - somabrain_predictor_*_emitted_total — update counters

- Integrator metrics
  - somabrain_integrator_updates_total{domain}
  - somabrain_integrator_frames_total{tenant}
  - somabrain_integrator_leader_total{leader}
  - somabrain_integrator_leader_switches_total{tenant}
  - somabrain_integrator_leader_entropy{tenant} — 0..1
  - somabrain_integrator_opa_latency_seconds
  - somabrain_integrator_errors_total{stage}
  - somabrain_integrator_tau — current temperature

- Useful PromQL examples
  - Top leaders: sum by (leader) (rate(somabrain_integrator_leader_total[5m]))
  - Leader switches (last hour): increase(somabrain_integrator_leader_switches_total[1h])
  - Entropy p95 by tenant (last 1h): quantile_over_time(0.95, somabrain_integrator_leader_entropy[1h])
  - Predictor error by domain: histogram_quantile(0.9, sum by (le, domain) (rate(somabrain_predictor_error_bucket[5m])))

## Run Procedures

- Start/Restart
  - Ensure Kafka and Redis are reachable
  - Export required envs (see configuration) and start services via orchestrator
  - Verify /healthz endpoints and view logs for topic readiness

- Smoke test (optional)
  - Use the teach→reward E2E smoke script (scripts/e2e_teach_feedback_smoke.py) to validate event flow and reward production

- Benchmark (optional, for math validation)
  - make bench-diffusion
  - Inspect artifacts under benchmarks/results/... and benchmarks/plots/...

## Troubleshooting

- No GlobalFrame messages
  - Check Integrator logs for decode/publish errors
  - Verify predictors are emitting to cog.*.updates
  - Confirm SOMABRAIN_INTEGRATOR_ENFORCE_CONF and ALPHA are set and reasonable

- Confidence seems off
  - With enforcement ON, confidence is derived from delta_error; inspect alpha and predictor delta_error magnitude
  - Compare predictor error histograms across domains to detect outliers

- High leader churn
  - Check integrator_leader_switches_total and leader_entropy; consider adjusting softmax temperature via cog.config.updates

- OPA denies all frames
  - If fail-closed is ON, frames may be dropped; confirm policy and endpoint availability; consider fail-open for diagnostics

## Change Management

- Defaults are safe for production: predictors ON, integrator enforcement ON
- When changing alpha or temperature, deploy gradually and monitor leader_entropy and leader_total
- Document changes in docs/reference/changelog.md under the current version section
