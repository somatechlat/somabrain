# PLAN — COGNITION ALWAYS ON + Full Triad Security Token

| Field | Value |
|---|---|
| Document Identifier | SOMA-BR-PLAN-COG-SEC-001 |
| Date | 2026-10-12 |
| Status | Operator-approved direction — execute on GO |
| Owner | MiMoCode-somabrain (brain + SFM) |
| Peer | MiMoCode-somaAgent01 (agent frontend — **do not touch**) |
| Hard law | COGNITION ALWAYS ON — 100% FULL CAPACITY |

---

## 0. OPERATOR LAW (non-negotiable)

1. **COGNITION ALWAYS ON — 100% FULL CAPACITY.** SomaBrain starts with every cognitive function ACTIVE. Written into `CLAUDE.md`, `AGENT.md`, `docs/VIBE_RULES.md`, project MEMORY.
2. **Full security token design across the whole triad** (Agent ↔ Brain ↔ SFM) — coordinated via A2A.
3. No shims, no fakes, no default-OFF cognition, no half-thinking brain.
4. Never edit `somaAgent01/`.

---

## 1. REPORT — Current state vs law

### 1.1 Cognition (violates the law today)

| Flag | Current default | Required |
|---|---|---|
| `SOMABRAIN_LEARNING_LOOP_ENABLED` | False | **True** |
| `SOMABRAIN_LEARNING_RATE_DYNAMIC` | False | **True** |
| `SOMABRAIN_USE_META_BRAIN` | False | **True** |
| `SOMABRAIN_USE_PLANNER` | False | **True** |
| `ENABLE_OAK` | False | **True** |
| `SOMABRAIN_ENTROPY_CAP_ENABLED` | False | **True** |
| `SOMABRAIN_USE_MICROCIRCUITS` | False | **True** |
| `SOMABRAIN_USE_SOFT_SALIENCE` | False | **True** |
| `SOMABRAIN_USE_DRIFT_MONITOR` | False | **True** |
| `SOMABRAIN_USE_SDR_PREFILTER` | False | **True** |
| `SOMABRAIN_USE_GRAPH_AUGMENT` | False | **True** |
| `SOMABRAIN_USE_HRR_FIRST` | False | **True** |
| `SOMABRAIN_USE_EXEC_CONTROLLER` | False | **True** |
| `SOMABRAIN_MEMORY_ENABLE_WEIGHTING` | False | **True** |
| `SOMABRAIN_USE_HRR` | True | True (keep) |

**Also:** hippocampus / amygdala / prefrontal / basal ganglia / neuromodulators are **NOT on the remember/recall path**. Law requires them ON every memory cycle.

### 1.2 Memory path (P0 crash)

- `token_value` NameError at `memory/client/transport.py:171` + `memory/transport.py:361` → LTM store hop dies.
- cfg/self split → `namespace is not configured (T-5 fail-closed)`.

### 1.3 Token architecture (broken across triad)

- Brain Vault `:30200` key `somabrain_memory_http_token` vs SFM Vault `:10200` key `soma_api_token` → historic 401 class.
- Agent token authorizes `/admin/services/*` (CRITICAL).
- Supervisor password in URL (CRITICAL).
- Non-constant-time compare at `standalone_auth.py:33`.

---

## 2. PLAN — Execution waves

### Wave A — COGNITION ALWAYS ON (settings + path wiring)

| # | Work | Files | Acceptance |
|---|---|---|---|
| A1 | Flip all cognitive defaults to **True** | `somabrain/settings/cognitive.py` | Every flag above defaults True; `ModeConfig` full-potential |
| A2 | `feature_enabled` fail-closed + kill-switch only | `somabrain/runtime/modes.py` | Unknown key → False/raise; deny-list is the only disable path |
| A3 | Wire hippocampus/amygdala/PFC/BG/neuromod onto **remember + recall + promote** | `api/endpoints/memory_remember.py`, `api/endpoints/memory.py`, `memory/promotion.py` | Each cycle runs the cog stack; unit test proves call graph |
| A4 | Planner-off honesty (kill-switch case) | `api/endpoints/cognitive.py` | Disabled → `error.code=planner_disabled`, never `{"plan":[]}` |
| A5 | Cognition status block on memory responses | `api/memory/models.py`, `memory_remember.py` | `cognition:{planner,learning_loop,meta_brain,oak}.enabled` |
| A6 | Tests: full-capacity boot | `tests/unit/test_cognition_always_on.py` | Boot with defaults → all flags True; remember path invokes cog modules |

