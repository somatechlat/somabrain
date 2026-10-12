# SOMA-BR-DEV-REPORT-2026-10-12 — Brain 100% Working: Theoretical Development Report

## Document Control

| Field | Value |
|---|---|
| Document Title | Brain 100% Working — Theoretical Development Report |
| Document Identifier | SOMA-BR-DEV-REPORT-2026-10-12 |
| Version | 1.0.0 |
| Date | 2026-10-12 |
| Status | Draft |
| Author | SomaTech Engineering (Architect seat) |
| Approver | — |
| Classification | Internal |
| Scope | `somabrain` + `somafractalmemory` only. `somaAgent01` is read-for-contract, never edited. |
| Source of truth | The code. Every row cites `file:line` observed in this working tree. |
| Related | `docs/plans/2026-10-05-SOMABRAIN-SFM-INTEGRATION-AUDIT.md`, `docs/iso/SOMA-BR-DEBT-001.md`, `docs/iso/SOMA-BR-MASTER-REMEDIATION-001.md`, `docs/iso/SOMA-BR-CONFIG-API-TEST-001.md`, `docs/plans/a2a/LEDGER.md` |

**Honesty law:** this report does NOT claim 100%. Every "done" has evidence; every "green" is a command that was run; every unproven item is marked OPEN. Where a doc says FIXED and code disagrees, code wins.

---

## §1 Last agent-session findings (evidence)

### 1.1 Which session is "last"

| Rank | Session | mtime | Topic | Relevance |
|---|---|---|---|---|
| 1 | `ses_ffe5ecfe7325effeqyyDhL4O2n` | 2026-10-12 07:33 | "Full multi-agent review + report/plan for somaAgent01 (A2A peer live)" | **LAST agent-integration session** |
| 2 | `ses_ffe5ed3f589fdffeWlJ5t23qy8` | 2026-10-11 14:15 | Enterprise security (SOMA-STD-SECURITY-001) + real SomaBrain connect + degraded chat | Prior agent-connect session |
| 3 | `ses_ffe5ed4a9bf8dffe1dhwcBn4sa` | 2026-10-11 09:20 | Enterprise Vault Agent + AppRole bootstrap LIVE | Brain/SFM infra |

Sources: `~/.local/share/mimocode/memory/sessions/` (mtime-sorted), `docs/plans/a2a/LEDGER.md:189` (last ledger row 2026-10-11T18:50:00Z).

### 1.2 What the last session DELIVERED (ses_ffe5ecfe7325effeqyyDhL4O2n)

Evidence: `~/.local/share/mimocode/memory/sessions/ses_ffe5ecfe7325effeqyyDhL4O2n/checkpoint.md` §5.

1. **architect-1 verdict (complete 2026-10-12):** architecture seams are REAL and correct; product is blocked by (a) uncommitted ~346-file working tree, (b) down local stack + peer-owned memory P0s, (c) undeployed Temporal/Clef. A full live chat run is not possible without violating the no-mocks law. (checkpoint.md:53-63)
2. **T-1 memory path proven real** — `services/common/memory_gateway.py:109` `FanoutMemoryGateway` → `services/common/adapters/somabrain_adapter.py:177`; no SFM client in the agent. (agent-side, documented only)
3. **T-2 coord single `_stable_coord`** via shared package `soma_memory_contract/__init__.py:22`. (verified in this repo)
4. **T-3 embed 768-dim precomputed** on the send side (handoff P1 closed).
5. **security-reviewer-1:** 3 CRITICAL / 5 HIGH / 4 MEDIUM / 3 LOW on the agent seat (checkpoint.md:65-73). Report-only.
6. **Plan of record (W0–W5)** presented to Operator (checkpoint.md:28-34): W0 secure+boot, W1 peer P0s, W2 memory-lane proof, W3 Temporal attach, W4 Clef live, W5 Playwright done-gate.

### 1.3 What the last session LEFT OPEN

| # | Open item | Evidence |
|---|---|---|
| O-1 | `code-reviewer-1` still running at checkpoint time — review never consolidated | checkpoint.md:51, §2 |
| O-2 | ~346-file dirty tree in somaAgent01 not committed in slices (W0) | checkpoint.md:29 |
| O-3 | Peer P0s standing: Milvus/MinIO auth, `memory_ok=true`, OPA `/memory/*`, W0.4 recall-by-coordinate | checkpoint.md:31 |
| O-4 | `turn_meta.memory_hits` None-vs-[] collapse (outage looks like "no memories") | checkpoint.md:63, `chat_orchestrator.py:1057-1066` |
| O-5 | Temporal + Clef undeployed/unproven | checkpoint.md:60 |
| O-6 | Phantom residual: `tools.py:398` requests `{base}/internal/attachments/{id}/binary` — gateway does not serve it | checkpoint.md:62 |
| O-7 | R-15 remaining: agent `somabrain_adapter.remember` must call `MemoryAck.from_brain_response` (outside this repo) | `docs/iso/SOMA-BR-DEBT-001.md:603` |
| O-8 | Peer ACK on `SOMA-STD-SECURITY-001` not yet in INBOX at 2026-10-11 | `ses_ffe5ed3f589fdffeWlJ5t23qy8/checkpoint.md:74,148` |

### 1.4 Brain-side last delivery (this repo)

Last A2A LEDGER row (`docs/plans/a2a/LEDGER.md:189`, 2026-10-11T18:50:00Z, seat `BRAIN-READ-CLEANUP`):
**WAVE-SFM-INT D6/D7/D9/D10/D11/V10/B17** — degraded-recall honesty + orphan-store cleanup. Graph ops raise `MemoryRecallUnavailable` on transport loss; `RecallHit.degraded` field; health reads `SOMABRAIN_MEMORY_DEGRADE_*`; Oak routes through SFM MemoryClient; `jobs/milvus_reconciliation.py` + fake sha256 Milvus vectors DELETED; `EpisodicSnapshot` model DELETED; Qdrant residue removed; `soma-compatibility.json` self-name fixed. Tests `test_recall_degraded_flag.py` + `test_health_settings_real.py` + `test_no_orphan_milvus_writes.py` 21/21 RED→GREEN.

**That work is UNCOMMITTED.** `git status` on `main` shows **255 dirty paths** (208 M, 16 D, 31 ??) vs `origin/main`. HEAD is still `90ff88a feat(api): BrainSetting GET/PUT` (`git log --oneline -1`). Everything from 2026-10-09T02:15Z onward that was not pushed lives only in the working tree. **This is the single largest risk to "100% working": the proven work is not durable.**

### 1.5 Live test evidence run for this report (2026-10-12)

