# SOMABRAIN ↔ SFM Integration Audit, Plan & Remediation

**Date:** 2026-10-05
**Scope:** `somabrain` + `somafractalmemory` (SFM)
**Standard:** SOMA-STD-TRIAD-001 (T-1 · stack lock · degraded recall must flag)
**Method:** 3 independent specialists (architect · code-explorer · code-architect), findings cross-checked against live code with file:line evidence.

---

## 1. Verdict

**SOMABRAIN is NOT 100% integrated with SFM.** The happy-path memory write works, but several critical seams are broken, lying, or bypassing SFM entirely.

| Gate | Status |
|---|---|
| T-1 (only SomaBrain writes SFM) | **PASS** — single `MemoryClient` gateway; no SFM client outside |
| Stack lock (Milvus · Postgres · bearer · no Qdrant) | **PASS** — no Qdrant code; bearer auth live and fail-closed |
| All data into SFM | **FAIL** — WM, importance, Oak options, events, learning state, journal all miss SFM |
| No accept-and-ignore | **FAIL** — `k_hop`, `importance`, `memory_type` all silently drop |
| Degraded recall flags, never silent `[]` | **FAIL** — graph path + SFM search still silent |
| Embedding durability | **FAIL** — Milvus-down drops vectors with a warning |
| No ghost settings / stubs / fakes | **PARTIAL** — SFM clean; SomaBrain has ghost health keys, dead schema, hash dummy vectors |

---

## 2. Full Report — Damage & Broken Work Found

### CRITICAL (blocks "save ALL data in SFM")

| ID | Finding | Evidence |
|---|---|---|
| **D1** | **WM persistence is dead on arrival.** SomaBrain writes `memory_type="working_memory"` / `"working_memory_eviction"`; SFM accepts only `episodic\|semantic\|belief`. Every WM flush → HTTP 422. | `somabrain/memory/wm_persistence.py:39,124,224` vs `somafractalmemory/api/schemas.py:33` |
| **D2** | **`importance` is a dead column.** SomaBrain computes importance and puts it in payload JSON only. SFM `MemoryService.store()` has no `importance` parameter; column stays `0.0` forever. Search `order_by("-importance")` is a no-op. | `somafractalmemory/admin/core/services.py:207-246`, `models.py:49` |
| **V1** | **Two store-body builders; outbox paths strip `embedding`/`tenant_id`.** Correct seam builder exists (`client/transport.py:17-45`, `client/write.py:39-61`) but `remember_sync_persist` / `aremember_background` rebuild `{coord, payload, memory_type}` only. SFM then hash-fallbacks the embedding. | `somabrain/memory/remember.py:191-197,266-272,421-425` |

### HIGH

| ID | Finding | Evidence |
|---|---|---|
| **D3 / B18** | **`k_hop` accepted and ignored.** Router declares `k_hop: int = 1`, never forwards it. `GraphService.get_neighbors` is strictly 1-hop. Lying API. | `somafractalmemory/api/routers/graph.py:78` vs `:99-102` |
| **D4 / B21** | **Embeddings dropped when Milvus is down.** `logger.warning` and continue — precomputed embedding not persisted, row commits without vector. No SFM-side outbox. | `somafractalmemory/admin/core/services.py:273-282` |
| **D5 / B17** | **SFM search silently degrades.** Vector failure → ORM fallback with only a log line; `MemorySearchResponse` has no `degraded` field. Vector-only empty path returns `[]` with no flag. | `services.py:466-471`, `api/schemas.py:76-79` |
| **D6** | **Graph reads return silent `[]`** on transport loss / HTTP error / exception. Caller cannot distinguish "no neighbors" from "SFM down". | `somabrain/memory/client/graph_ops.py:254,304,311,338,376,386,395` |
| **D7** | **Orphan direct-Milvus write path (Oak).** `MilvusClient.upsert_option` writes vectors straight to Milvus, bypassing SFM. Plus sha256 pseudo-vectors with no provenance flag. | `somabrain/api/endpoints/oak.py:20,40`, `jobs/milvus_reconciliation.py:26`, `memory/milvus_client.py:120-131` |

### MEDIUM

