# Adaptation & Per-Tenant Learning Knobs

This document describes the SomaBrain adaptation engine, global learning flags, and per-tenant override configuration.

## Overview
The adaptation engine updates retrieval weights `(alpha, beta, gamma, tau)` and utility weights `(lambda_, mu, nu)` on each successful feedback event. It supports:
- Dynamic learning rate scaling (neuromodulators or signal-based)
- Tau decay (temperature annealing) per feedback
- Entropy capping to prevent over-dispersion of retrieval weights
- Per-tenant overrides via a YAML or JSON configuration file

## Global Environment Flags
| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `SOMABRAIN_ENABLE_TAU_DECAY` | bool | `0` | Enable tau decay logic. |
| `SOMABRAIN_TAU_DECAY_RATE` | float | `0.0` | Decay rate applied: `tau = max(tau * (1 - rate), 0.05)`. |
| `SOMABRAIN_ENABLE_ENTROPY_CAP` | bool | `0` | Enable entropy capping logic. |
| `SOMABRAIN_ENTROPY_CAP` | float | `0.0` | Shannon entropy upper bound over normalized `(alpha, beta, gamma, tau)`. |
| `SOMABRAIN_LEARNING_TENANTS_FILE` | path | `config/learning.tenants.yaml` | Path to per-tenant overrides file. |
| `SOMABRAIN_LEARNING_TENANTS_OVERRIDES` | JSON string | (unset) | Inline JSON alternative to file (e.g. `{"tenantA": {"tau_decay_rate": 0.03}}`). |

Global values apply only when a tenant does not define an override.

## Per-Tenant Overrides
Create a YAML (or JSON) file referenced by `SOMABRAIN_LEARNING_TENANTS_FILE`:

```yaml
sandbox:
  tau_decay_rate: 0.02
  entropy_cap: 1.25

demo:
  tau_decay_rate: 0.05
  entropy_cap: 1.0
```

Supported keys:
- `tau_decay_rate` (float)
- `entropy_cap` (float)

Missing keys fall back to global environment.

## Metrics
New metrics (Prometheus):
- `somabrain_tau_decay_events_total{tenant_id}` – count of tau decay applications.
- `somabrain_entropy_cap_events_total{tenant_id}` – count of entropy sharpen events.
- `somabrain_learning_retrieval_entropy{tenant_id}` – current retrieval entropy after each feedback.
- Existing per-weight gauges (e.g. `somabrain_learning_retrieval_tau`).

### Retrieval Entropy Calculation
Let vector `v = [alpha, beta, gamma, tau]` after update:
```
p_i = v_i / sum(v)
H = -Σ p_i * ln(p_i)
```
If `H > entropy_cap` (and `entropy_cap > 0`), all non-max components are scaled toward zero by a bounded factor to reduce dispersion.

## Neuromodulator Influence
The adaptation engine can be configured to use neuromodulator levels to dynamically adjust the learning rate. When enabled, the dopamine level from the `Neuromodulators` service is used to scale the base learning rate. This allows the system to learn faster in response to positive feedback (higher dopamine) and more slowly in response to negative feedback (lower dopamine).

This feature is controlled by the `SOMABRAIN_LEARNING_RATE_DYNAMIC` environment variable.

## Feedback Flow (Simplified)
1. Request hits `/context/feedback`.
2. Adaptation Engine computes learning rate and applies deltas. If dynamic learning rate is enabled, the dopamine level is used to scale the base learning rate.
3. Tau decay (if enabled) executes with rate from tenant override or global.
4. Entropy computed; metric recorded; capping applied if necessary.
5. State persisted (Redis if configured) and metrics updated.

## Example Usage (curl)
```bash
# Sandbox feedback (rate=0.02)
curl -sS -X POST http://localhost:9696/context/feedback \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"s1","query":"Q","prompt":"P","response_text":"R","utility":0.5,"reward":0.5,"tenant_id":"sandbox"}'

# Demo feedback (rate=0.05)
curl -sS -X POST http://localhost:9696/context/feedback \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"d1","query":"Q","prompt":"P","response_text":"R","utility":0.5,"reward":0.5,"tenant_id":"demo"}'

# Inspect adaptation state
curl -sS 'http://localhost:9696/context/adaptation/state?tenant_id=sandbox' | jq '.'
```

## Operational Guidance
- Adjust `tau_decay_rate` cautiously; too high can undercut diversity.
- Set `entropy_cap` slightly above observed steady-state entropy to allow exploration without runaway diffusion.
- Use dashboards to track: `tau`, retrieval entropy, effective learning rate, feedback count.

## Roadmap (Reference)
Refer to the **canonical roadmap** for detailed implementation plans:
[canonical_roadmap.md](../../canonical_roadmap.md)
This foundation allows adding upcoming controls:
- Entropy floor (avoid over-collapse)
- Annealed learning gains schedule
- Per-tenant sparsity / capacity targets

## Failure Modes
| Issue | Symptom | Action |
|-------|---------|--------|
| Missing overrides file | Global defaults only | Provide file or set inline JSON env |
| Excessive tau collapse | Very low tau (<0.1) | Lower decay rate or raise min floor (currently 0.05) |
| Entropy never capped | High entropy metric, zero cap events | Lower `entropy_cap` or verify enable flag |
| Metrics absent | Missing Prom scrape gauge | Verify `prometheus_client` installed & /metrics reachable |

## Summary
Per-tenant learning parameters now configurable via a simple YAML/JSON file with robust fallbacks. Metrics expose decay and entropy behaviors for monitoring and tuning.