| Command | Result |
|---|---|
| `python3 -m pytest tests/unit -q -p no:django` (full) | **25 failed, 439 passed, 30 skipped, 11 errors** |
| `python3 -m pytest tests/unit/test_math_contracts.py tests/unit/test_memory_layer_vocab.py` | 50 passed, **1 failed** (`SOMABRAIN_TAU_MIN` 0.4 ≠ `TAU_FLOOR` 0.1) |
| `python3 -m pytest tests/unit/test_tenant_isolation_wh3.py` (isolated) | 12 passed, **1 failed** (`test_evaluate_matching_tenant_is_not_403` DID NOT RAISE) |
| `python3 -m pytest tests/unit/test_w3_anneal_gains_entropy.py` | **4 failed**, 10 passed (Rust parity + `get_gains` missing + sign law 0.1025≥0.1) |
| `python3 -m pytest tests/property/test_forbidden_terms.py` | **2 failed** — forbidden terms in `transport/client.py`, `transport/net.py`, `memory/client/ranking.py` |
| `python3 -m pytest tests/unit/test_sfm_auth_and_client.py::test_transports_use_resolver` | **1 failed** — grep-proof expects `resolve_sfm_api_token` literally in transport sources |
| `python3 -m pytest tests/unit/test_health_honesty.py` | **1 failed** — `planner_loaded` still True when import should fail |

**Runtime bug found while testing:** `somabrain/memory/client/transport.py:171` and `somabrain/memory/transport.py:361` both reference `token_value` which is **never defined** in those scopes (`NameError`). The memory HTTP transport init path crashes on the auth-presence check. This is a P0 on the live memory hop.

---

## §2 Function inventory

Status legend: **IMP** implemented · **PART** partial · **MISS** missing · **BRK** broken · **UNT** untested · **CFG** config-drifted.

### 2.1 Memory path (T-1 brain → SFM)

| Function | Status | File | Gap |
|---|---|---|---|
| remember (single) | IMP (with BRK residual) | `somabrain/memory/remember.py`, `api/endpoints/memory_remember.py` | `token_value` NameError in transport init (`memory/client/transport.py:171`) breaks the hop until fixed |
| remember (batch) | IMP | `api/endpoints/memory_remember.py`, `memory/remember_bulk.py` | A12 fail-closed landed (no silent partial drop) |
| recall (vector+WM+graph+lexical) | IMP | `memory/client/search.py`, `read.py`, `ranking.py`, `api/memory/recall.py` | query_vec accepted, no re-embed (ADV-41 C1/C3) |
| forget | IMP | `api/endpoints/memory.py` | — |
| outbox T-6 durable-before-hop | IMP | `db/outbox.py`, `workers/outbox_publisher.py`, `services/outbox_sync.py` | accept still ~160–250ms (LEDGER:163), not single-digit |
| WM admit / salience / eviction | IMP | `memory/wm/core.py:210-667`, `wm/wm_eviction.py`, `wm_salience.py` | prune knobs live (`max_wm_items` etc.) |
| WM → LTM promotion | IMP | `memory/promotion.py:205-426`, `wm/wm_promotion.py` | promoter factory on worker thread (ADD-12 FIXED) |
| WM persistence to SFM | IMP | `memory/wm_persistence.py` | vocabulary now `working_memory` accepted by SFM (`somafractalmemory/api/schemas.py:33`) — D1 closed |
| LTM consolidation (NREM/REM) | PART | `memory/consolidation.py:90-182` | sleep endpoints call it (`api/endpoints/sleep.py:194`); no live proof of full sleep-cycle consolidation under load |
| Degraded recall honesty | IMP | `memory/recall_ops.py`, `client/graph_ops.py`, `types.py` | `RecallHit.degraded`, `MemoryRecallUnavailable` on outage (LEDGER:189) |
| Idempotency `mem:{coord}` | IMP | `memory/remember.py:31-97` | H3 collision raises; replay collapses |
| Single store-body builder | IMP | `memory/client/transport.py:17-54` (`build_store_payload`/`build_search_payload`) | outbox paths now route through it (V1 closed per WAVE-SFM-INT) |
| Coord authority `_stable_coord` | IMP | `soma_memory_contract/__init__.py:22` | golden vectors both sides (T-2 CLOSED) |
| Embed dim seam 768 | IMP | `somabrain/embed_dim.py:35-52`, `settings/cognitive.py:144-149` | fail-closed on missing/mismatch; **env name drift remains** (§4) |
| Graph neighbors / path | IMP | `client/graph_ops.py` | k_hop now real BFS bounded [1,5] in SFM (`api/routers/graph.py:78-108`) — B18 closed |
| Bulk / search parity | IMP | `remember_bulk.py`, SFM `api/routers/search.py` | GET/POST `memory_type` filter parity closed (D14) |

### 2.2 Math core (bhdc / quantum / recency)

| Function | Status | File | Gap |
|---|---|---|---|
| Contracts single source | IMP | `math/contracts.py` (TAU_FLOOR=0.1 at :144) | `config/env.example:131` + `.env:113` still set `SOMABRAIN_TAU_MIN=0.4` → **CFG drift, test red** |
| Recency kernel (one family) | IMP | `math/recency.py` | NaN age → floor (C4 FIXED) |
| BHDC encoder | IMP | `math/bhdc_encoder.py` | `production_sparsity` require_setting (A4 FIXED) |
| HRR / QuantumLayer | IMP | `admin/core/quantum.py:41-552`, `math/bhdc_encoder.py` | default ON (`SOMABRAIN_USE_HRR`); mix vocab `none\|hadamard`; init failure raises (no silent Tiny) |
| `PureQuantumLayer` | UNT (test-only by design) | `admin/core/quantum_pure.py:15` | explicitly test-only — must never enter live path |
| Chebyshev / Sinkhorn / Lanczos | IMP | `math/lanczos_chebyshev.py`, `sinkhorn.py`, `fd_rho.py`, `graph_heat.py` | covered by `tests/property/test_math_core_properties.py` |
| Wiener λ* / Theorem 1 | IMP | `math/contracts.py`, DEBT-011/012 FIXED | engine-level τ floor/ceiling test still **MISSING** (`CONFIG-API-TEST-001.md:488`) |
| Rust adaptation gains (sole authority) | BRK in tests | `learning/adaptation/rust_math.py`, `rust_core/src/adaptation.rs` | `test_w3_anneal_gains_entropy.py` 4 failures: `get_gains` missing on engine, sign law 0.1025≥0.1, rust/python anneal mismatch |

### 2.3 Neuromodulators

