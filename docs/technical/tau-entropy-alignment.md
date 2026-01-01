# Tau & Entropy Alignment (Strict Mode)

This note documents how temperature (tau) adaptation and entropy caps interact across the system.

## Components
- Adaptation Engine (`learning/adaptation.py`):
  - Applies tau annealing (exponential | step | linear) or legacy decay on feedback.
  - Enforces optional entropy cap on the retrieval parameter vector `(alpha, beta, gamma, tau)` when enabled.
- Context Builder (`context/builder.py`):
  - Applies diversity heuristic (duplicate ratio) to adjust tau within `[recall_tau_min, recall_tau_max]`.
  - Enforces per-tenant entropy cap loaded from `SOMABRAIN_LEARNING_TENANTS_FILE` after tau adjustment.
- Integrator Hub (`services/integrator_hub.py`):
  - Applies entropy cap to domain fusion weights (not the retrieval vector) to prevent degenerate uniform distributions.

## Intent
Keep retrieval exploration controlled (tau not collapsing too fast or exploding) while ensuring the combined retrieval parameter distribution does not exceed tenant policy entropy. The integrator entropy cap works on a separate probability space (leader domain weights) and remains orthogonal.

## Order of Operations
1. Adaptation Engine consumes feedback, updates parameters, applies tau anneal/decay, then entropy cap if enabled.
2. Context Builder builds a bundle for a request, applies diversity heuristic to tau, then enforces tenant entropy cap.
3. Integrator evaluates domain weights and applies fusion entropy cap if configured.

## Guarantees
- Entropy Never Increases During Cap Enforcement: Both adaptation engine and context builder use iterative sharpening; entropy either decreases or (worst-case) remains above cap with a final strong shrink, never increasing.
- Orthogonality: Retrieval vector entropy cap does not conflict with integrator domain entropy cap—different spaces.
- Determinism: All transformations use pure arithmetic; no random sampling during cap enforcement.

## Metrics
- `somabrain_entropy_cap_events_total` (adaptation) and `somabrain_integrator_entropy_cap_events_total` (integrator) count enforcement occurrences.
- `somabrain_integrator_regret_observed` plus `somabrain_integrator_time_to_stability_seconds` surface convergence dynamics relative to regret/entropy targets.

## Configuration Sources
- File: `config/learning.tenants.yaml` for per-tenant `entropy_cap`, optional anneal overrides.
- Env: `SOMABRAIN_TAU_ANNEAL_MODE`, `SOMABRAIN_TAU_ANNEAL_RATE`, `SOMABRAIN_TAU_MIN`, `SOMABRAIN_ENABLE_ENTROPY_CAP`, etc.

## Operational Guidance
- Set conservative tenant entropy caps first (e.g., 1.0–1.2) then tune tau anneal rates to achieve acceptable recall diversity.
- Use the drift detector’s baselines to adjust anneal rates when sustained high entropy correlates with regret spikes.
- In incident response (drift + rollback), config updates should reduce `exploration_temp` in integrator and optionally tighten retrieval entropy caps.

## Future Extensions
- Unify tau adaptation signals (dup ratio + regret delta) into a single PID-like controller.
- Persist per-tenant entropy convergence statistics for predictive adjustments.
- Add calibration-aware tau adjustments (lower tau when confidence reliability drops).
