> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# SomaBrain Adaptive Tuning Plan

This note captures the autonomous tuning loop referenced across the roadmap
(S3–S6) so engineers have a single place to cross-check implementation details.

## Signals Collected (Evaluate/Feedback endpoints)
- Stored in Postgres tables `feedback_events` (raw outcomes) and `token_usage` (resource accounting).
- Utility triple `(p, c, ℓ)` and computed `U = λ log p − μ c − ν ℓ`
- Audit decision (`allow/deny`), violated articles, constitution checksum
- Memory stats: hit rate, retrieval latency, context length, scratchpad size
- Agent feedback (`reward`, optional human rating)

All signals are persisted to Postgres `learning_signals` and streamed to Kafka
`soma.telemetry` for observability.

## Parameter Surfaces
- Utility weights `(λ, μ, ν)` with constraints `λ, μ, ν ≥ 0`, max bounds from constitution
- Retrieval weights `(α, β, γ)`, temperature `τ`
- Working-memory TTL and slot count per tenant (bounded integers)

## Optimisation Loop
1. Every N seconds an adaptation worker (see `somabrain/learning/adaptation.py`) batches recent
   signals per tenant.
2. Compute estimated gradients using observed utility deltas. Apply projected update:
   ```
   θ_{t+1} = Π_𝒞(θ_t − η_t ẑ∇L_t)
   ```
   with adaptive learning rate `η_t` and constraint projection `Π_𝒞`.
3. For retrieval weights use Thompson sampling / UCB to choose candidate parameter sets, compare
   downstream reward/latency, and update posteriors.
4. Persist new weights to Postgres (`learning_weights`), cache in Redis, emit audit event
   `context.evaluate.update` with diffs.
5. If metrics breach constitutional bounds (utility variance, policy violations), trigger automatic
   rollback to last signed snapshot and alert operations (S6 scope).

## Observability & Runbooks
- Metrics: weight values, gradient norms, rollback count, adaptation latency.
- Alerts: weight out-of-range, rollback triggered, adaptation error rate.
- Runbooks describe rollback + replay procedure and point to weight history table.

This plan is referenced in roadmap S3 (context builder), S4 (adaptation engine), and S6 (observability).
