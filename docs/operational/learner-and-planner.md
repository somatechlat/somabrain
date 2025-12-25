# Learner & Planner Operational Notes

## LearnerService
- Transport: Kafka consumer on `cog.next_event`, producer on `cog.config.updates` (idempotent, acks=all).
- Validation: confidence must be numeric and in [0,1]; event_id used for idempotency; DLQ records failures.
- Metrics: `somabrain_learner_events_consumed_total`, `somabrain_learner_events_failed_total{phase}`, `somabrain_learner_events_produced_total`, `somabrain_learner_event_latency_seconds`, `somabrain_learner_lag_seconds`, `somabrain_learner_dlq_total`.
- DLQ: Kafka topic `SOMABRAIN_LEARNER_DLQ_TOPIC` if configured; otherwise file `./data/learner_dlq.jsonl` (configurable via `SOMABRAIN_LEARNER_DLQ_PATH`).
- Backpressure: retry/backoff via Kafka config; manual offset store+commit to avoid double-processing on failures.
- Ops checks: monitor lag gauge and DLQ count; ensure `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1` in integration runs.

## Planner
- Stateless DFS planner with action catalog (cost-ordered) and guaranteed non-empty plan (falls back to `analyze_goal`).
- Execution hook: `Planner.execute(plan, executor)` runs steps with early stop on failure; returns result list.
- Tests: `tests/services/test_planner_costs.py`, `tests/services/test_planner_execute.py` cover ordering and stop-on-failure.
- Integration: wire executor to your action runtime and feed outcomes back into learning (future work).
