# A2A CLAIMS — file path locks

Format: `| path/prefix | agent | task | started_at | status |`
Status: ACTIVE | RELEASED | DONE
Before large edits, claim. Release when done.

| path/prefix | agent | task | started_at | status |
|---|---|---|---|---|
| somabrain/math/contracts.py | MiMoCode-W1 | W1 contracts | 2026-10-05 | DONE |
| somabrain/runtime/neuromodulators.py | MiMoCode-W2 | W2 neuromod | 2026-10-05 | DONE |
| somabrain/learning/annealing.py | MiMoCode-W3 | W3 anneal | 2026-10-05 | ACTIVE |
| rust_core/src/adaptation.rs | MiMoCode-W3 | W3 gains | 2026-10-05 | ACTIVE |
| somabrain/admin/cognitive/ | MiMoCode-W6 | W6 cognition | 2026-10-05 | ACTIVE |
| somabrain/memory/remember.py somabrain/admin/cognitive/hippocampus.py somabrain/api/endpoints/memory_remember.py somabrain/api/endpoints/admin.py somabrain/api/endpoints/cognitive.py | MiMoCode | W0 crash fixes | 2026-10-05T12:18:40Z | ACTIVE |
| somabrain/opa/client.py somabrain/controls/opa_middleware.py somabrain/api/endpoints/thread.py somabrain/api/endpoints/calibration.py | MiMoCode | W1 auth isolation | 2026-10-05T12:18:40Z | ACTIVE |
| somabrain/core/security/legacy_auth.py somabrain/api/standalone_auth.py somabrain/memory/milvus_client.py somabrain/db/outbox_replay.py somabrain/db/outbox_clean.py somabrain/db/outbox.py somabrain/schemas/memory.py somabrain/schemas/api.py somabrain/api/endpoints/memory.py somabrain/api/memory/models.py | MiMoCode | W1 auth isolation (H1-H4,M1-M2) | 2026-10-05T13:00:00Z | ACTIVE |
| somabrain/api/endpoints/memory_remember.py | MiMoCode | W1 H8 batch tenant/universe (overlap with W0 crash fixes — coordinate) | 2026-10-05T13:00:00Z | ACTIVE |
| somabrain/memory/client/ | MiMoCode | T-5 fail-closed on the live recall hot path (search.py return [] on outage) + lost audit events | 2026-10-05T12:18:40Z | ACTIVE |
| somabrain/db/ | MiMoCode | T-5 default sweep: outbox_replay/outbox_clean or-default | 2026-10-05T12:18:40Z | ACTIVE |
| somabrain/metrics/ | MiMoCode | T-5 default sweep: memory_metrics or-default | 2026-10-05T12:18:40Z | ACTIVE |
| somabrain/services/outbox_sync.py | MiMoCode | T-5 default sweep | 2026-10-05T12:18:40Z | ACTIVE |
| somabrain/workers/quota_manager.py | MiMoCode | T-5 default sweep | 2026-10-05T12:18:40Z | ACTIVE |
| somabrain/context/tenant_overrides.py | MiMoCode | T-5 default sweep | 2026-10-05T12:18:40Z | ACTIVE |
| somabrain/memory/client/ | ClaudeCode | T-5 fail-closed on live recall hot path (search.py) + lost audit events | 2026-10-05T12:19:22Z | ACTIVE |
| somabrain/db/outbox_replay.py | ClaudeCode | T-5 default sweep | 2026-10-05T12:19:22Z | ACTIVE |
| somabrain/db/outbox_clean.py | ClaudeCode | T-5 default sweep | 2026-10-05T12:19:22Z | ACTIVE |
| somabrain/metrics/memory_metrics.py | ClaudeCode | T-5 default sweep | 2026-10-05T12:19:22Z | ACTIVE |
| somabrain/services/outbox_sync.py | ClaudeCode | T-5 default sweep | 2026-10-05T12:19:22Z | ACTIVE |
| somabrain/workers/quota_manager.py | ClaudeCode | T-5 default sweep | 2026-10-05T12:19:22Z | ACTIVE |
| somabrain/context/tenant_overrides.py | ClaudeCode | T-5 default sweep | 2026-10-05T12:19:22Z | ACTIVE |
| somabrain/memory/scoring.py somabrain/memory/client/ranking.py somabrain/math/recency.py somabrain/admin/core/learning/scoring.py somabrain/services/cognitive_loop_service.py somabrain/admin/cognitive/personality.py | MiMoCode | W5c ADV-1 critical recency+NaN+personality | 2026-10-05T12:24:01Z | ACTIVE |
| somabrain/api/endpoints/memory_remember.py somabrain/db/outbox.py somabrain/tenant.py somabrain/constitution/__init__.py somabrain/api/endpoints/admin.py somabrain/api/endpoints/memory_admin.py | MiMoCode | W0b critical outbox+tenant+constitution | 2026-10-06T14:26:44Z | ACTIVE |
| tests/e2e/test_triad_integration.py tests/e2e/test_memory_roundtrip.spec.js | rapid-triad-gate | W1.3 memory round-trip gate (somaAgent01) | 2026-10-06T14:30:00Z | DONE |