| Function | Status | File | Gap |
|---|---|---|---|
| Single store tree | IMP | `runtime/neuromodulators.py:217-415` | DEBT-001…007 FIXED (W2) |
| Clamped API | IMP | `api/endpoints/neuromod.py`, `project()`/`checked_value` | — |
| DA→LR live via singleton | IMP | `runtime/neuromodulators.py`, `learning/adaptation/engine.py:507` | — |
| ACh / 5-HT / NA targets | IMP | `runtime/neuromodulators.py:124-160` | real consumers wired |
| Homeostatic law on eval_step | IMP | `services/cognitive_loop_service.py`, ADD-03 FIXED | — |
| Per-tenant isolation | IMP | `PerTenantNeuromodulators` (`:310-333`) | shared-`RetrievalWeights` singleton leak was fixed (W1 sceptic A2/A9) |

### 2.4 Learners / adaptation

| Function | Status | File | Gap |
|---|---|---|---|
| AdaptationEngine weight updates | IMP | `learning/adaptation/engine.py:59-640` | Rust sole math authority (DEBT-008 CLOSED) |
| APM memory-event learning | IMP | `learning/memory_events.py`, `engine.py:379-411` | LEARNING_PROVEN 10/10 workbench + live :30101 e2e |
| Agent-interaction learning | IMP | `tests/unit/test_agent_interaction_learning.py`, `tests/e2e/test_live_learning_e2e.py` | quality 0.6424→0.7057 proven |
| Prune/decay knobs | IMP | `memory/wm/core.py:534-667`, BRAIN_DEFAULTS keys | WM prune infinite-loop fixed (LEDGER:157) |
| Entropy cap (sharpens α,β,γ only) | IMP | `learning/annealing.py`, DEBT-010 CLOSED | — |
| `optimize_hyperparameters` | **BRK / fake** | `engine.py:602-609` | returns `lr_opts[0]`/`tau_opts[0]` — no search. **Implement or delete.** |
| `transfer_parameters` | **BRK / fake** | `engine.py:611-613` | only sets `_task_type`. **Implement or delete.** |
| Curriculum stage | PART | `engine.py:615-623` | easy/hard LR multipliers only — not a curriculum |
| Learning persistence | PART | `learning/persistence.py` | Redis only; LEDGER D-scope says "learning state not in SFM" (ADR needed, Phase 5 of integration audit) |
| `parameter_supervisor` | PART | `services/parameter_supervisor.py:19-39` | preset apply exists; was flagged "fake" in explore-9 F2 — no live proof it drives tenant config end-to-end |
| Learner online / DLQ | PART | `services/learner_online.py`, `learner_dlq.py` | `SOMABRAIN_LEARNING_LOOP_ENABLED` now real key + `LearnerService.run()` gate; Kafka topics `cog.learner.dlq` created (LEDGER:116) |

### 2.5 Planner / cognition

| Function | Status | File | Gap |
|---|---|---|---|
| Graph planner | IMP | `planning/planner.py:25` `plan_from_graph` | — |
| RWR planner | IMP | `planning/planner_rwr.py` | — |
| Exec controller | IMP | `planning/exec_controller.py` | — |
| `/cognitive/act` focus + plan | IMP | `api/endpoints/cognitive.py:227` | `recall_hits` dead sensor wired to real `mem_client.recall` (LEDGER:109) |
| Hippocampus | PART | `admin/cognitive/hippocampus.py` | `create_hippocampus` orphan factory in `bootstrap/core_singletons.py:144` — verify caller or delete |
| Working memory buffer (cognitive) | IMP | `admin/cognitive/working_memory_buffer.py` | — |
| Basal ganglia / prefrontal / emotion / amygdala / microcircuits / personality | IMP | `admin/cognitive/{basal_ganglia,prefrontal,emotion,amygdala,microcircuits,personality}.py` | W6 real-or-delete landed; verify each has a live consumer on the `/act` path |
| ThalamusRouter / UCB1Bandit / CollaborationManager | **MISS / dead** | previously `admin/cognitive/{thalamus,attention,collaboration}.py` | explore-8: DEAD=4. CLAIMS row 76 (`refactor-cleaner` W3 KILL dead research cortex) still ACTIVE — confirm deleted or wire |
| AdaptiveCore | PART (shim) | `adaptive/core.py:112` | self-declared "thin wrapper" — decide: real orchestrator or delete |
| TinyDeterministicEmbedder | IMP (by design) | `admin/core/embeddings.py:57` | one-space with agent `embed_text` (blake2b+trigrams, golden fp match, R-14 C2) |
| LLMPredictor | PART | `admin/core/learning/prediction.py:355` | explore-8 flagged "cosine-only"; provider=mahal now default (LEDGER:162) — verify full provider set |
| Sleep states + consolidation hook | IMP | `api/endpoints/sleep.py:67-285`, `sleep/__init__.py`, `memory/consolidation.py` | `ttl_seconds` write-only (explore-9 F7) |
| Oak options (via SFM) | IMP | `api/endpoints/oak.py:32-62`, `oak/option_manager.py` | routed through SFM `memory_type=semantic` (D7 closed). **OAK option model not migrated** — live log: "Run 'makemigrations somabrain' and 'migrate' to enable OAK features" |
| ContextBuilder / evaluate / feedback / adaptation | IMP | `api/endpoints/context.py:36-200`, `context/builder.py` | tenant bound credential-only (W-H3) |

### 2.6 Admin / API / jobs / ops

| Function | Status | File | Gap |
|---|---|---|---|
| Ninja API surface (23 routers) | IMP | `api/v1.py:48-155` | includes `memory_alias` legacy mount (`api/endpoints/memory_alias.py`, 65 lines) — claim said "delete compat routes" (`CLAIMS.md:112`) but file is still registered at `api/v1.py:106-108` |
| BrainSetting GET/PUT | IMP | `api/endpoints/brain_settings.py:98-126` | bounded put + credential-tenant; 103 declared keys (`brain_settings/models.py:325`) |
| Health honesty | IMP (with red tests) | `api/endpoints/health.py:57-205`, `health/helpers.py` | `ok = memory_ok and postgres_ok and kafka_ok`; but `test_check_cognitive_load_false_when_imports_fail` red and `test_health_honesty.py:325` `planner_loaded` still True |
| OPA fail-closed middleware | IMP | `controls/opa_middleware.py`, `constitution/` | deny-by-default rego; allow-cache TTL 2s (LEDGER:163) |
| Outbox publisher worker | IMP | `workers/outbox_publisher.py` | claim lease + SKIP LOCKED (P1, migration 0006) |
| Quota manager | IMP | `workers/quota_manager.py` | `OUTBOX_TENANT_QUOTA_*` |
| gRPC transport (optional agent↔brain) | IMP | `transport/`, `management/commands/serve_brain_grpc.py` | KEEP verdict (DEBT-010 addendum) |
| `jobs/` package | **MISS** | `somabrain/jobs/` contains only `__pycache__` | `milvus_reconciliation.py` correctly deleted (D7); the package itself is now an empty shell — remove or give it a real job |
| `predictors/` package | **MISS** | `somabrain/predictors/` contains only `__pycache__` | predictors live under `admin/core/learning/prediction.py` + `services/*_predictor.py`; empty package is debris |
| Temporal long-work | UNT | agent-side + `services/` | "Long work stays on Temporal" (OUTBOX contract) but no brain-side Temporal worker proven in this tree |
| Migrations | PART | `somabrain/migrations/` | `0007` EpisodicSnapshot deleted (D9). **OAK option model needs a new migration** (live warning) |