### Wave B — P0 memory hop (must be green before anything ships)

| # | Work | Files | Acceptance |
|---|---|---|---|
| B1 | Fix `token_value` NameError (delete dead check) | `memory/client/transport.py`, `memory/transport.py` | No NameError; `pytest tests/unit/memory` green |
| B2 | Fix cfg/self namespace+tenant | `memory/client/transport.py`, `memory/sfm_auth.py` | `test_pool.py` green |
| B3 | `store_from_payload` no silent False | `memory/client/write.py` | Raise or outbox |
| B4 | SFM store echoes applied fields | `somafractalmemory/api/schemas.py`, `routers/memory.py` | `importance`, `belief_*`, `vector_written` in response |

### Wave C — Full triad security token (A2A with peer)

| # | Work | Files | Acceptance |
|---|---|---|---|
| C1 | Canonical key `somabrain_memory_http_token` everywhere | SFM `settings/django_core.py` | Both sides same KV path+key |
| C2 | One generator, both Vault mounts, read-back assert | `infra/standalone/seed_vault.py` (+ SFM twin) | Same 43-char value both sides |
| C3 | Entropy floor ≥32 `[A-Za-z0-9_-]{32,}` | `memory/sfm_auth.py`, SFM `_credential` | 17-char token refused |
| C4 | Bearer only — drop `X-API-Key` | `memory/sfm_auth.py` | One auth header |
| C5 | Admin token split | `api/endpoints/admin.py`, `admin_journal.py` | Agent token → 403 on `/admin/services/*` |
| C6 | Supervisor password out of URL | `api/endpoints/admin.py` | `grep 'pwd}@'` empty |
| C7 | `hmac.compare_digest` | `api/standalone_auth.py:33` | Constant-time |
| C8 | Credential-bound tenant on SFM | `somafractalmemory/api/utils.py`, `auth.py` | Header mismatch → 403 |
| C9 | Auth-gate topology endpoints | `system_health.py`, `health.py`, `features.py` | Unauth `/health/full` → 401 |
| C10 | Peer ACK on R-14 embed strategy | A2A INBOX/OUTBOX | Documented decision |

### Wave D — Real-infra proof

| # | Work | Acceptance |
|---|---|---|
| D1 | Compose up → health green → remember 200 `persisted_to_ltm` | Live stack |
| D2 | Cognition-on proof: remember triggers hippocampus/amygdala/neuromod (log/metric) | Observed on live |
| D3 | Token ceremony: Brain→SFM 201 not 401 | Live |
| D4 | `make gate` exit 0 | One-shot |
| D5 | All unit + property + integration green | 0 failed / 0 errors |

---

## 3. A2A coordination status

| Item | Status |
|---|---|
| INBOX message → agent seat (both repos) | **SENT** 2026-10-12T15:40:00Z |
| CLAIMS (cognitive.py, modes.py, transport, SFM django_core, law docs) | **ACTIVE** |
| LEDGER row | appended |
| Peer ACK | **PENDING** |

Token design sent for ACK:
- ONE key `somabrain_memory_http_token`
- ONE generator `token_urlsafe(32)` both Vaults + read-back
- Entropy floor · Bearer-only · Admin split · Credential-bound tenant · `hmac.compare_digest` · 768 one vector space (R-14)

---

## 4. Non-goals

- No edits to `somaAgent01/`
- No shims / fakes / stubs
- No default-OFF cognitive flags left behind
- No "100%" claim until Wave D gates are green and cited in LEDGER

---

## 5. Immediate next actions (on operator GO)

1. Wave B P0 crash fix (token_value + cfg/self) — unblocks memory
2. Wave A cognition defaults + remember-path wiring
3. Wave C token unification (after peer ACK on key name)
4. Wave D live proof
