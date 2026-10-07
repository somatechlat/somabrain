# UI FIELD PARITY — Agent Zero → Soma (100% + better)

## Document Control

| Field | Value |
|---|---|
| Document Title | UI Field Parity — Agent Zero to Soma Agent |
| Document Identifier | SOMA-UI-FIELD-PARITY-001 |
| Version | 1.0.0 |
| Date | 2026-10-07 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9241-210:2019 — Human-centred design |
| Next Review | 2026-12-28 |
| Related | SOMA-UI-UX-001 · SOMA-UI-SPEC-001 · SOMA-UI-MOCKUPS-001 · SOMA-UI-MODEL-ADMIN-001 |
| Sources | `agent-zero-main` settings + `_model_config`; `somaAgent01` admin/llm, voice, agents, core/settings |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-10-07 | SomaTech Engineering | Initial complete field parity tables (Agent Zero ↔ Soma). |

**Rule:** Every working Agent Zero field has a Soma home. Soma UI is easier and more powerful. No “slot” language.

---

## 1. Model fields (model-field.html) — must all exist

| Agent Zero field | Soma UI (Normal / Advanced) | Storage |
|---|---|---|
| Provider | Normal | `provider` |
| Model name + **search** | Normal + **Load models** list | `name` |
| API key (masked, reveal) | Normal → **Vault** | secrets |
| Supports Vision | Normal | `vision` |
| Use separate Vision Model | Advanced | vision sidecar |
| Context window size | **Advanced** | `ctx_length` |
| API base URL | **Normal = Custom URL** | `api_base` |
| Context space for chat history | **Advanced** (slider 0.01–1) | `ctx_history` |
| Max embeds | Advanced (if vision) | `max_embeds` |
| Timeout (seconds) | Advanced | `timeout` |
| Max tokens | **Advanced** (explicit + kwargs map) | `max_tokens` / kwargs |
| Context space for utility input | Advanced (slider) | `ctx_input` |
| Requests per minute | Advanced | `limit_requests` |
| Input tokens per minute | Advanced | `limit_input` |
| Output tokens per minute | Advanced | `limit_output` |
| Additional parameters | Advanced JSON | `kwargs` |

**Soma-only extras (better than Agent Zero):** display_name, is_active, cost_tier, priority, capabilities, domains, Used-for, Activate button, Test on card.

## 2. Agent settings (agent.html)

| AZ | Soma |
|---|---|
| Default agent profile | Personality |
| Knowledge subdirectory | Knowledge folder |
| Inherit active project | Inherit current project |
| Consecutive unusable response limit | Max failed replies |

## 3. Workdir (workdir.html)

| AZ | Soma Settings |
|---|---|
| Workdir path + Browse | Workspace path + Browse |
| Show workdir structure | Show workspace to agent |
| Depth / Line / Folder / File limits | Advanced workspace limits |
| Ignored files (gitignore) | Ignore list |
| Preview workspace map | **Preview** button |

## 4. Locale / Interface

| AZ | Soma |
|---|---|
| Timezone + effective | Timezone + effective |
| Time format 12h/24h | Time format |
| UI control visibility mobile/desktop | Interface visibility |

## 5. Voice

| AZ | Soma 7C |
|---|---|
| voice plugin fields | Persona, voice_id, speed, volume, TTS/STT, language, turn detection, silence, model, prompt, temperature, max_tokens |

## 6. External / MCP / Skills / Backup / Remote

| AZ | Soma Settings section |
|---|---|
| API keys | 7F Integrations (Vault) |
| LiteLLM params | 7I or 7H Advanced |
| Secrets vars | 7F |
| Auth login/password | 7H Security |
| Remote control tunnel | **7U Remote** |
| MCP servers + timeouts | **7P MCP** |
| Skills list/import/scan | **7P Skills** |
| Backup/restore/update | **7G Advanced** |
| Plugins marketplace | **7O Plugins** |
| File browser prefs + remote folders + size limits | **5C Files** |
| Developer RFC + websocket test | **7H System** |

## 7. Improvements vs Agent Zero (why Soma UI is better)

1. **Cards** — whole model on one card; AZ hides identity in forms.  
2. **Activate** one-click LIVE.  
3. **Load models** list from key + Custom URL (AZ search; we show full list first).  
4. **Normal vs Advanced** — everyday vs power (AZ buries all in one form).  
5. **No “slot”** — Used for / Chat / Help / Memory.  
6. **Keys in form + Vault** — complete control; AZ separate modal.  
7. **Seeded DeepSeek 2.8 LIVE**.  
8. **Test on card**.  
9. Full product map: memory, multimodal, quality, gateway, embeddings (AZ weaker).

## 8. Acceptance

- [ ] Side-by-side: every AZ field name appears in Soma mock field tables.  
- [ ] Model modal Advanced includes ctx_history, max_embeds, timeout, max_tokens, rate limits, kwargs.  
- [ ] Custom URL + Load models documented.  
- [ ] Zero UI string “slot”.  