### 2.7 SFM contract seams

| Function | Status | File | Gap |
|---|---|---|---|
| store / retrieve / delete / search | IMP | `somafractalmemory/admin/core/services.py:251-478` | tenant fail-closed `_require_tenant` (R6) |
| importance first-class column | IMP | `api/schemas.py:38`, `services.py:259-303` | B20 closed |
| belief fields (confidence/polarity) | IMP | `api/schemas.py:39-41` | B19 closed |
| `working_memory` enum | IMP | `api/schemas.py:33` | D1 closed |
| k_hop real traversal | IMP | `api/routers/graph.py:78-108`, `services.py:736-748` | B18 closed |
| degraded flag on search/graph | IMP | `api/schemas.py:88-96,185-202`, `services.py:473-478` | B17/D5 closed |
| dual-store Postgres truth + Milvus ANN | IMP | `admin/core/implementations/milvus_vector.py` | fail-closed on dim mismatch (`:111`); B21 vector-drop path needs re-verify post WAVE-SFM-INT |
| bearer auth `SOMA_API_TOKEN` | IMP | `api/auth.py:27-73`, `settings/django_core.py:174-176` | Vault-only `secret/agent/credentials[soma_api_token]`; fail-closed when unset |
| shared token with brain | IMP (ops-sensitive) | brain `memory/sfm_auth.py:57` `resolve_sfm_api_token` | **Historic 401 root cause** (token len 17 vs 64, log-line-as-token) is fixed in code (LEDGER:60,159) but is an ops footgun — see §6 |

---

## §3 Full remaining-code backlog (ordered)

Acceptance criteria (AC) are executable. No item is "done" without its AC command green.

### P0 — correctness / crash / honesty (do first)

| # | Item | File targets | Acceptance criteria |
|---|---|---|---|
| B-01 | **Fix `token_value` NameError** on memory transport init | `somabrain/memory/client/transport.py:171`, `somabrain/memory/transport.py:361` | replace with `resolve_sfm_api_token(cfg)` result (or delete the dead check); `python3 -m pytest tests/unit/test_sfm_auth_and_client.py tests/unit/memory -q` green; live `POST /memory/remember` returns 200 not 500 |
| B-02 | **Commit the 255-file dirty tree** in reviewable slices | whole repo | `git status -s` empty vs `origin/main`; each slice = one LEDGER row; no squash of RED/GREEN evidence |
| B-03 | **τ floor single truth** | `config/env.example:131`, `.env:113`, `settings/cognitive.py:225`, `brain_settings/models.py` `tau_min` | delete the 0.4 env defaults (or set 0.1); `python3 -m pytest tests/unit/test_math_contracts.py::TestTauSchedule -q` green |
| B-04 | **W3 Rust gains/anneal parity** | `learning/adaptation/engine.py` (add `get_gains` or fix tests), `rust_core/src/adaptation.rs`, `learning/adaptation/rust_math.py` | `python3 -m pytest tests/unit/test_w3_anneal_gains_entropy.py tests/unit/test_rust_gains_parity.py tests/unit/test_wave_a_fail_closed.py -q` all green; sign law `gamma` strictly decreases on positive reward |
| B-05 | **Forbidden-terms sweep** | `transport/client.py`, `transport/net.py`, `memory/client/ranking.py` | `python3 -m pytest tests/property/test_forbidden_terms.py -q` green |
| B-06 | **Tenant evaluate 403 test** | `api/endpoints/context.py:36-68`, `api/auth.py` `bind_credential_tenant` | `python3 -m pytest tests/unit/test_tenant_isolation_wh3.py -q` 13/13 green (currently 12/13) |
| B-07 | **Health `planner_loaded` / `check_cognitive_load` honesty** | `health/helpers.py`, `api/endpoints/health.py` | `python3 -m pytest tests/unit/test_health_honesty.py -q` green |
| B-08 | **Stale grep-proof in `test_transports_use_resolver`** | `tests/unit/test_sfm_auth_and_client.py:26` | either assert `build_sfm_request_headers` (the real single authority per R5) or make transports call `resolve_sfm_api_token` explicitly; one auth path only |
| B-09 | **OAK option model migration** | `somabrain/migrations/` (new), `admin/core/models.py`, `oak/option_manager.py` | `python manage.py makemigrations somabrain && python manage.py migrate` clean; OAK create→plan e2e 200; the "not yet migrated" log line gone |
| B-10 | **Delete or implement fakes** | `engine.py:602-613` `optimize_hyperparameters` / `transfer_parameters`; `adaptive/core.py:112` `AdaptiveCore` shim | AC: each is either a real algorithm with a behavioral test, or the symbol is gone and no caller remains (`rg` zero hits outside tests) |

### P1 — settings single-source + Docker/real-infra green

