# Coordination Handoff — 2026-10-05

**For:** any other agent/session working the Soma triad (`somaAgent01` · `somabrain` · `somafractalmemory`).
**From:** the session running rapid-development mode on 2026-10-05.
**Why this file exists:** a cross-session message to `Triad repos last session review [b9fd5b]` was **held and never delivered** (permission-mode mismatch). This is the same content, readable by anyone in the repos.

---

## What is already landed (pushed to main, verified before landing)

### somaAgent01
| Commit | What |
|---|---|
| `dbc46280` | Unbrick the admin API. `settings_model.py` used `Optional` without importing it; `sessions.py` builds settings at import time, so **every endpoint** failed to load. Also one shared agent↔brain credential (was 17 vs 64 chars → 401 on every memory write). Also discarded `_ADMIN_FLOOR`. |
| `56d2786e` | Auth anti-enumeration. Uniform `401 "Invalid credentials"` on every denial; lock state and `retry_after` are audit facts, not client facts. Dummy test pepper replaced with the real Vault reader. |
| `d93e8340` | AgentIQ panel. `GET /api/v2/core/agentiq` was `500 SynchronousOnlyOperation` (`derive_all_settings` called sync ORM from async). Also fixed `lanes.py` reading `body.get("learned")` when the block lives at `body["persona"]["learned"]`. |
| `8653032d` | Brain client: deleted 9 phantom routes (incl. `publish_reward → /learning/reward`, a 404 on every turn), deleted the dead second memory stack, wired `plan/suggest` + `threads` + `personality`. `brain_suggested_tools` was computed then discarded on the stream path. |
| `5549dc4e` | Namespace from the operator layer (`InfrastructureConfig`), one role resolver `TenantUser.roles_for`, e2e selector fixes. |
| `10a9b9fa` | `.dockerignore` was **listed in `.gitignore`** so it was never tracked — every clone built images with no secret exclusions. |
| `ec815df0` | One lane vocabulary (`LANE_KEYS`). Fixed two arithmetic bugs: floor split dropped tokens; minimums **invented** tokens via `buffer += deficit`. |

### somabrain
| Commit | What |
|---|---|
| `3227ca7` | One `_stable_coord` in-repo (was 2; wrapper **deleted**, not aliased). 11 settings names in `ContextBuilder` resolved. |
| `d28ca12` | Recall accepts a precomputed query vector — was re-embedding with a **different** embedder than the write path, so cosine was meaningless and recall returned noise. |
| `1a1e902` | 841 tracked `rust_core/target/**` build artifacts untracked. |
| `ed9677d` | Compose topology exported → brain `/health` **healthy** (11/11, was `critical`); `outbox_publisher` no longer crash-loops. |
| `e826f0b` | Required topology keys added to the tracked `.env.example`. |
| `24362ab` | T-5 fail-closed on `recall_ops` / `outbox` / `retrieval_pipeline`. **Also fixed:** `getattr(graph_client, "tenant_id", "default")` while `MemoryClient` exposes `.tenant` — the getattr always missed and **every tenant was folded into one `"default"` partition**. |

### somafractalmemory
| Commit | What |
|---|---|
| `283783a` | `belief` modelled in `MemoryType` + stats (was accepted then silently dropped). Dummy credential `sfm-api-token-123` removed from `.env` and from `tests/proofs/test_docker_proof.py`. |
| `7552d93` | `.dockerignore` created (the repo had none — both `.env` files were entering the build context). |

---

## What I am NOT touching — tell me if you are

- `rust_core/src/*` and the math work (`3d0fe52 math: real Wiener λ*(p), FWHT guard, Mahalanobis, one recency kernel`) — **not mine**. I don't ship what I don't understand.
- `docs/iso/SOMA-BR-*` Phase A truth docs
- `webui/` (an agent was on UI honesty, stalled)

---

## Open questions for whoever knows

1. **`_BOOTSTRAP` NameError** at `somabrain/settings/django_core.py:265` — `token = _BOOTSTRAP.get("SOMA_API_TOKEN") or _BOOTSTRAP.get("SOMABRAIN_API_TOKEN")` but `_BOOTSTRAP` is **undefined** in that module. It sits on the trust-boundary token reader. Was that dict deleted recently?

2. **`BrainSetting.initialize_defaults`** — `POST /api/context/feedback` 500s with
   `Brain setting 'active_brain_mode' not found for tenant 'default'. Run initialize_defaults() first.`
   Nothing calls it. Is seeding an operator action, or should there be a bootstrap path?

---

## Known remaining defects (named, unowned)

| Defect | Where |
|---|---|
| `return []` on outage on the **live** recall hot path | `somabrain/memory/client/search.py:79,149` (via `read.py:28`) |
| Audit events silently dropped | `somabrain/core/security/audit.py:75` calls `enqueue_event` without `tenant_id`, which now fail-closes |
| ~15 more `or "default"` sites | `outbox_replay.py`, `outbox_clean.py`, `memory_metrics.py`, `tenant_overrides.py`, `quota_manager.py`, `outbox_sync.py` |
| `BrainSetting` schema encodes the fallback T-5 forbids | `brain_settings/models.py:30,73` — `tenant = CharField(default="default")` |
| T-2 still NOT met across the triad | 2 `_stable_coord` (1 brain + 1 agent). Docs claim "MET". **The docs are wrong.** No shared `soma-memory-contract` package exists. |
| `chat_orchestrator.py:1061` emits token counts under `"lanes"` while `agentiq.py:116` emits shares — same key, two units | W3.1 gate |
| Stale `somabrain:latest` image | still has code defaults for `MINIO_ENDPOINT`/`SCHEMA_REGISTRY_URL`, reads `VAULT_TOKEN` from ENV (banned), writes secrets into `os.environ` (AP-05). The live tree is correct; the image predates it. |
| `docker-compose.override.yml` sets `replicas: 0` for `outbox_publisher` | a plain `docker compose up` refuses to start it |

---

## Standing rules in force (from `docs/plans/AGENT-BRIEFING-RAPID-TRIAD-001.md`)

1. **No hardcoded values.** A default IS one.
2. **No fallbacks.** A value comes from a real setting or the call refuses.
3. **One chain:** `Capsule > AgentSetting > InfrastructureConfig > SettingsModel > EMPTY`.
4. **No stubs / mocks / shims / TODOs.** A shim is a bypass.
5. **Secrets — Vault only.** KV v2 `POST` replaces the document: read → merge → write → read back and assert. Never write a secret to any file including `/tmp`.
6. **Fail-closed (Rule 91).** A missing value is a refusal naming the setting.
7. **Never weaken a gate to pass a test.** Absent credential ⇒ failure naming it.
9. **No unnecessary files.** **Delete what is wrong — never back it up.**
11. **Commits** under the owner's own git identity. **No AI attribution of any kind.**

**THE ONE PATH** — never create a lane:
```
browser → WS /ws/v2/chat/{capsule_id} → ChatConsumer → V3ChatOrchestrator
  → run_tool_loop → FanoutMemoryGateway → SomaBrainAdapter → SomaBrain → SFM
```
