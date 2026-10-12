# A2A CLAIMS — file path locks

## Document Control

| Field | Value |
|---|---|
| Document Title | A2A CLAIMS — file path locks |
| Document Identifier | SOMA-BR-A2A-CLAIMS-001 |
| Version | 1.0.1 |
| Date | 2026-10-05 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2027-01-05 |
| Related | `docs/plans/2026-10-05-COORDINATION-HANDOFF.md`, `docs/plans/a2a/LEDGER.md` |
| Source of truth | This file (append-only claim table) |
| Scope | File path locks for multi-agent work on this machine |
| Audience | All coding agents (MiMoCode, Claude Code, Codex, Grok) |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-10-05 | SomaTech Engineering | A2A claims channel opened. |
| 1.0.1 | 2026-10-08 | SomaTech Engineering | Document control header added (SOMA-BR-DOCS-001). Claim rows unchanged — this file is append-only. |

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
| docs/iso/ docs/iso/DOCUMENT-REGISTER.md AGENT.md docs/plans/a2a/CLAIMS.md docs/plans/a2a/LEDGER.md docs/plans/a2a/INBOX.md docs/plans/a2a/OUTBOX.md docs/plans/2026-10-05-COORDINATION-HANDOFF.md docs/project/ scripts/check_docs.py scripts/gen_register.py | triad-iso-docs | ISO doc control + register + settings law + living-docs roles | 2026-10-08T22:30:00Z | DONE |
| somabrain/runtime_config.py somabrain/services/learner_online.py somabrain/settings/django_core.py somabrain/settings/infra.py somabrain/core/security/legacy_auth.py somabrain/memory/transport.py somabrain/memory/client/transport.py somabrain/services/integrator_hub_triplet.py somabrain/opa/client.py scripts/outbox_admin.py tests/unit/ | python-reviewer-security | LAW sweep: runtime_config no-env, token aliases collapse to SOMA_API_TOKEN, transport/OPA/learner magics -> settings/contracts | 2026-10-08T23:30:00Z | ACTIVE |
| tests/e2e/test_live_learning_e2e.py scripts/live_learning_e2e.py | brain-memory-engineer | W1 live E2E agent-interaction learning proof (:30101) | 2026-10-09T01:50:00Z | ACTIVE |
| somabrain/learning/memory_events.py scripts/live_learning_e2e.py tests/e2e/test_live_learning_e2e.py | brain-memory-engineer | APM-1 share context-route engine + live learning E2E | 2026-10-09T02:30:00Z | ACTIVE |
| docs/ README.md AGENT.md CLAUDE.md LEARNING_MATHEMATICAL_PROOF.md SOMABRAIN_MATHEMATICAL_PROOF_REPORT.md rust_core/README.md infra/k8s/README.md | doc-codemap-audit | Full docs-vs-code audit + false-claim purge + ISO sync (code = source of truth) | 2026-10-09T03:00:00Z | ACTIVE |
| somabrain/settings/managed.py somabrain/core/infrastructure_defs.py somabrain/memory/transport.py somabrain/memory/client/transport.py | MiMoCode-somabrain | P0 remember 203: managed_get async ORM swallow -> empty memory_http_endpoint in request path | 2026-10-09T00:50:00Z | ACTIVE |
| docs/OPS_MANUAL.md docs/ONBOARDING.md docs/plans/a2a/LEDGER.md docs/plans/a2a/INBOX.md | MiMoCode-somabrain | T20 ops runbook: vault root path, BrainSetting URL keys, remember proof so agents need no code hunt | 2026-10-09T00:50:00Z | ACTIVE |
| somabrain/memory/transport.py somabrain/memory/client/transport.py | brain-memory-engineer | M2 residual: brain->SFM bearer Unauthorized on remember persist (endpoint now resolves) | 2026-10-09T00:56:45Z | DONE |
| somabrain/bootstrap/singletons.py somabrain/context/factory.py somabrain/admin/core/quantum.py | MiMoCode-somabrain | ADV A1/A2: kill call-site or-defaults + fail-closed HRR (no silent Tiny) | 2026-10-09T01:15:00Z | ACTIVE |
| docs/iso/SOMA-BR-ARCH-TRUTH-001.md docs/iso/SOMA-BR-OPS-RUNBOOK-001.md docs/iso/SOMA-BR-CONFIG-API-TEST-001.md | MiMoCode-somabrain | ADV C1: delete Milvus-optional lies; dual-store required truth | 2026-10-09T01:15:00Z | ACTIVE |
| somabrain/bootstrap/singletons.py somabrain/context/factory.py somabrain/admin/core/quantum.py | MiMoCode-somabrain | ADV A1/A2 fail-closed HRR | 2026-10-09T01:15:00Z | RELEASED |
| docs/iso/SOMA-BR-ARCH-TRUTH-001.md docs/iso/SOMA-BR-ARCH-001.md docs/iso/SOMA-BR-CONFIG-API-TEST-001.md | MiMoCode-somabrain | ADV C1 dual-store truth | 2026-10-09T01:15:00Z | RELEASED |
| somafractalmemory/admin/core/services.py somafractalmemory/admin/core/implementations/milvus_vector.py tests/unit/test_embedding_contract.py | brain-memory-engineer | ADV B1/B2: kill hash_penalty call-site literals + dual-store fail-open | 2026-10-09T12:00:00Z | ACTIVE |
| somafractalmemory/infra/standalone/docker-compose.yml | MiMoCode-somabrain | FIX milvus MinIO env names + address so ANN collections load (million-txn dual-store) | 2026-10-09T01:55:00Z | ACTIVE |
| somabrain/memory/hybrid.py | MiMoCode-somabrain | WAVE A5 delete dead hybrid.py (return [] on outage, no callers) | 2026-10-09T16:20:03Z | RELEASED |
| somabrain/memory/utils.py | MiMoCode-somabrain | WAVE A6 fetch_by_coord fail-closed (no [] on outage) | 2026-10-09T16:20:03Z | RELEASED |
| somabrain/bootstrap/singletons.py | MiMoCode-somabrain | WAVE A3 kill predictor fallback (no Mahalanobis soft-fallback) | 2026-10-09T16:20:03Z | RELEASED |
| somabrain/services/milvus_ann.py | MiMoCode-somabrain | WAVE A7 milvus_ann.search raise on outage | 2026-10-09T16:20:03Z | RELEASED |
| somabrain/memory/remember_bulk.py | MiMoCode-somabrain | WAVE A12 bulk no silent partial drop | 2026-10-09T16:20:03Z | RELEASED |
| docs/iso/SOMA-BR-MASTER-REMEDIATION-001.md | MiMoCode-somabrain | Master remediation plan (Rust default, Admin UI, waves) | 2026-10-09T16:20:03Z | ACTIVE |
| somabrain/admin/core/embeddings.py somabrain/memory/milvus_client.py | MiMoCode-somabrain | WAVE A11: kill fde fake label + transformer->tiny silent fallback + milvus Exception alias | 2026-10-09T16:40:00Z | RELEASED |
| somabrain/api/memory/helpers.py somabrain/api/memory/models.py | MiMoCode-somabrain | WAVE A10: drop 'all' layer synonym + fix namespace doc leak (ADV-3 DONE) | 2026-10-09T16:45:00Z | RELEASED |
| somabrain/webui/design-system/ somabrain/infra/web/ | MiMoCode-somabrain | WAVE C design tokens (orange #FF4D00 brand) + SomaBrain Admin UI shell | 2026-10-09T17:41:52Z | ACTIVE |
| docs/iso/SOMA-BR-UIUX-001.md | MiMoCode-somabrain | WAVE C ISO UIUX screens & feature spec | 2026-10-09T17:41:52Z | ACTIVE |
| somabrain/memory/remember.py somabrain/memory/client/read.py | MiMoCode-somabrain | WAVE A8/A9/M5 operator-ordered: client outbox IntegrityError replay + no silent background + mark_sent warning | 2026-10-09T17:53:23Z | RELEASED |
| somabrain/math/contracts.py | MiMoCode-somabrain | A4 operator: kill env default in production_sparsity | 2026-10-09T18:15:48Z | RELEASED |
| somafractalmemory/admin/core/services.py | MiMoCode-somabrain | R6 operator: tenant fail-closed (no default) | 2026-10-09T18:15:48Z | RELEASED |
| somabrain/services/learner_online.py somabrain/services/learner_dlq.py somabrain/learning/memory_events.py | MiMoCode-somabrain | operator: kill tenant or-default on learning path | 2026-10-09T18:15:48Z | RELEASED |
| somabrain/settings/resolve.py somabrain/settings/infra.py somabrain/config/urls.py somabrain/api/endpoints/system_health.py somabrain/bootstrap/singletons.py somabrain/controls/memory_client.py somabrain/settings/cognitive.py somabrain/memory/client/transport.py somabrain/transport/ somabrain/management/commands/serve_brain_grpc.py | MiMoCode-somabrain | SINGLE-PATH: kill optional_url/optional_setting on core URLs; MemoryClient one mode; gRPC verdict DELETE | 2026-10-09T19:43:39Z | ACTIVE |
| docs/ README.md AGENT.md CLAUDE.md docs/iso/ docs/OPS_MANUAL.md docs/ONBOARDING.md docs/USER_GUIDE.md docs/SRS_FULL.md docs/SOMABRAIN_ARCHITECTURE.md | ClaudeCode-docs | Session-change truth sync: zero-optional-paths, DEBT-008/010 closed, fail-closed memory, tenant fail-closed, R5 sfm_auth, layer vocab, design tokens, master plan | 2026-10-09T20:30:00Z | ACTIVE |
| /Users/macbookpro201916i964gb1tb/Documents/GitHub/somafractalmemory/docs/ /Users/macbookpro201916i964gb1tb/Documents/GitHub/somafractalmemory/README.md /Users/macbookpro201916i964gb1tb/Documents/GitHub/somafractalmemory/AGENT.md | ClaudeCode-docs | SFM docs truth sync (tenant fail-closed, dual-store required) | 2026-10-09T20:30:00Z | ACTIVE |
| docs/iso/ docs/README.md scripts/check_docs.py scripts/gen_register.py | MiMoCode-somabrain | T8 ISO organize + certify + document tracking | 2026-10-09T20:17:42Z | ACTIVE |
| path/prefix | agent | task | started_at | status |
|---|---|---|---|---|
| somabrain/settings/django_core.py somabrain/api/endpoints/memory_alias.py | MiMoCode-rapid-prod | WAVE1-RAPID: DEBUG decouple from log level + delete memory_alias compat routes. NOT touching settings/resolve.py, settings/infra.py, memory/transport.py (peers ACTIVE). | 2026-10-10T15:30:00Z | ACTIVE |
| somaAgent01/admin/core/chat_orchestrator.py somaAgent01/services/common/adapters/somabrain_adapter.py somaAgent01/services/common/memory_contract.py somaAgent01/config/settings.py somabrain/somabrain/core/logging_setup.py somabrain/somabrain/core/mode.py somabrain/somabrain/core/version.py somabrain/somabrain/bootstrap/beautiful_logging.py somabrain/demo_learning_simple.py somabrain/somabrain/settings/development.py somabrain/somabrain/settings/test_lean.py somabrain/config/feature_flags.py somabrain/config/logging.yaml somabrain/config/observability/ somabrain/somabrain/infrastructure/__init__.py somabrain/somabrain/core/__init__.py | MiMoCode-rapid-w1 | RAPID WAVE1: orchestrator silent [] + forget honesty + brain_tenant fail-closed + embed docs truth + safe dead-code deletes. NOT touching decisions/, mod_clef/, tool_calling.py, policy/confidence.rego (peers ACTIVE). Note: somabrain_adapter.py also claimed ACTIVE by ClaudeCode Wave A (embeddings) — different methods, no overlap. | 2026-10-10T16:00:00Z | ACTIVE |
| infra/standalone/docker-compose.yml infra/standalone/.env | soma-prod-hardening+soma-infra-health | F-09 MinIO RAM tmpfs handoff | 2026-10-10T13:00:00Z | ACTIVE |
| path/prefix | agent | task | started_at | status |
|---|---|---|---|---|
| infra/standalone/vault.hcl infra/standalone/docker-compose.yml infra/standalone/vault_unseal.py | soma-prod-hardening | F-16 Vault audit device on named volume + enable at unseal (shared files — merge additive, do not revert peer edits) | 2026-10-10T18:00:00Z | ACTIVE |
| infra/standalone/docker-compose.yml infra/standalone/seed_vault.py infra/standalone/.env | MiMoCode | F-06+F-15 curl-in-argv seeder + idempotent Vault seed + .env secret strip | 2026-10-10T18:30:00Z | DONE |
| infra/standalone/docker-compose.yml infra/standalone/vault_unseal.py infra/standalone/init_vault.py infra/standalone/.env infra/standalone/.env.example | MiMoCode-F05 | F-05 secrets=Vault only: kill SECRETS_DIR/SOMA_T0_SECRETS_DIR file mounts, wire t0_ram tmpfs, in-memory seeder | 2026-10-10T22:00:00Z | DONE |
| soma-memory-contract/ somaAgent01/services/common/memory_contract.py somabrain/somabrain/memory/client/serialization.py somaAgent01/tests/unit/test_coord_golden_vectors.py somabrain/tests/unit/test_coord_golden_vectors.py | MiMoCode-rapid-w1 | T-2 one coord authority: shared package + both consumers + golden vectors | 2026-10-10T23:30:00Z | DONE |
| somabrain/somabrain/config/logging.yaml somabrain/somabrain/core/__init__.py | MiMoCode-rapid-w1 | dead-code: zero-caller logging.yaml DELETE + stale docstring fix | 2026-10-10T23:30:00Z | DONE |
| somaAgent01/infra/standalone/README.md somaAgent01/infra/standalone/vault.hcl somaAgent01/infra/standalone/docker-compose.yml somaAgent01/infra/standalone/docker-compose.shared-network.yml somabrain/infra/standalone/vault.hcl somabrain/docs/iso/SOMA-BR-OPS-RUNBOOK-001.md somaAgent01/docs/standards/SOMA-STD-BOOTSTRAP-001.md somafractalmemory/infra/standalone/.env | MiMoCode-rapid-w1 | TASK C: rewrite docs still saying secrets live in ./secrets/ (now Vault/keychain/T0_DIR only) | 2026-10-10T23:30:00Z | DONE |
| somabrain/settings/django_core.py somabrain/settings/infra.py somabrain/settings/cognitive.py somabrain/brain_settings/models.py | MiMoCode-triad-config | SOMA-STD-CONFIG-001: behaviour env->BrainSetting, DEBUG decouple F-02, circuit/bhdc/api_url/log_level | 2026-10-11T00:00:00Z | ACTIVE |
| somabrain/memory/remember.py somabrain/memory/client/write.py somabrain/memory/client/transport.py somabrain/memory/wm_persistence.py | MiMoCode-sfm-integration | WAVE-SFM-INT: single body builder + WM vocabulary + importance forward (D1/V1/D2) | 2026-10-11T17:07:58Z | ACTIVE |
| somabrain/memory/client/graph_ops.py somabrain/memory/client/types.py somabrain/memory/recall_ops.py somabrain/api/endpoints/health.py | MiMoCode-sfm-integration | WAVE-SFM-INT: graph degraded flags + recall degraded + health ghost keys (D6/D10/B17) | 2026-10-11T17:07:58Z | RELEASED |
| somabrain/api/endpoints/oak.py somabrain/jobs/milvus_reconciliation.py somabrain/memory/milvus_client.py somabrain/admin/core/models.py | MiMoCode-sfm-integration | WAVE-SFM-INT: Oak orphan Milvus + dead episodic_snapshots cleanup (D7/D9) | 2026-10-11T17:07:58Z | RELEASED |
| somabrain/tests/unit/test_store_fields_sfm.py somabrain/tests/unit/test_recall_degraded_flag.py somabrain/tests/unit/test_memory_type_contract.py | MiMoCode-sfm-integration | WAVE-SFM-INT: cross-repo contract + degraded tests | 2026-10-11T17:07:58Z | RELEASED |
| somabrain/settings/service_registry.py somabrain/core/ports.py somabrain/brain_settings/models.py somabrain/settings/infra.py somabrain/settings/cognitive.py somabrain/journal/local_journal.py somabrain/services/integrator_hub_triplet.py | MiMoCode-settings-law | settings law audit fixes | 2026-10-09 | RELEASED |
| docs/plans/2026-10-12-BRAIN-100PCT-DEV-REPORT.md | MiMoCode-architect | Theoretical development report: Brain 100% working + Docker/real-infra + agent contract | 2026-10-12T13:15:00Z | DONE |
| somabrain/settings/cognitive.py somabrain/runtime/modes.py | MiMoCode-somabrain | COG-ALWAYS-ON | 2026-10-12T15:40:00Z | ACTIVE |
| somabrain/memory/client/transport.py somabrain/memory/transport.py | MiMoCode-somabrain | TOKEN-UNIFY | 2026-10-12T15:40:00Z | ACTIVE |
| somafractalmemory/settings/django_core.py | MiMoCode-somabrain | TOKEN-UNIFY | 2026-10-12T15:40:00Z | ACTIVE |
| somabrain/CLAUDE.md somabrain/AGENT.md somabrain/docs/VIBE_RULES.md | MiMoCode-somabrain | COG-LAW-DOCS | 2026-10-12T15:40:00Z | ACTIVE |
| somabrain/somabrain/services/milvus_ann.py somabrain/somabrain/services/ann.py somabrain/tests/integration/test_milvus_integration.py somabrain/tests/unit/test_wave_a_fail_closed.py | MiMoCode-somabrain | B29 HARD-DELETE: remove SomaBrain direct-to-Milvus write lane (MilvusAnnIndex); SFM is sole Milvus writer | 2026-10-12T16:05:00Z | ACTIVE |
| somabrain/somabrain/bootstrap/core_singletons.py somabrain/somabrain/admin/brain/fnom.py | MiMoCode-somabrain | B29: delete create_fnom_memory Milvus/Postgres bypass; FNOM = MemoryClient only | 2026-10-12T16:30:00Z | ACTIVE |