| # | Item | File targets | Acceptance criteria |
|---|---|---|---|
| B-11 | **Purge behavior env-reads** (law: tunables = Django + BrainSetting + agent SettingsModel only) | `api/memory/helpers.py:459-500` (`_env` for `SOMABRAIN_RECALL_DEFAULT_RERANK`/`RETRIEVERS`), `journal/local_journal.py:78` `from_env`, `cog/producer.py:12` `_bootstrap_from_env`, `workers/wm_updates_cache.py:113` (`or 8` call-site default), `learning/persistence.py:89` (`7*24*3600` literal) | `rg 'os\\.environ|env\\(' somabrain --glob '!**/__pycache__/**'` shows only topology (hosts/ports/paths) + `DJANGO_SETTINGS_MODULE`; law tests `test_law_settings_secrets_sweep.py` green |
| B-12 | **Embed-dim name collapse** | `settings/cognitive.py:144` (`env.int("EMBED_DIM")`), `.env.example:23`, `embed_dim.py`, SFM `settings/infra.py:115` `_VECTOR_DIM_ENV_ALIASES` | one declared name per concept: `SOMABRAIN_EMBED_DIM` (brain) / `MEM_EMBED_DIM` (agent) / `SOMA_VECTOR_DIM` (SFM) as documented aliases only; mismatch boots fail-closed; `test_embed_dim_seam_768.py` green both repos |
| B-13 | **Real-infra integration suite green** | `tests/integration/`, `tests/e2e/test_live_learning_e2e.py`, `scripts/live_learning_e2e.py`, `scripts/learning_workbench.py` | compose up → vault unseal → migrate → `remember` 200 `persisted_ltm` → `recall` hits → brain restart → still there → workbench LEARNING_PROVEN; all against real Postgres/Redis/Kafka/MinIO/Milvus/Vault |
| B-14 | **Outbox accept latency** (residual 160–250ms, target single-digit) | `api/endpoints/memory_remember.py`, `db/outbox.py`, middleware stack (`settings/cognitive.py` `HOT_API_PREFIXES`) | p50 accept < 20ms uncontended under `scripts/` load harness; journal append async; document the SLA in OPS-RUNBOOK |
| B-15 | **`memory_alias` disposition** | `api/endpoints/memory_alias.py`, `api/v1.py:106-108`, `soma-compatibility.json` | either keep as documented legacy alias (and close CLAIMS.md:112 as DONE-not-deleted) or delete + 404; no silent dual surface |
| B-16 | **Empty packages cleanup** | `somabrain/jobs/`, `somabrain/predictors/` | deleted or given one real job each; `import somabrain.jobs` has a documented purpose |
| B-17 | **SFM B21 vector-drop re-verify** | `somafractalmemory/admin/core/services.py:273-282` | kill Milvus → store raises or vector-outbox; never warn-and-continue without a replayable row |
| B-18 | **ParameterSupervisor live proof** | `services/parameter_supervisor.py`, `core/runtime/config_runtime.py` | behavioral test: apply_preset('plastic') changes tenant BrainSetting values that a later recall actually reads |
| B-19 | **Sleep `ttl_seconds` / `scheduled_wake`** | `api/schemas/sleep.py:32-38`, `migrations/0002_tenantsleepstate.py:28` | fields either consumed by a real wake scheduler or removed from the schema |
| B-20 | **τ bounds engine-level test** | `tests/unit/` (new), `learning/adaptation/engine.py:480` | assert engine respects `SOMABRAIN_TAU_MIN/MAX` (`CONFIG-API-TEST-001.md:488` MISSING row) |

### P2 — completeness / 100% active

| # | Item | File targets | Acceptance criteria |
|---|---|---|---|
| B-21 | Dead-cortex confirmation (ThalamusRouter / UCB1Bandit / CollaborationManager) | `admin/cognitive/` | `rg` zero live callers, or each wired into `/act` with a behavioral test |
| B-22 | `create_hippocampus` orphan factory | `bootstrap/core_singletons.py:144` | one caller on the live path or deleted |
| B-23 | Learning-state sink ADR (Redis vs SFM) | `learning/persistence.py`, `docs/iso/` | ADR filed; if SFM, add `memory_type` sink; if Redis-only, boundary documented so "ALL data" is measurable (integration-audit Phase 5) |
| B-24 | Event journal / metrics / snapshots sink ADR | `journal/local_journal.py`, `metrics/` | same as B-23 |
| B-25 | Full-potential matrix proof | `config/env.example`, `infra/standalone/.env.example`, compose `:?` pass-throughs | every `USE_*` / `ENABLE_OAK` / `REQUIRE_OPA` / `LEARNING_*` =1 boots healthy; KILL_SWITCH=0; OPA+Kafka+OAK all live on `/health` |
| B-26 | Consolidation under load (NREM/REM) | `memory/consolidation.py` | sleep-cycle e2e: admit N items → `transition_sleep_state` → NREM/REM → LTM rows exist and recall finds them |
| B-27 | Live triad gate re-run after B-01…B-09 | `tests/e2e/` | remember→recall→memory-lane STEP1-4 all green (the 2026-10-06 gate had 1 failed STEP2 SFM 401) |
| B-28 | ISO doc truth for this report's findings | `docs/iso/SOMA-BR-DEBT-001.md`, `CONFIG-API-TEST-001.md`, `MASTER-REMEDIATION-001.md` | every B-xx row appears with status; `scripts/check_docs.py` PASS |

---

## §4 Settings single-source audit findings

**Law (binding):** tunables come ONLY from Django settings + BrainSetting (DB) + agent SettingsModel. YAML/JSON file presets are NOT authority. Secrets come from Vault only.

### 4.1 What is correct

| Mechanism | File | Verdict |
|---|---|---|
| `require_setting` / `require_url` / `require_tenant` / `require_namespace` / `resolve_tunable` | `settings/resolve.py:53-105` | fail-closed; `optional_setting`/`optional_url` DELETED (LEDGER:180) |
| `managed_get` / `topology()` — BrainSetting then Django, never os.environ, never config files | `settings/managed.py:63-101` | correct; async ORM hop `_db_call` fixed (LEDGER:159) |
| `BRAIN_DEFAULTS` 103 declared keys | `brain_settings/models.py:325` | single declaration registry (R-VAL-01) |
| BrainSetting GET/PUT API | `api/endpoints/brain_settings.py:98-126` | bounded put, credential-tenant |
| Dead-key sweep | LEDGER:139 | 79 zero-reader keys deleted; 70 live remained at that time; registry now 103 with prune/learnable additions |
| Secrets Vault-only | `core/security/vault_client.py`, SFM `settings/django_core.py:174-176` | `SOMA_API_TOKEN` from `secret/agent/credentials[soma_api_token]`, never env, never default |
| Topology env allowed | `settings/service_registry.py:31` (`SOMABRAIN_MEMORY_HTTP_ENDPOINT`, `POSTGRES_DSN`, `REDIS_URL`, `KAFKA_URL`, `OPA_URL`, `KEYCLOAK_URL`) | hosts/ports/paths only — legal per law |

### 4.2 Violations and drift (must fix)

