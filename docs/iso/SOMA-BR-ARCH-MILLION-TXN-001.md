# SOMA-BR-ARCH-MILLION-TXN-001 — Full Production Architecture (as built)

> **Code = truth.** Boxes are processes/stores **running now**. Dashed = proposed
> scale-up that reuses **existing** infra only (Temporal · Kafka · OPA · Outbox).
> Stack lock: Temporal owns long/scheduled work. No second queue authority.

---

## Document Control

| Field | Value |
|---|---|
| Document Title | Full Production Architecture (as built) |
| Document Identifier | SOMA-BR-ARCH-MILLION-TXN-001 |
| Version | 1.1.0 |
| Date | 2026-10-09 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | Product Owner |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2027-01-09 |
| Source of truth | Live compose + `somabrain/` + `somaAgent01/` + `somafractalmemory/` |
| Related | `SOMA-BR-OPS-RUNBOOK-001`, `SOMA-STD-TRIAD-001`, `SOMA-BR-ARCH-TRUTH-001` |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-10-09 | SomaTech Engineering | Initial dual-store + write path architecture. |
| 1.1.0 | 2026-10-09 | SomaTech Engineering | **Full infra**: Temporal (agent long-work), OPA (fail-closed), Kafka (`cog.*` / `memory.store`), Vault, exporters. Proposal rewritten to reuse these — no second queue authority. |

---

## 1. Full stack (everything that is real)

```
┌──────────────────────────────── AGENT PLANE ────────────────────────────────┐
│  somaagent_webui          :20080   Lit 3.x                                  │
│  somaagent_standalone     :20020   Django + Ninja                           │
│  Temporal workers (LONG / SCHEDULED WORK — sole authority)                   │
│      ├─ conversation_worker   process_message · sleep_cycle · advance_jobs  │
│      ├─ delegation_gateway    A2A / tool delegation workflows               │
│      └─ research_workflow     outline / research activities                 │
│  Temporal host: SA01_TEMPORAL_HOST (one connect authority)                   │
│  somaagent_postgres :20432   redis :20379   vault :20882   keycloak :20880  │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ Bearer somabrain_memory_http_token
                                     │ (Vault only — never ENV/file)
┌────────────────────────────────────▼───────────────── BRAIN PLANE ─────────┐
│  somabrain_app           :30101  Django Ninja  remember/recall/act/settings │
│       OpaMiddleware (every route)  ──► OPA :30104  FAIL-CLOSED              │
│  somabrain_cog           :8083   cognitive loop · domain predictors         │
│  somabrain_outbox_publisher        OutboxEvent drain → SFM (durable hop)    │
│  somabrain_integrator_triplet      Kafka consume/produce GlobalFrame        │
│                                                                        │
│  Brain Postgres :30106   OutboxEvent · BrainSetting · sleep · audit         │
│  Brain Redis    :30100   cache · adaptation state                           │
│  Kafka          :30102   cog.*.updates · cog.global.frame · memory.store    │
│                         memory.degraded · memory.episodic.snapshot          │
│                         cog.segments · cog.next_event · soma.audit          │
│  Schema Registry :30108    Kafka exporter :30103                            │
│  Vault :30200 (+ unseal watch)   OPA :30104                                 │
│  Prometheus :30105   Jaeger :30111-14   MinIO :30109-10                     │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ same Vault bearer
┌────────────────────────────────────▼──────────────── MEMORY PLANE ─────────┐
│  somafractalmemory_api :10101                                               │
│       OPA :10818 (fail-closed)                                              │
│  Postgres :10432  TRUTH   rows · coord · graph · TTL · mem:{coord}          │
│  Milvus   :10530  INDEX   ANN 768-d                                         │
│  Redis :10379   Vault :10200   MinIO   etcd   OPA                           │
└────────────────────────────────────────────────────────────────────────────┘
```

**Embeddings:** HRR dim **8192** internal → seam **768** (`MEM_EMBED_DIM`).

**T-1:** agent never holds an SFM client.  
**T-6:** durable-before-hop.  
**Stack lock:** Temporal = long/scheduled work. Kafka = domain events. OPA = policy. Outbox = durability gate. No parallel cron/queue authority.

---

## 2. Control planes (not just “infrа”)

| Plane | Technology | What it owns |
|---|---|---|
| **Long / scheduled work** | **Temporal** (agent) | chat message cycles, sleep/consolidation, research, A2A delegation, job advance |
| **Policy** | **OPA** (brain + SFM) | every brain route (`OpaMiddleware`), integrator leader veto, SFM authz |
| **Events** | **Kafka** | `cog.*` predictors, global frame, `memory.store`, audit, DLQ |
| **Secrets** | **Vault** | `somabrain_memory_http_token`, JWT, DB passwords — no ENV |
| **Durability gate** | **Outbox** (Brain Postgres) | T-6 accept + `mem:{coord}` idempotency + replay |
| **Truth / Index** | **Postgres + Milvus** | dual-store (both required) |
| **Cache** | Redis | health, adaptation state, WM assist |
| **Observe** | Prometheus · Jaeger · exporters | metrics · traces · infra health |

