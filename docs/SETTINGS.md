> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# SomaBrain Settings (Deprecated Summary)

This file has been **consolidated** into the canonical configuration reference: see
`docs/CONFIGURATION.md`.

Only deltas and environment profile guidance remain here to avoid duplication.

## 1. Canonical Source
All environment variables, strict mode rules, predictor precedence, health/readiness contract,
and mode matrix now live in: `docs/CONFIGURATION.md`.

## 2. Environment Profiles (Short Form)
| Profile | Strict | Predictor Default | Recall Path Priority | Notes |
|---------|--------|-------------------|----------------------|-------|
| dev | Off | stub | in-process recent | Use only for rapid prototyping. |
| strict-dev | On | mahal | HTTP -> in-process | CI / pre-prod validation. |
| staging | On | mahal | HTTP -> in-process | Full observability + alerting. |
| prod | On | dynamic (mahal/llm) | HTTP -> in-process | No stub usage tolerated. |
| bench | On | mahal | in-process deterministic | Deterministic performance runs. |

## 3. Observability Quick Targets
| Signal | Action Threshold |
|--------|------------------|
| `UNBIND_EPS_USED` p95 | >3× baseline → investigate spectral drift |
| `RECALL_MARGIN_TOP12` | Falling trend >20% → review noise / rerank weight |
| `ready=false` (health) | Block agents consuming tasks |

## 4. Migration Notes
- Remove any internal references to `predictor_provider=stub` in staging/prod manifests.
- Ensure agents gate on `/health.ready` before dispatching workloads.
- If memory HTTP backend intentionally absent (sandbox), seed a few memories before expecting recall quality.

## 5. Future Removals
This file will be deleted once all external integrations reference `CONFIGURATION.md` directly.

---
For full details open: `docs/CONFIGURATION.md`.