| ID | Finding | Evidence |
|---|---|---|
| **D8** | SFM graph path exceptions dressed as `found=False, path=[]` | `api/routers/graph.py:152-159` |
| **D9** | Dead schema `episodic_snapshots` — model + admin + migration, zero writers/readers | `somabrain/admin/core/models.py:92-121` |
| **D10** | Ghost settings in health endpoint — reads `MEMORY_DEGRADE_*` (wrong names), hardcodes `memory_degrade_queue: True` | `somabrain/api/endpoints/health.py:150-152` |
| **D11** | Both `soma-compatibility.json` claim `self.name: "somaagent01"` — copy-paste drift | both repos `soma-compatibility.json:8-12` |
| **D12** | `remember` async fallback `except Exception: pass` then returns coord as if stored | `somabrain/memory/client/write.py:151-156` |
| **B19** | Belief is a label only — `memory_type=belief` exists, but no confidence/polarity/provenance fields | `models.py:27-33`, migration 0008 |
| **B22** | Ghost `ENTROPY_CAP` alias + `http_keepalive` knobs | `learning/annealing.py:73`, `brain_settings/models.py:379` |

### LOW

| ID | Finding | Evidence |
|---|---|---|
| **D13** | Outbox replay identity can diverge (uses `dedupe_key` as memory key) | `services/outbox_sync.py:51-61` |
| **D14** | GET `/memories/search` drops `memory_type` filter (POST has it) | `api/routers/search.py:68-76` |
| **D15** | WM restore query is free-text, not a filter | `wm_persistence.py:274-277` |
| **V5** | Ghost outbox topics (`memory.delete`, `graph.delete_link`, `wm.persist`, `wm.evict`) declared but no producers | `db/outbox.py:39-48` |
| **V10** | Qdrant residue in `generate-global-env.sh` + `.gitignore` | `scripts/generate-global-env.sh:58` |

### Not yet in SFM ("ALL data" gap)

| Artifact | Where it lives now |
|---|---|
| Working memory items | in-process only (WM persist is 422) |
| Importance | payload JSON only, not indexed column |
| Oak options | orphan Milvus |
| Events journal | local JSON files |
| Learning state | Redis |
| Metrics / snapshots | Prometheus only |
| Neuromod / predictor / BrainSetting | SomaBrain Postgres only |

---

## 3. B17–B22 / B29 Status (re-verified against code)

| ID | Symptom | Status | Evidence |
|---|---|---|---|
| B17 | degraded recall → silent `[]` | **PARTIAL** | Brain recall fixed (`recall_ops.py:27-35`); SFM search + graph client still silent |
| B18 | k_hop ignored | **OPEN** | `graph.py:78` never forwarded |
| B19 | belief unmodelled | **PARTIAL** | type exists; no confidence/polarity fields |
| B20 | importance always 0 | **OPEN** | column exists, never written |
| B21 | embedding drop on Milvus down | **OPEN** | `services.py:273-282` warn-and-continue |
| B22 | settings ghosts | **MOSTLY FIXED** | SFM purged; residual in SomaBrain health + annealing |
| B29 | undefined class | **UNDEFINED** | track D7 (Oak orphan) / D9 (dead schema) as stand-ins |

---

## 4. Implementation Plan (phased)

### Phase 0 — Stabilize workspace (0.5d)
1. Commit or stash staged deletes in `somabrain`; commit or remove SFM vault bootstrap.
2. Resolve A2A double-claims (`docs/plans/a2a/CLAIMS.md:71-72`); one seat owns `somabrain/memory/*`.
3. Log this audit to `docs/plans/a2a/LEDGER.md` (append-only).

### Phase 1 — One write contract (2–3d) — unlocks "ALL data into SFM"
1. **Single body builder.** Route `remember_sync_persist` / `aremember_background` / bulk through `_seam_store_fields` / `build_store_payload`. Delete duplicate dict literals at `remember.py:191-197,266-272,421-425`.
2. **Add `importance` + belief fields to `MemoryStoreRequest`** → `store_memory` → `MemoryService.store`. Write into `update_or_create` defaults.
3. **Unify `kind` → `memory_type`** at the seam (one mapping helper); reject unknown kinds fail-closed.