---

## 3. Write path (million-txn contract)

```
POST /memory/remember
  │
  ├─ OPA  OpaMiddleware (fail-closed)
  ├─ Bearer (Vault) + credential-tenant bind
  ├─ HRR embed (QuantumLayer default ON)
  │
  ├─ OUTBOX INSERT (Brain Postgres)          ← durability gate
  │     idempotency = mem:{coord}
  │     payload identity ≠ request_id
  │
  ├─ WM admit (in-process hot cache)
  │
  ├─ 200 { durability: durable_outbox | persisted_ltm, outbox_event_id, … }
  │        default fast-ack = durable_outbox (T-6 outbox row; LTM hop async)
  │
  └─ async hop (outbox_publisher → SFM)
        Postgres row  (truth)
        Milvus vector (ANN)
        Kafka: memory.store (event) · memory.degraded (on failure)
```

### Scale levers **already in the stack**

| Need | Existing mechanism | Setting (BrainSetting / Django) |
|---|---|---|
| Concurrent ingest | ASGI app | replica `app` |
| Durable accept | Outbox + publisher | `OUTBOX_TENANT_QUOTA_LIMIT` / `_WINDOW` |
| Retry storm | `mem:{coord}` collapse | — |
| Tenant isolation | headers + credential bind | `SOMABRAIN_DEFAULT_TENANT` |
| Backpressure | outbox quota | tenant quota knobs |
| Long/slow work | **Temporal** activities | agent `SA01_TEMPORAL_HOST` |
| Policy | OPA | `SOMABRAIN_OPA_URL` |
| Events | Kafka `memory.store` / `cog.*` | `kafka_bootstrap_servers` |
| Capacity | prune/decay | `memory_decay_rate`, `max_wm_items`, `max_ltm_items_per_tenant`, `wm/ltm_prune_threshold` |
| Vectors | Milvus ANN | `milvus_host` / `milvus_port` |

---

## 4. Read path (recall)

```
POST /memory/recall
  ├─ OPA
  ├─ embed query (or precomputed 768-d)
  ├─ WM first
  ├─ Milvus ANN top-k
  ├─ Postgres hydrate + tenant/namespace filter
  ├─ rank (hash-penalty from SOMA_HASH_EMBEDDING_PENALTY — settings only)
  └─ 200 hits[]   fail-closed on outage (never fake-empty success)
```

---

## 5. Learning (APM-1) + sleep (Temporal)

```
remember/recall/forget/promote  →  apply_memory_event
        → AdaptationEngine weights α β γ λ μ ν
        → retrieval / utility / prune

Temporal sleep_cycle_activity  →  consolidation / decay / prune
        (sole scheduled-work authority — no cron sidecar)
```

---

## 6. Dual-store (why both)

| | Postgres | Milvus |
|---|---|---|
| Role | Durable truth | ANN index |
| Must | T-6 · `mem:{coord}` · txns · graph | p95 top-k at millions of vectors |
| Fail-open? | **No** | **No** (missing host refuses; schema describe raises) |

---

## 7. PROPOSED ingest scale-up — **reuse full infra only**

No new broker. No second queue. No cron.

```
POST remember ──► [ASGI app replicas]
                    │
                    ├─ embed (HRR) batched per request
                    └─ ONE Outbox row   ← T-6 unchanged
                              │
                    outbox_publisher (existing)
                              │  batch upsert
              ┌───────────────┴────────────────┐
              ▼                                ▼
         SFM Postgres                     SFM Milvus
              │
              └─► Kafka memory.store  (already a topic)
                        │
                        ▼
              Temporal activity (agent plane)
              sleep_cycle / consolidation / research
              uses brain MemoryGateway — never SFM direct
```

| Change | Uses | Explicitly NOT |
|---|---|---|
| Batch SFM writes | existing `POST /memories/batch` + publisher | new service |
| Publisher concurrency | outbox_publisher scaling | new cron |
| Async long jobs | **Temporal** workflows (already own sleep/research) | parallel queue authority |
| Horizontal scale | `app` + `outbox_publisher` replicas | sharding magic |
| Policy on every hop | **OPA** (already middleware) | ad-hoc auth |
| Event fan-out | **Kafka** `memory.store` / `memory.degraded` | in-process bus |

---

## 8. Proof status (2026-10-09)

| Gate | Status |
|---|---|
| remember 200 `durable_outbox` (fast-ack) / `persisted_ltm` (sync) | GREEN |
| recall hits | GREEN |
| HRR QuantumLayer default | GREEN |
| learning E2E | PROVEN (α 1.0→1.40) |
| outbox drain | 1712 sent / 0 failed |
| OPA fail-closed (401 without bearer) | GREEN |
| SFM dual-store fail-closed | GREEN |
| Kafka topics `cog.*` + `memory.store` | GREEN |
| Temporal (agent long-work) | WIRED (conversation · sleep · research · A2A) |
| Rust math core | 17/17 |
| Vault-only secrets | GREEN |
