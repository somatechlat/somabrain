# SOMA-BR-OPS-RUNBOOK-001 — Agent Operations Runbook

> **Read this before grepping the codebase.** Operational facts (tokens, URLs,
> ports, store roles, proofs) live here. Code wins on behavior; this file
> tells you *where* to look and *how* to operate without inventing values.

---

## Document Control

| Field | Value |
|---|---|
| Document Title | Agent Operations Runbook |
| Document Identifier | SOMA-BR-OPS-RUNBOOK-001 |
| Version | 1.0.1 |
| Date | 2026-10-09 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2027-01-09 |
| Related | `SOMA-STD-TRIAD-001`, `SOMA-BR-ARCH-TRUTH-001`, `2026-10-05-COORDINATION-HANDOFF.md` |
| Source of truth | Live standalone stack + `somabrain/settings/managed.py` |
| Audience | Every coding agent on somabrain / somaAgent01 / somafractalmemory |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.1 | 2026-10-09 | SomaTech Engineering | Tenant fallback documented accurately (SOMABRAIN_DEFAULT_TENANT only when credential has none; else require_tenant refuses). |
| 1.0.0 | 2026-10-09 | SomaTech Engineering | Initial issue. Vault map, topology keys, store roles, remember/recall proofs, failure recipes from live M2/HRR incidents. |

---

## 1. Laws (binding)

| # | Law |
|---|---|
| 1 | **Settings = Django + BrainSetting (DB).** Never `os.environ` as authority. Never YAML/JSON file presets. |
| 2 | **Secrets = Vault only** (Covenant Art 26). Never ENV, never files in git, never DB plaintext. |
| 3 | **No hardcoded values** at call sites (URL/host/port/path/number). Declaration-site only (`R-VAL-04`). A default is hardcoded if it sits outside the settings module / BrainSetting registry. |
| 4 | **No fallbacks.** Missing setting = refusal naming the setting (Rule 91 / T-5). |
| 5 | **Fail-closed.** Never guess a host or credential. |
| 6 | **CODE = TRUTH.** Docs must cite `file:line` when they claim behavior. |
| 7 | **No AI attribution** on commits or PRs. |

Resolver (one lookup helper): `somabrain/settings/managed.py::managed_get`
— BrainSetting (DB) then Django. Topology keys are listed in `managed.py::_BRAIN_KEYS`.

---

## 2. Live standalone map (ports)

| Service | Host port | Container | Role |
|---|---|---|---|
| SomaBrain API | **30101** | `somabrain-somabrain_standalone_app-1` | Agent-facing brain (remember/recall/act) |
| SomaFractalMemory (SFM) | **10101** | `somafractalmemory-standalone-api` | Durable LTM store (Postgres + Milvus) |
| Brain Vault | **30200** | `somabrain_standalone_vault` | Secrets for brain + agent shared credential |
| SFM Postgres | 10432 | `somafractalmemory-standalone-postgres` | SFM durable rows |
| SFM Milvus | 10530/10531 | `somafractalmemory-standalone-milvus` | SFM vector index |
| Agent API | 20020 | `somaagent_standalone` | somaAgent01 |
| Agent WebUI | 20080 | `somaagent_webui` | Lit UI |
| Brain Postgres | 30106 | `somabrain-somabrain_standalone_postgres-1` | Brain Django ORM (outbox, BrainSetting) |
| Brain Redis | 30100 | `somabrain-somabrain_standalone_redis-1` | Cache / adaptation state |
| Kafka | 30102 | `somabrain-somabrain_standalone_kafka-1` | Domain events / outbox sync |
| OPA | 30104 | `somabrain-somabrain_standalone_opa-1` | Policy (fail-closed) |

Docker DNS names used *inside* the compose network (not from the host):

- SFM: `http://somafractalmemory-standalone-api:10101`
- From the host: `http://127.0.0.1:10101`

**Never hardcode these in application code.** They are topology settings.

---

## 3. Secrets map (Vault only — never print values)

### 3.1 Vault root token (brain)

| Item | Value |
|---|---|
| Custodian | OS keychain or operator-held `VAULT_TOKEN` / `VAULT_TOKEN_FILE` pointing at the T0_DIR RAM tmpfs (`/run/t0/vault_root_token`). **Never a file in any repo** (SOMA-STD-BOOTSTRAP-001 §2.3, Covenant Art 26). |
| Vault address | `http://127.0.0.1:30200` |
| Lookup | `GET /v1/secret/data/agent/credentials` with header `X-Vault-Token: <root>` |
| Shared credential key | `somabrain_memory_http_token` |