### Phase 2 — Contract honesty (2d)
4. **Honor `k_hop`** in `GraphService.get_neighbors` (BFS / recursive CTE, bounded) — or reject `k_hop>1` with 422. Never ignore.
5. **Fix WM vocabulary:** extend `MemoryType` + `MemoryStoreRequest` with `working_memory` (eviction as metadata, not type). Then wire `WMPersister` — or delete `wm_persistence.py` (no ghost).
6. **Drain or delete ghost outbox topics** (`db/outbox.py:39-48`).

### Phase 3 — Degraded-recall flags + embedding durability (2d)
7. Graph ops return `{hits, degraded, reason}` instead of bare `[]`. Propagate `degraded` through `MemorySearchResponse` / `GraphNeighborsResponse`.
8. **B22 fix:** on Milvus insert failure, abort the transaction or enqueue a vector-outbox + replay. Never silently drop a precomputed vector.

### Phase 4 — Kill orphan stores (1–2d)
9. Route Oak option vectors through SFM (`memory_type=semantic`, `payload.kind=option`) or quarantine explicitly. Delete `MilvusClient.upsert_option` write usage.
10. Remove Qdrant residue from `generate-global-env.sh` + `.gitignore`.

### Phase 5 — Scope ADR for non-memory brain state (1d)
11. ADR: are neuromod / learning weights / BrainSetting / predictor state in SFM? If yes, add `memory_type="state"` or `sfm_brain_state`. If no, document the boundary so "ALL data" is measurable.

---

## 5. Remediation Plan (fix what prior agents broke)

| # | Fix | Files | Action |
|---|---|---|---|
| R1 | Restore single store-body seam | `memory/remember.py:191-272,421-425` | Use `_seam_store_fields`; regression test asserts top-level `embedding`/`tenant_id` on every POST |
| R2 | Make importance real | SFM `api/schemas.py`, `api/routers/memory.py`, `admin/core/services.py` + Brain `memory/*` | Field end-to-end; test stored `importance != 0` |
| R3 | k_hop truth | SFM `api/routers/graph.py`, `admin/core/services.py:603+` | BFS to depth `k_hop` or 422 on `k_hop>1` |
| R4 | WM type lie | `wm_persistence.py` + SFM `models.py`/`schemas.py` | Implement-or-delete; align vocabulary |
| R5 | Ghost outbox topics | `db/outbox.py:39-48` | Implement producers or delete topic rows |
| R6 | Direct Milvus writers (Oak) | `jobs/milvus_reconciliation.py`, `api/endpoints/oak.py`, `memory/milvus_client.py` | SFM-only vector writes; keep `MilvusClient` read-only or delete |
| R7 | Graph silent `[]` | `memory/client/graph_ops.py:254-395` | Flag degraded; never bare `[]` on failure |
| R8 | B22 vector drop | SFM `admin/core/services.py:251-279` | Fail-closed transaction or vector-outbox + replay |
| R9 | Qdrant residue | `scripts/generate-global-env.sh:58`, `.gitignore:100-101` | Delete |
| R10 | Uncommitted agent debris | both repos `git status` | Commit or revert; clear A2A double-claims |
| R11 | Dual `Authorization`+`X-API-Key` | `memory/sfm_auth.py:30-33` | Drop `X-API-Key` if unused |
| R12 | Ghost health keys | `api/endpoints/health.py:150-152` | Read `SOMABRAIN_MEMORY_DEGRADE_*`; derive queue flag |
| R13 | Dead `episodic_snapshots` | `admin/core/models.py:92-121` | Implement-or-delete |
| R14 | Compat manifest drift | both `soma-compatibility.json` | Correct `self.name` + canonical seam routes |
| R15 | `except Exception: pass` | `client/write.py:151-156` | Outbox enqueue or raise |
| R16 | Outbox replay identity | `services/outbox_sync.py:51-61` | Use original `coord`, unwrap nested payload |
| R17 | GET search `memory_type` parity | SFM `api/routers/search.py:36` | Add filter |
| R18 | Ghost `ENTROPY_CAP` / `http_*` knobs | `learning/annealing.py:73`, `brain_settings/models.py:379` | Rename or delete |

