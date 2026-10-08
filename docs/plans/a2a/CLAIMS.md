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
| somabrain/api/endpoints/memory_remember.py | ClaudeCode | WM->LTM promoter sync-ORM-from-async bug + fast-ack honesty | 2026-10-07T00:27:30Z | ACTIVE |
| clients/python somabrain/docs FIXED re-audit | MiMoCode | final sweep | 2026-10-07T11:34:26Z | ACTIVE |
| somabrain/memory/client/transport.py somabrain/settings/infra.py | ClaudeCode | brain->SFM bearer: transport reads cfg.soma_api_token and sends the wrong credential (401) | 2026-10-07T11:37:41Z | ACTIVE |
| somaAgent01/services/common/adapters/somabrain_adapter.py | ClaudeCode | Wave A: send precomputed query embedding on recall | 2026-10-07T12:12:40Z | ACTIVE |
| somaAgent01/tests/e2e/ somaAgent01/playwright.config.js | ClaudeCode | Wave B: Playwright memory-algorithms workbench | 2026-10-07T12:12:40Z | ACTIVE |
| somaAgent01/webui/ | ClaudeCode | Wave C: UI/UX honesty purge | 2026-10-07T12:12:40Z | ACTIVE |
| somabrain/memory/client/search.py somabrain/services/recall_service.py somabrain/api/memory/recall.py | MiMoCode | R-14 standby assist -- only if ClaudeCode delegates | 2026-10-07T12:20:59Z | ACTIVE |
| somabrain/memory/client/ranking.py somabrain/memory/client/search.py tests/unit/test_embed_dim_seam_768.py | MiMoCode | ADV-41 C1/C3: stop re-embed on live re-rank + behavioral proof | 2026-10-07T12:35:50Z | ACTIVE |
| somabrain/memory/client/read.py somabrain/memory/client/core.py somabrain/services/memory_service.py somabrain/api/memory/recall.py | MiMoCode | ADV-41 C1: thread embedding= through public recall/search API | 2026-10-07T13:05:00Z | ACTIVE |
| docs/iso/SOMA-BR-DEBT-001.md somabrain/api/memory/helpers.py somabrain/api/memory/models.py somabrain/api/endpoints/memory.py tests/unit/test_memory_layer_vocab.py | MiMoCode | ADV-3 C2/H3: layer vocab single helper + DEBT honesty | 2026-10-07T13:30:00Z | DONE |
| infra/standalone/docker-compose.yml somabrain/settings/infra.py | MiMoCode-somabrain | S0 live prove vault unseal + real healthchecks | 2026-10-08T14:35:00Z | ACTIVE |
| somabrain/settings/cognitive.py somabrain/memory/client/transport.py somabrain/memory/transport.py somabrain/learning/annealing.py somabrain/learning/persistence.py somabrain/learning/adaptation/engine.py somabrain/math/contracts.py | MiMoCode-somabrain | W-H1 settings/magic-number purge residual (ghost ENTROPY_CAP, HTTP placeholders, tau_max dual, NaN, call-site literals) | 2026-10-08T14:35:00Z | ACTIVE |
| somabrain/settings/cognitive.py somabrain/memory/client/transport.py somabrain/memory/transport.py somabrain/learning/annealing.py somabrain/learning/persistence.py somabrain/learning/adaptation/engine.py somabrain/math/contracts.py somabrain/memory/client/write.py somabrain/memory/client/ranking.py somabrain/memory/promotion.py somabrain/db/outbox.py somabrain/learning/prediction.py somabrain/services/integrator_leader.py tests/unit/ | brain-memory-engineer | W-H1 settings/magic-number purge (ghost ENTROPY_CAP, HTTP placeholders, tau_max dual, NaN, call-site literals) | 2026-10-08T15:00:00Z | ACTIVE |
| infra/standalone/docker-compose.yml | brain-memory-engineer | S0 live prove: durable vault unseal + real outbox healthcheck | 2026-10-08T14:35:00Z | ACTIVE |
| somabrain/api/endpoints/context.py somabrain/api/endpoints/memory_remember.py somabrain/api/endpoints/memory.py somabrain/api/endpoints/brain_settings.py somabrain/api/auth.py tests/unit/test_tenant_isolation_wh3.py | ClaudeCode | W-H3 tenant isolation (credential-tenant authority) | 2026-10-08T16:00:00Z | DONE |
| somabrain/learning/adaptation/engine.py somabrain/learning/adaptation/utils.py somabrain/math/contracts.py somabrain/context/builder.py somabrain/services/cognitive_loop_service.py tests/unit/ | MiMoCode-somabrain | W1 APM-1: memory-event learning signals into AdaptationEngine weights (alpha/beta/gamma/tau/theta) | 2026-10-08T18:30:00Z | ACTIVE |
| somabrain/admin/cognitive/collaboration.py somabrain/admin/cognitive/thalamus.py somabrain/admin/cognitive/attention.py somabrain/admin/cognitive/__init__.py somabrain/predictors/ somabrain/services/parameter_supervisor.py somabrain/core/runtime/config_runtime.py somabrain/runtime/modes.py somabrain/api/memory/recall.py | refactor-cleaner | W3 KILL dead research cortex | 2026-10-08T19:30:00Z | ACTIVE |
| docs/OPS_MANUAL.md docs/ONBOARDING.md docs/USER_GUIDE.md docs/SRS_FULL.md docs/SOMABRAIN_ARCHITECTURE.md VIOLATIONS.md | doc-updater | settings/Vault law doc sync (no file presets, secrets Vault-only) | 2026-10-08T21:00:00Z | ACTIVE |