```bash
# Pattern (token values stay in shell variables / T0_DIR tmpfs; never echo them,
# never write them to a repo path). Example: read the scoped/one-shot token from
# the RAM tmpfs custodian mounted at /run/t0 inside the compose network.
ROOT=$(tr -d '[:space:]' </run/t0/vault_root_token)
MEM=$(curl -sS -H "X-Vault-Token: $ROOT" http://127.0.0.1:30200/v1/secret/data/agent/credentials \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["data"]["somabrain_memory_http_token"])')
```

Python helper already written: `scripts/live_learning_e2e.py::resolve_bearer_token()`.

### 3.2 What each credential is for

| Vault key | Used by | Presented to |
|---|---|---|
| `secret/agent/credentials[somabrain_memory_http_token]` | Agent **and** Brain→SFM | `Authorization: Bearer` on brain API **and** SFM API |
| `somabrain/auth[jwt_secret]` | Brain | Django `SECRET_KEY` / JWT |
| `somafractalmemory/database[password]` | SFM | Postgres role `somafractalmemory` |

**One shared HTTP bearer.** Live proof 2026-10-09: SFM `settings.SOMA_API_TOKEN`
hash-equals `somabrain_memory_http_token`. A second `somabrain/runtime[api_token]`
is how brain once sent a log line as a credential and got 401
(`somabrain/core/security/vault_client.py::get_runtime_secret` now maps
`api_token` / `memory_http_token` to that **one** key).

### 3.3 Token hygiene

- Never print or commit tokens. GitHub push protection has already blocked a leaked file once.
- Never set tokens in ENV (law). Bootstrap reads Vault into Django settings.
- `SOMA_API_TOKEN_FILE` / `SOMABRAIN_MEMORY_HTTP_TOKEN_FILE` are **path** slots only.

---

## 4. Topology settings (BrainSetting / Django — not ENV)

| Purpose | Key | Example live value | Reader |
|---|---|---|---|
| SFM base URL | `memory_http_endpoint` | `http://somafractalmemory-standalone-api:10101` | `managed_get` → `resolve_memory_endpoint` |
| Kafka | `kafka_bootstrap_servers` | compose broker | `get_kafka_bootstrap` |
| OPA | `opa_url` | compose OPA | OPA client |
| Redis | `redis_host` / `redis_port` | compose Redis | `get_redis_url` |
| Milvus | `milvus_host` / `milvus_port` | compose Milvus | vector store factory |
| Default tenant (fallback only when credential has none) | `SOMABRAIN_DEFAULT_TENANT` | `standalone` in standalone profile; empty otherwise → `require_tenant` refuses | `somabrain/tenant.py` |

Set BrainSetting via `GET/PUT /brain/settings` (system-role UI) or
`BrainSetting.set(key, value, tenant)`. Tenant is required (T-5).

```bash
# Prove the URL is visible on the live request path
curl -sS -H "Authorization: Bearer $MEM" \
  -H 'Content-Type: application/json' \
  -X POST http://127.0.0.1:30101/memory/remember \
  -d '{"content":"probe","namespace":"ltm"}'
# Expect 200 + durability fields (see §6). 503 "Memory HTTP endpoint required"
# means BrainSetting.memory_http_endpoint is empty on the worker — see §7.
```

---

## 5. Why SFM has **both** Postgres and Milvus

They are **not** duplicates. They are two indexes over one logical memory, split
by access pattern so save/recall stays O(log n) at millions of transactions.

| Store | What it holds | Access pattern | Why not the other |
|---|---|---|---|
| **Postgres** | Durable truth: memory rows, payloads, tenant/namespace partitions, graph edges, metadata, TTL, audit | Point get/put, exact idempotency (`mem:{coord}`), transactions, outbox replay, quotas | Vector ANN cannot do transactional unique keys or SQL joins for graph/ops |
| **Milvus** | Approximate nearest-neighbor **vector index** over embeddings | Top-k similarity recall under load | Relational scan of millions of vectors is too slow for p95 recall |

**Save path (T-6 durable-before-hop):**

```
remember → embed (HRR/Rust default) → outbox row (Brain Postgres)
        → SFM write:
             Postgres  = payload + coord + tenant/namespace + durability row
             Milvus    = embedding vector for ANN recall
        → WM promote (in-process) → LTM persisted
```

**Recall path:**

```
recall → embed query → Milvus ANN top-k (speed)
       → Postgres hydrate payloads / filter tenant+namespace (truth)
       → rank / rerank (brain) → return hits
```

**Millions of transactions:** Postgres takes the write/transaction/idempotency
load; Milvus takes the similarity load; Kafka/outbox decouples ingest from SFM
latency; brain WM is the hot cache. Dropping either store breaks a hard
requirement: Postgres-only cannot meet recall p95; Milvus-only cannot meet
T-6 durability or `mem:{coord}` idempotency.

