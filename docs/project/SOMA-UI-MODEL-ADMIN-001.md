# SOMA AGENT — MODEL ADMINISTRATION UI SPECIFICATION

## Document Control

| Field | Value |
|---|---|
| Document Title | Model Administration — Card UI Specification |
| Document Identifier | SOMA-UI-MODEL-ADMIN-001 |
| Version | 1.0.0 |
| Date | 2026-10-07 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9241-210:2019 — Human-centred design |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-10-07 | SomaTech Engineering | Initial card-based model admin specification (replaces tab+dropdown slots UX). |

---

## 1. Purpose and non-negotiables

Model administration **must** allow the operator to:

1. See every model as a **full card** (provider, name, role badges, context, status).
2. **Select a card** and edit **all** settings for that model in one panel.
3. Assign the model to **Chat / Utility / Embedding** slots from the card.
4. Keep API keys **write-only** (Vault) with Show / Test Connection.
5. Reveal **advanced** fields only on demand (SOMA-UI-UX-001 P-03).

**Source of truth for fields:** `admin/llm/api.py` `ModelIn` / `ModelOut` (provider, name, type, api_base, capabilities, priority, cost_tier, domains, ctx_length, limit_*, vision, kwargs).

**Reference UX patterns (agent-zero `_model_config`):** `model-field` block, Main/Utility/Embedding section cards, Advanced expander, summary + edit, keys separate from model defs.

**Forbidden:** three bare slot dropdowns as the only editor; flat catalog that hides ModelIn fields; silent llama default without showing the binding.

---

## 2. Screen anatomy

Single surface: **`/settings/models`** (also `/agent/models`).

```
[1] Active summary card
[2] Model card grid (select / add)
[3] Full model editor (selected card)
[4] Slot map (Chat / Utility / Embedding) + presets
```

### 2.1 Active summary

- Provider, model name, role badges (Chat / Utility / Embedding / Vision)
- Key state: masked + “Configured” / “Missing”
- Actions: **Edit selected** · **Test Connection**

### 2.2 Model card grid

Each card (SOMA-UI-SPEC-001 card variants: default / hoverable / **selected**):

| Element | Content |
|---|---|
| Header | Provider label + status (Active / Setup / Error) |
| Title | Model name |
| Meta | ctx_length · cost_tier · vision · speed (if known) |
| Roles | Chip list derived from slot assignment + type |
| Footer | **Select** / **Selected ✓** · quick **Assign** menu |

Grid is keyboard-reachable (P-07). Click card → selected state → editor loads.

### 2.3 Full model editor (THE requirement)

Two-column field rows (`field-label` | `field-control`) + Advanced collapse.

**Primary (always visible)**

| Field | Control | API |
|---|---|---|
| Provider | select (resets api_base/kwargs if changed) | `provider` |
| Model name | text + model-search | `name` |
| Type | chat / embedding / utility (if supported) | `type` |
| API key | masked + Show + Test | Vault via provider (not stored on model) |
| Supports vision | toggle | `vision` |
| Assign slots | checkboxes Chat / Utility / Embedding | `PUT /llm/slots` |

**Advanced (collapsed by default)**

| Field | Control | API |
|---|---|---|
| API base URL | text | `api_base` |
| Context window | number | `ctx_length` |
| Max tokens / limits | number | `limit_*` |
| Timeout | number | (config) |
| Rate limits | numbers | `limit_*` / config |
| Cost tier | select | `cost_tier` |
| Domains | tags | `domains` |
| Capabilities | multi | `capabilities` |
| Priority | number | `priority` |
| Additional parameters | JSON editor | `kwargs` |

Actions: **Save Model** · **Test Connection** · **Delete** (confirm) · **Assign to Slots**.

### 2.4 Slot map

| Role | Shows | Edit path |
|---|---|---|
| Chat | selected model card summary | from card Assign or preset |
| Utility | model (must support utility — **not** chat-only list) | same |
| Embedding | embedding model | same |

- **Inactive models stay visible** in the map (badge “inactive”) — never silently “unset”.
- Persistence must be **one contract** (documented in backend section): do not hide Capsule.chat_model vs AgentSetting split in the UI; show “Saved for capsule / tenant” and use one write path.

---

## 3. Empty / loading / error states

| State | UI |
|---|---|
| No models | Hero empty state + **Add model** + setup-gate |
| Loading | Skeleton cards |
| Test connection fail | Inline error on card + toast |
| No key | Card status “Setup”; editor prompts key |
| Permission denied | Read-only banner (`settings:edit` required) |

---

## 4. Permissions

- **View models:** authenticated.
- **Edit model / keys / slots:** `settings:edit` → `system:configure` (existing).
- Without edit: show cards and slot map; disable Save/Assign/Delete.

---

## 5. API contract (UI must match)

| Endpoint | Use |
|---|---|
| `GET/PUT /llm/providers` | provider list, base_url, default_model, enable |
| `GET/POST/PATCH/DELETE /llm/models` | full `ModelIn`/`ModelOut` fields |
| `GET/PUT /llm/slots` | chat_model_id, utility_model_id, embedding_model_id |
| `GET/POST/... /llm/presets` | named slot+model bundles |
| `POST /llm/test-connection` | per model/provider |
| `PUT /secrets/providers/{id}` | write-only keys |

UI **must** send and display: `capabilities, priority, cost_tier, domains, ctx_length, limit_*, vision, kwargs` (today they are hidden — this is a defect).

---

## 6. Design system alignment

- Dark-first palette (SOMA-UI-MOCKUPS-001 COLOR KEY)
- Cards: 8px radius, selected border Soma Blue `#3B82F6`
- `<soma-secret-field>` for keys; `<soma-model-card>` / `<soma-model-editor>` / `<soma-slot-map>` (to be specified in SOMA-UI-SPEC-001)
- Progressive settings (P-03); modules-style visual cards (P-04)

---

## 7. Acceptance criteria

1. Selecting a card opens an editor that exposes **every** `ModelIn` field.
2. Save round-trips all fields through `PATCH /llm/models`.
3. Assign Chat/Utility/Embedding from the card updates the slot map.
4. Utility slot lists models that can serve utility (not chat-only).
5. Inactive models remain in the slot map.
6. Advanced block collapsed by default.
7. API key never rendered in clear text.
8. Without `settings:edit`, edit controls are disabled (not hidden without explanation).
9. No silent provider/model switch: active binding always visible in summary card.

---

## 8. Out of scope

- Chat message UX (SOMA-UI-UX-001 §chat)
- Billing / tenant admin screens
- Embedding math / recall quality (R-14)

---

## 9. Mapping — agent-zero → Soma

| agent-zero | Soma |
|---|---|
| `model-field.html` | `soma-model-field` rows in editor |
| `main.html` Main/Utility/Embedding cards | slot sections + card roles |
| `preset-overview.html` | Active summary + slot map |
| `api-keys.html` | Vault-backed `soma-secret-field` + test |
| Advanced expander | Advanced collapse |
| `model-setup-gate.html` | Empty/setup state on grid |