| ID | Finding | Evidence | Severity |
|---|---|---|---|
| S-1 | **`SOMABRAIN_TAU_MIN=0.4` in env files** overrides `TAU_FLOOR=0.1` | `config/env.example:131`, `.env:113` vs `math/contracts.py:144` | **CFG drift → test red** (`test_math_contracts.py:230` asserts 0.1) |
| S-2 | Behavior tunables read from `_env()` at call site | `api/memory/helpers.py:459-500` (`SOMABRAIN_RECALL_DEFAULT_RERANK`, `SOMABRAIN_RECALL_DEFAULT_RETRIEVERS`) | law violation (env is behavior authority) |
| S-3 | `JournalConfig.from_env()` | `journal/local_journal.py:78,470,508` | journal tunables from env |
| S-4 | Kafka bootstrap from env helper | `cog/producer.py:12` `_bootstrap_from_env` | should resolve via `require_url`/BrainSetting |
| S-5 | Call-site magic default `or 8` | `workers/wm_updates_cache.py:113` | even though `WM_UPDATES_TTL_SECONDS` is declared at `settings/cognitive.py:635`, the `or 8` reintroduces a call-site policy literal (AP-01) |
| S-6 | Literal `7 * 24 * 3600` TTL default | `learning/persistence.py:89` | undeclared policy literal |
| S-7 | **Embed-dim env name drift** | brain `env.int("EMBED_DIM")` → `SOMABRAIN_EMBED_DIM` (`settings/cognitive.py:144`); agent `MEM_EMBED_DIM`; SFM `SOMA_VECTOR_DIM` + alias `MEM_EMBED_DIM` (`settings/infra.py:115`); `.env.example:23` still bare `EMBED_DIM=768` | **high-risk config drift** (user-flagged): three names, one concept; seam test exists but env names differ per consumer |
| S-8 | Ghost/alias residual in docs vs code | `CONFIG-API-TEST-001.md:110` still records `SOMABRAIN_TAU_MIN` 0.4 as the live default | docs lie until S-1 fixed |
| S-9 | `scripts/fix_settings_attrs_pass2.sh:104` still rewrites `tau_min` → `SOMABRAIN_TAU_MIN` | one-shot migration script left in tree | remove or gitignore as non-runtime |
| S-10 | `test_transports_use_resolver` is a **grep-proof** (source-grep false proof class) | `tests/unit/test_sfm_auth_and_client.py:26` | same anti-pattern as the withdrawn `test_embed_dim_seam_768` source-grep proof (LEDGER:77,88) |

### 4.3 Verdict

Settings are **structurally correct** (single declaration, fail-closed resolve, Vault-only secrets) but **not clean**: 1 live floor drift (S-1), 5 residual env-as-authority sites (S-2…S-6), and 1 naming-triad risk (S-7). "Single perfect source" is **NOT proven**.

---

## §5 Docker + real-infra readiness gaps

Scope: gaps only. No invented services.

### 5.1 What exists (verified in `infra/standalone/docker-compose.yml`)

- **17+ services with healthchecks** (redis, kafka, kafka_topics_init, kafka_exporter, schema_registry, opa, prometheus, jaeger, vault_agent_{postgres,minio,app}, postgres, vault, vault_unseal, vault_unseal_watch, vault_init, db_migrate, postgres_exporter, app, cog, outbox_publisher, minio, integrator_triplet).
- **Vault AppRole** provisioned in `init_vault.py:402-490` (`setup_approle`): auth/approle enable, least-privilege policies, `role_id`/`secret_id` to isolated tmpfs `APPROLE_DIR` (`:379-389`). Idempotent skip-if-present (`:484-489`).
- **Vault Agent sidecars** for postgres/minio/app (`:350-440`) with `vault_app_secrets` / `vault_pg_secrets` / `vault_minio_secrets` volumes.
- **Migrations**: `somabrain_standalone_db_migrate` runs `python manage.py migrate --noinput` (`:648-673`) after `vault_agent_app` + `postgres` healthy.
- **Secrets model**: F-05 landed — `t0_ram` tmpfs (`:1228`), `init_vault.py` in-memory `secrets.token_urlsafe`, no `SECRETS_DIR` file mounts, MinIO `*_FILE` → `/run/t0/*`.
- **Shared network**: `docker-compose.shared-network.yml` for brain↔SFM DNS.

### 5.2 Gaps

| ID | Gap | Evidence | Impact |
|---|---|---|---|
| G-1 | **Proven work is uncommitted** (255 paths) — compose/image builds from a dirty tree | `git status -sb` = `main...origin/main` with 208 M / 16 D / 31 ?? | "Docker-deployable" cannot be certified; any reset loses the 2026-10-09→11 fixes |
| G-2 | **OAK migration missing** — live warning "OAK Option model not yet migrated. Run 'makemigrations somabrain'" | observed in test stderr 2026-10-12 | OAK features silently degraded in container |
| G-3 | **`token_value` NameError** on memory transport init | `memory/client/transport.py:171`, `memory/transport.py:361` | container memory hop can 500 on boot/first write |
| G-4 | **Two Vault instances** (brain `:30200`, SFM `:10200`) with separate seeding | `somabrain/infra/standalone/docker-compose.yml:536-537`, `somafractalmemory/infra/standalone/docker-compose.yml:64`; memory notes: credential seeding mismatch (agent token len 17 vs brain 64) caused 401 | ops footgun; needs one documented seed ceremony + read-back assert (F-06 `seed_vault.py` exists but SFM side is separate) |
| G-5 | **SFM postgres password realignment is manual** (Channel-ENV `ALTER USER`) | LEDGER:60, session `ses_ffe5ed3f589fdffeWlJ5t23qy8` §7 | re-seed breaks SCRAM auth; SEC-001 §1.9 SCRAM-over-TCP proof still open |
| G-6 | `docker-compose.override.yml` `replicas: 0` footgun | LEDGER:95 documented at `DEPLOYMENT_GUIDE.md:135` | silent zero-replica deploy |
| G-7 | Accept latency 160–250ms vs single-digit target | LEDGER:163 residual | real-infra perf gate not green |
| G-8 | Empty `jobs/`, `predictors/` packages shipped in image | `somabrain/jobs/`, `somabrain/predictors/` | image debris; confuses "all functions on" |
| G-9 | No single "real-infra gate" command documented as the DoD | `scripts/live_learning_e2e.py`, `scripts/learning_workbench.py` exist but no `make gate` that runs compose-up → migrate → triad e2e → learning proof → teardown | "Docker + real-infra tests green" is not mechanically provable in one step |
| G-10 | `config/env.example` + `.env` still carry behavior tunables (S-1…S-4) | `config/env.example:131`, `.env:113` | container boot re-introduces τ drift |

### 5.3 Verdict

Infra skeleton is **substantially real** (AppRole, Vault Agent, healthchecks, migrate job, tmpfs secrets). Docker-deployable is **NOT certified** because G-1 (dirty tree), G-2 (OAK migration), G-3 (transport NameError), and G-9 (no one-shot gate) block it.

---

## §6 Agent connection contract obligations (Brain/SFM side only)

This section is the contract the Brain + SFM owe `somaAgent01`. **No agent code is modified.** Agent obligations are listed only as "agent must" clauses the Brain already assumes.

### 6.1 Topology

