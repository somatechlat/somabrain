# Runtime Configuration

The `somabrain.runtime_config` module is the single source of truth for runtime tunables. Values are loaded from built‑in defaults and may be overridden in local development via `data/runtime_overrides.json` when running in `full-local` mode. In production modes overrides are ignored.

## Access Helpers

Use the helper functions:
- `runtime_config.get(key, default)` generic fetch
- `runtime_config.get_bool(key, default)` boolean conversion (`1/true/yes/on`)
- `runtime_config.get_float(key, default)` float conversion
- `runtime_config.get_str(key, default)` string conversion
- `runtime_config.set_overrides(dict)` (dev only) persist overrides to `data/runtime_overrides.json`

## Override File (Dev Only)
Create or modify `data/runtime_overrides.json` to adjust values during local iteration:
```json
{
  "integrator_alpha": 1.5,
  "fusion_normalization_enabled": true,
  "learner_emit_period_s": 10.0
}
```
These overrides are only applied when mode name is `full-local`.

## Key Categories

### Cognition / Integrator
- `integrator_alpha`, `integrator_alpha_min`, `integrator_alpha_max`, `integrator_target_regret`, `integrator_alpha_eta`
- `fusion_normalization_enabled`, `drift_detection_enabled`, `integrator_enforce_conf`

### Predictor Scheduling / Models
- `state_update_period`, `agent_update_period`, `action_update_period`
- `state_model_ver`, `agent_model_ver`, `action_model_ver`

### Learning / Exploration
- `learner_ema_alpha`, `learner_emit_period_s`, `learner_beta_ema_alpha`
- `learner_tau_min`, `learner_tau_max`, `learner_default_lr`, `learner_keepalive_tau`
- `tau_decay_enabled`, `tau_decay_rate`
- `tau_anneal_mode`, `tau_anneal_rate`, `tau_anneal_step_interval` (anneal supersedes decay when active)
- `entropy_cap_enabled`, `entropy_cap`
- `learning_state_persistence` (persist adaptation state to Redis)
- `learning_rate_dynamic` (neuromodulator/dopamine influenced effective LR)

### Memory
- `memory_enable_weighting`, `memory_phase_priors`, `memory_quality_exp`, `memory_fast_ack`

### Feature Flags (Centralized)
- `cog_composite` (composite cognition frame)
- `soma_compat` (compatibility mode)
- `feature_next_event` (subscribe to next events)
- `feature_config_updates` (subscribe to global frame for config context)
- `learning_state_persistence`, `learning_rate_dynamic`

### Serialization / Test Flexibility
- `learner_strict_avro` (if false, learner service will accept JSON fallback for reward/next events when Avro is unavailable — config updates remain Avro only)
- `learner_allow_json_input` (reserved for future expanded JSON input validation)

## Rationale
Centralizing tunables avoids divergent environment variables and ensures consistent behavior across services (predictors, integrator, learner, memory). Defaults are production‑like; local development can iterate quickly via overrides without editing code or compose files.

## Adding New Tunables
1. Add a sensible default to `_defaults_for_mode` in `runtime_config.py`.
2. Consume via `runtime_config.get_*` in the service/module.
3. (Optional) Document the new key here.
4. For dev experimentation, adjust `data/runtime_overrides.json`.

## Anti‑Patterns Avoided
- No ad‑hoc `os.getenv` calls for tunables in service code (except for true infrastructure endpoints or secrets).
- No multiple sources (YAML + env + code constants) — single merged dict.
- No mode‑specific logic scattered across services.

## Example Usage
```python
from somabrain import runtime_config as rc
alpha = rc.get_float("integrator_alpha", 2.0)
if rc.get_bool("fusion_normalization_enabled"):
  apply_normalization(frame)
anneal_mode = rc.get_str("tau_anneal_mode")
if anneal_mode:
  schedule_tau_anneal(rc.get_float("tau_anneal_rate", 0.05))
```

## Testing Overrides
In tests you can temporarily set overrides:
```python
from somabrain import runtime_config as rc
rc.set_overrides({
  "learner_emit_period_s": 5.0,
  "learner_tau_min": 0.2,
  "tau_anneal_mode": "exp",
  "tau_anneal_rate": 0.05,
  "learning_state_persistence": True
})
```
Ensure tests clean up if they rely on specific values.

---
This file documents the central runtime configuration system to maintain a stable, production‑aligned default while enabling fast local iteration. In `full-local` you can safely turn on all advanced learning features (entropy capping, anneal schedules, dynamic learning rate, persistence) for end‑to‑end validation.