Evidence: SFM health aggregator lists **both** `postgresql` and `milvus` as
required services (`somafractalmemory` health payload). Brain remember response
reports `durability: durable_outbox` (fast-ack) or `persisted_ltm` (sync) and `outbox_event_id` only when the durable
path succeeded.

---

## 6. Proofs (run these — do not claim without them)

### 6.1 Remember 200 (M2)

```bash
curl -sS -X POST http://127.0.0.1:30101/memory/remember \
  -H "Authorization: Bearer $MEM" -H 'Content-Type: application/json' \
  -d '{"content":"proof","namespace":"ltm"}'
```

**Pass:** HTTP 200 and body includes:

| Field | Required |
|---|---|
| `ok` | `true` |
| `durability` | `durable_outbox` **or** `persisted_ltm` |
| `outbox_event_id` | integer (T-6 proof) |
| `queued_for_ltm` / `persisted_to_ltm` | `true`/`false` match durability |
| `error` | `null` |

**Fast-ack (default ON):** accept returns `durable_outbox` + `queued_for_ltm=true`
after the verified outbox row. LTM hop is background/outbox_publisher. Do **not**
require `persisted_to_ltm=true` on the accept response. Sync path (fast-ack off)
returns `persisted_ltm`.

### 6.2 HRR default ON

```text
logs must NOT contain: "falling back to TinyDeterministicEmbedder"
QuantumLayer must construct (see bootstrap/singletons.make_quantum_layer)
mix ∈ {none, hadamard} — SOMABRAIN_MATH_BHDC_MIX (settings/cognitive.py)
```

### 6.3 SFM health

```bash
curl -sS -H "Authorization: Bearer $MEM" http://127.0.0.1:10101/health
# healthy: true — postgresql + redis + milvus all healthy
```

### 6.4 Live learning

```bash
python scripts/live_learning_e2e.py   # exit 0
```

---

## 7. Failure recipes (from live incidents)

| Symptom | Real cause | Fix |
|---|---|---|
| `503 Memory HTTP endpoint required but not configured` | `managed_get` ORM read failed in ASGI (SynchronousOnlyOperation swallowed) or BrainSetting row empty | `settings/managed.py::_db_call` hops ORM off the event loop; set BrainSetting `memory_http_endpoint`; restart app (code mount is `ro`) |
| `401 Invalid API token` / `Unauthorized` from SFM | Brain sent wrong bearer (e.g. log text in `SOMA_API_TOKEN`) | One authority: `somabrain_memory_http_token` (`vault_client.get_runtime_secret`) |
| SFM `password authentication failed for user somafractalmemory` | Postgres role password ≠ Vault `somafractalmemory/database[password]` | Align role password to Django-resolved secret; never invent a second password |
| `mix must be 'none' or 'hadamard'` + Tiny fallback | `SOMABRAIN_MATH_BHDC_MIX` declared as float | Declaration is vocab: `env.str` default `"none"`; binary_mode `"pm_one"` \| `"zero_one"` |
| `tenant is not configured (T-5)` | `SOMABRAIN_DEFAULT_TENANT` empty | Fail-closed — configure tenant; never default |
| Need API token for curl | — | §3.1 Vault lookup; never commit the value |

**Code mount:** `somabrain:/app/somabrain:ro` — host edits need container restart.

---

## 8. A2A (always on)

| File | Use |
|---|---|
| `docs/plans/a2a/CLAIMS.md` | Claim paths **before** edit |
| `docs/plans/a2a/LEDGER.md` | Append-only commit/proof log |
| `docs/plans/a2a/INBOX.md` / `OUTBOX.md` | Peer messages (append-only) |
| Handoff | `docs/plans/2026-10-05-COORDINATION-HANDOFF.md` |

Rules pack: `/Users/macbookpro201916i964gb1tb/Documents/GitHub/somaAgent01/docs/standards/SOMA-STD-TRIAD-001.md`.
Local agents: `.mimocode/agent/brain-memory-engineer.md`, `brain-adversarial-skeptic.md`.

---

## 9. Best save / recall (millions of txn)

1. **Write:** one durable outbox row first (T-6), idempotency `mem:{coord}`, then SFM dual-write (Postgres truth + Milvus vectors). Never accept without the outbox row.
2. **Read:** ANN for candidates (Milvus), relational filter/hydrate (Postgres), brain rerank. Fail-closed on outage — no `return []` pretending success.
3. **Scale knobs (BrainSetting, not files):** `memory_decay_rate`, `wm_prune_threshold`, `ltm_prune_threshold`, `max_wm_items`, `max_ltm_items_per_tenant`.
4. **HRR on** (`SOMABRAIN_USE_HRR` default true) so embeddings are stable hyperdimensional vectors for ANN.
5. **Tenant:** credential-bound; body tenant is assertion only (403 on mismatch).