| Consumer | Port / endpoint | Authority |
|---|---|---|
| Brain HTTP API | host `:30101` (`SOMABRAIN_PORT=30101`, `.env.example:43`) | compose |
| Brain Vault | host `:30200` (`docker-compose.yml:536-537`) | compose |
| SFM Vault | host `:10200` (`somafractalmemory/infra/standalone/docker-compose.yml:64`) | compose |
| SFM API | resolved via BrainSetting `memory_http_endpoint` (no ENV authority) | `settings/managed.py:26` |
| Agent API / WebUI | `:20020` / `:20080` | agent-owned |

### 6.2 Credentials (Vault-only)

| Secret | Vault path | Consumers | Obligation |
|---|---|---|---|
| `somabrain_memory_http_token` | `secret/agent/credentials[somabrain_memory_http_token]` (brain vault `:30200`) | Brain→SFM bearer **and** Agent→Brain bearer | **ONE shared 64-char value.** Brain resolves via `memory/sfm_auth.py:57` `resolve_sfm_api_token` + `build_sfm_request_headers` (`:18`, single header builder R-5). SFM validates `settings.SOMA_API_TOKEN` (`api/auth.py:27-73`) from `secret/agent/credentials[soma_api_token]` (`settings/django_core.py:174-176`). Seed ceremony MUST write the same value to both key names and read-back assert. **Never** let a log line become a token (historic root cause: a 97-char status message was stored as the credential — LEDGER:67). |
| `soma_secret_key` | `secret/agent/credentials` | SFM | seeded with merge+read-back |
| Postgres role password | Vault → Channel-ENV → `ALTER USER` | SFM/Brain DB | never a password file (F-05) |

**Brain-side hard requirements:**
1. `resolve_sfm_api_token` fail-closed on missing/short/space-containing token (`sfm_auth` rejects spaced log strings — LEDGER:159).
2. Auth headers built in exactly one place (`build_sfm_request_headers`); `X-API-Key` dual path already collapsed (R11).
3. Token never in `os.environ`, never in logs (tests `test_no_secrets_in_environ.py`, `test_vault_token_file_only.py`).

### 6.3 Vector-space contract

| Concept | Agent name | Brain name | SFM name | Value |
|---|---|---|---|---|
| Embedding dim | `MEM_EMBED_DIM` | `SOMABRAIN_EMBED_DIM` (env `EMBED_DIM` / `EMBED_DIM_SEAM`) | `SOMA_VECTOR_DIM` (alias `MEM_EMBED_DIM`) | **768** |

Obligations:
1. Brain `embed_dim.py:35-52` fail-closed: missing `SOMABRAIN_EMBED_DIM` or mismatch vs `SOMABRAIN_EMBED_DIM_SEAM` → `RuntimeError` naming the key.
2. Agent must send **precomputed** 768-dim vectors in the agent's space, bit-identical to `TinyDeterministicEmbedder` (blake2b+fold+trigrams) — R-14 C2 one-space law. Brain ranking never re-embeds (`memory/client/ranking.py`, ADV-41 C1).
3. SFM `milvus_vector.py:111` rejects writes whose dim ≠ configured dim.
4. **Drift risk (S-7):** the three env names must stay documented as aliases of one concept; a new consumer must pick the alias, not invent `EMBED_DIM_MEM` etc.

### 6.4 HTTP contracts the Agent may call (Brain side)

Canonical (from `soma-compatibility.json` and `api/v1.py`):

| Method + path | Purpose | Honesty contract |
|---|---|---|
| `POST /api/memory/remember` | store one | `ok=durable_accept`; response carries `durability`, `outbox_event_id`, `persisted_to_ltm`, `queued_for_ltm` — **never hardcode ok=true** (`MemoryAck.from_brain_response`) |
| `POST /api/memory/remember/batch` | store many | `durable_accept`; no silent partial drop (A12) |
| `POST /api/memory/recall` | query | accepts precomputed `embedding`; layer vocab `wm\|ltm\|both` only (`api/memory/helpers.py` `normalize_layer`); unknown layer → 400; on outage → `MemoryRecallUnavailable` / 503, **never bare `[]`** |
| `POST /api/memory/forget` | delete | tenant-bound |
| `POST /api/context/evaluate` | route decision | credential-tenant authority (body mismatch → 403) |
| `POST /api/context/feedback` | utility signal | drives AdaptationEngine (APM-1) |
| `GET /api/context/adaptation/state` | read weights | per-tenant |
| `POST /api/context/adaptation/reset` | reset | per-tenant |
| `POST /api/cognitive/act` | focus + plan | `recall_hits` is a real sensor (not `[]` on outage) |
| `GET/PUT /api/brain/settings` | knob map | bounded put, credential-tenant |
| `GET /health` | readiness | `ok = memory_ok && postgres_ok && kafka_ok` (fail-closed) |
| `GET /healthz`, `/simple` | liveness only | must not claim full health |

Legacy aliases `/remember`, `/recall`, `/forget` exist via `api/endpoints/memory_alias.py` (thin delegates). Agent should use `/api/memory/*`.

### 6.5 Semantics the Agent must not assume

1. **Fast-ack is on.** Accept returns `durability=durable_outbox` + `queued_for_ltm=true`; `persisted_to_ltm=true` is NOT guaranteed on the accept response. Follow up via outbox drain or recall.
2. **Tenant is credential-bound.** `X-Tenant-ID` / body `tenant_id` are assertions only; mismatch → 403.
3. **Topology is BrainSetting**, not ENV (`memory_http_endpoint` etc.). Agent SettingsModel may hold its own side; it does not override Brain.
4. **HRR default ON** (`SOMABRAIN_USE_HRR`); disable is explicit only.
5. **Stores: Postgres = truth + Milvus = ANN, both required.** No hash-only mode.
6. **Provenance:** `SOMABRAIN_REQUIRE_PROVENANCE` needs Vault `SOMABRAIN_PROVENANCE_SECRET`; currently **off** in deploy (was a hard "policy deny" brick). If enabled, agent must send `X-Provenance` HMAC or every write 503s.
7. **Long work = Temporal**, not a second queue.
8. **Degraded recall must flag.** Agent must surface `degraded=true` / `MemoryRecallUnavailable` distinctly from "no memories" (this is the O-4 `memory_hits` None-vs-[] fix on the agent seat).

### 6.6 Brain-side obligations still open against this contract