### Order of operations (nothing breaks mid-remediation)

```
0. A2A claim + freeze contract
1. SFM additive schema (importance, belief fields, working_memory enum) — old Brain still works
2. SFM store/search/graph honesty (importance write, k_hop, degraded flag, fail-closed Milvus)
3. Brain seam fields + WM type + degraded flag + single body builder
4. Event/metric/snapshot/learning sinks → SFM
5. Ghost deletion (only after readers exist or keys proven unread)
6. Docs + A2A ledger + handshake ACK
```

Rollback at each wave = revert that wave's migration + code. Additive migrations are reversible.

---

## 6. Verification Plan

### Unit / contract
```bash
# SFM
cd somafractalmemory && python -m pytest tests/unit -q

# Brain
cd somabrain && python -m pytest tests/unit tests/property/test_forbidden_terms.py -q
```

### Integration smoke (real infra)
```bash
# 1. Write with importance + belief + embedding → 200
# 2. GET returns importance == 0.7 (B20 fixed)
# 3. WM write memory_type=working_memory → 200, not 422 (D1 fixed)
# 4. GET /graph/neighbors?k_hop=2 differs from k_hop=1 (B18 fixed)
# 5. Kill Milvus → search returns degraded=true, NOT [] (B17/B21 fixed)
# 6. Round-trip through SomaBrain only: POST /remember → GET /recall → hit.importance != 0
```

### Regression gates
```bash
cd somabrain && python -m pytest tests/unit tests/integration -q
cd somafractalmemory && python -m pytest tests -q
python -m pytest tests/property/test_forbidden_terms.py -q   # no stub/TODO/qdrant
```

---

## 7. Definition of Done — "100% integrated"

1. **Every Brain artifact has an SFM sink.** Episodes, WM items, beliefs, importance, embeddings, graph edges, events, metric/sleep snapshots, learning state — each lands in `sfm_memories` / `sfm_vector_embeddings` / `sfm_graph_links` / Milvus through the single `MemoryClient` gateway (T-1).
2. **No accept-and-ignore.** `importance`, `belief_*`, `k_hop`, `memory_type` are persisted/honoured or rejected 422.
3. **B17–B22 / B29 closed with file:line proof.**
4. **Degraded recall never silent `[]`.** Brain raises `MemoryRecallUnavailable` or returns hits with `degraded=true`. Distinguishable from genuine empty.
5. **Stack lock holds.** Milvus only, Postgres, bearer auth, no Qdrant, no ghost settings.
6. **Tests green on real infra.** A2A ledger records the contract change with handshake ACK.

---

## 8. Risks & Open Questions

1. **"ALL data" scope** — if neuromod/learning/BrainSetting must live in SFM, Phase 5 is a schema+API expansion, not wiring. Needs operator decision.
2. **WM as a type** — `working_memory` is not in triad INVARIANTS §5 vocabulary. Either standard changes or WM is episodic + layer metadata.
3. **Uncommitted trees** — both repos have large dirty state from prior agents; land or discard before remediation PRs.
4. **A2A collision** — two seats claim the same files (`CLAIMS.md:71-72`). Coordinate before Phase 1.
5. **Milvus-down cost** — fail-closed vs async-replay needs an explicit decision (T-6 favors durable-before-hop).
6. **B29 is undefined** — needs a definition in CLAUDE.md / agent doc.

---

## 9. Process Notes

- A2A: `somafractalmemory/docs/plans/a2a/CLAIMS.md:10` has **ACTIVE** claim on `infra/standalone/docker-compose.yml` (`soma-infra-health`). Do not touch without handshake.
- Prior-agent damage already cleaned (do not re-break): file presets purged; 79 dead BrainSetting keys deleted; HTTP placeholder defaults fixed; tenant-credential bind landed (W-H3).
- No Qdrant code exists in either repo — stack lock holds. Residue is docs/ops only.
- `tests/property/test_forbidden_terms.py` actively forbids `mock|stub|placeholder|todo|fixme|dummy` in prod code — keep it green.