| # | Obligation | Status |
|---|---|---|
| C-1 | `token_value` NameError fix (B-01) | **OPEN — blocks the hop** |
| C-2 | τ floor truth (B-03) | **OPEN** |
| C-3 | OAK migration (B-09) | **OPEN** |
| C-4 | One shared bearer documented + seeded read-back across both vaults (G-4) | **OPEN (ops)** |
| C-5 | MemoryAck.from_brain_response stays the honest mapper | CLOSED brain-side; agent call-site is O-7 |
| C-6 | Layer vocab `wm\|ltm\|both` single helper | CLOSED (`api/memory/helpers.py`) |
| C-7 | Degraded recall flags | CLOSED (WAVE-SFM-INT D6/B17) |
| C-8 | Real-infra triad e2e green (B-27) | **OPEN** |

---

## §7 Recommended build order (phases)

### Phase 0 — Stabilize (0.5–1d)
1. B-02 commit the dirty tree in slices (docs / settings / memory / tests / infra), LEDGER rows per slice.
2. B-01 `token_value` NameError fix (smallest P0, unblocks every live probe).
3. B-03 τ floor (delete 0.4 env defaults).
4. Close stale CLAIMS rows that are actually DONE (CLAIMS.md has many ACTIVE rows from 2026-10-05 that landed).

**Gate:** `git status` clean; `pytest tests/unit/test_sfm_auth_and_client.py tests/unit/test_math_contracts.py -q` green.

### Phase 1 — Honesty green (1–2d)
5. B-04 W3 Rust parity, B-05 forbidden-terms, B-06 tenant evaluate, B-07 health honesty, B-08 grep-proof replacement, B-10 fakes delete-or-implement.

**Gate:** `pytest tests/unit tests/property -q -p no:django` = 0 failed, 0 errors (skips allowed only for documented Django-settings guards).

### Phase 2 — Settings single-source (1d)
6. B-11 purge behavior env-reads → `require_setting` / BrainSetting.
7. B-12 embed-dim name collapse (document alias table; fail-closed mismatch).
8. B-15 memory_alias disposition, B-16 empty packages.

**Gate:** `rg 'os\.environ|env\(' somabrain -g '*.py'` shows topology only; law tests green; `test_embed_dim_seam_768.py` green both repos.

### Phase 3 — Docker + real-infra (1–2d)
9. B-09 OAK migration.
10. B-13 real-infra integration suite (compose up → vault → migrate → remember/recall/restart-durable → learning workbench).
11. B-25 full-potential matrix boot (OPA+Kafka+OAK+HRR+learning all on).
12. G-9 `make gate` one-shot (compose-up → migrate → triad e2e → learning proof → teardown) + G-4 one seed ceremony doc with read-back assert.

**Gate:** `make gate` exit 0 on a clean machine; `GET /health` → `ok=true` with memory_ok/postgres/kafka true; OAK create/plan 200.

### Phase 4 — Performance + completeness (1–2d)
13. B-14 accept latency (journal async / middleware trim / multi-worker) → p50 < 20ms.
14. B-17 SFM B21 re-verify, B-18 ParameterSupervisor live proof, B-19 sleep ttl/wake, B-20 τ bounds test.
15. B-21/B-22 dead-cortex + hippocampus factory confirmation.

**Gate:** load harness numbers recorded in OPS-RUNBOOK; every §2 row moves PART/BRK/UNT → IMP or is explicitly deleted.

### Phase 5 — 100% active proof (1d)
16. B-23/B-24 sink ADRs (learning state, events, metrics).
17. B-26 consolidation-under-load e2e.
18. B-27 live triad gate re-run (all 4 steps green).
19. B-28 ISO doc truth sync + `check_docs.py` PASS.

**Gate (definition of "100% working" for this stack):**
- every function in §2 is IMP or explicitly deleted with zero callers;
- `make gate` green against real infra;
- settings law clean (no behavior env, no file presets, secrets Vault-only);
- agent contract §6 obligations C-1…C-4, C-8 closed;
- A2A LEDGER shows the proofs with commands.

### Explicit non-goals
- No edits to `somaAgent01`.
- No shims / re-export facades / stubs / TODOs as fixes (DELETE or FULL IMPLEMENT).
- No claiming 100% until the Phase 5 gate commands are green and cited.

---

## Appendix A — Evidence index

| Claim | Evidence |
|---|---|
| 255 dirty paths | `git status -s` 2026-10-12, workdir `somabrain` |
| Last ledger row | `docs/plans/a2a/LEDGER.md:189` |
| Last agent session | `~/.local/share/mimocode/memory/sessions/ses_ffe5ecfe7325effeqyyDhL4O2n/checkpoint.md` |
| Unit suite 25F/439P/30S/11E | `python3 -m pytest tests/unit -q -p no:django` 2026-10-12 |
| `token_value` NameError | `memory/client/transport.py:171`, `memory/transport.py:361` |
| τ drift 0.4 vs 0.1 | `config/env.example:131`, `.env:113`, `math/contracts.py:144`, `test_math_contracts.py:230` |
| W3 parity red | `test_w3_anneal_gains_entropy.py` 4 failed (get_gains, sign law 0.1025, rust anneal) |
| Forbidden terms | `test_forbidden_terms.py` → `transport/client.py`, `transport/net.py`, `memory/client/ranking.py` |
| BRAIN_DEFAULTS = 103 keys | `brain_settings/models.py:325` (counted 2026-10-12) |
| AppRole live | `init_vault.py:402-490` |
| Migrate job | `docker-compose.yml:648-673` |
| SFM importance/B19/B20/B18/B17 closed | `somafractalmemory/api/schemas.py:33-41,38,88-96`, `api/routers/graph.py:78-108` |
| R-14/R-15 status | `docs/iso/SOMA-BR-DEBT-001.md:602-603` |

## Appendix B — Status rollup (honest)

| Area | Verdict |
|---|---|
| Memory path (T-1) | **~90% IMP** — blocked by B-01 crash + uncommitted tree |
| Math core | **~85% IMP** — τ drift + W3 parity red |
| Neuromodulators | **IMP** (DEBT-001…007 closed) |
| Learners / adaptation | **~80% IMP** — 2 fakes + persistence sink ADR open |
| Planner / cognition | **~75% IMP** — dead-cortex confirmation + OAK migration open |
| Admin / API / ops | **~85% IMP** — health test red + empty packages |
| SFM seams | **~90% IMP** — B21 re-verify open |
| Settings single-source | **NOT clean** (S-1…S-10) |
| Docker / real-infra | **NOT certified** (G-1…G-10) |
| Agent contract | **Mostly closed** — C-1…C-4, C-8 open |

**Overall: the Brain is NOT 100%. It is substantially real, heavily de-faked, and close — but a live transport crash, a settings floor drift, uncommitted proven work, and a missing real-infra gate stand between "substantially working" and "100% working, Docker-deployable, tested against real infrastructure."**
