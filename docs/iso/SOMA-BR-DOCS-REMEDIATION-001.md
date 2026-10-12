# SOMA-BR-DOCS-REMEDIATION-001 — Documentation Remediation Plan

## Document Control

| Field | Value |
|---|---|
| Document Title | Documentation Remediation Plan — Code as Source of Truth |
| Document Identifier | SOMA-BR-DOCS-REMEDIATION-001 |
| Version | 1.0.0 |
| Date | 2026-10-09 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2027-01-09 |
| Related | `docs/iso/SOMA-BR-DOCS-001.md`, `docs/iso/DOCUMENT-REGISTER.md`, `AGENT.md` |
| Source of truth | Code. Every claim in this plan cites a file path verified on 2026-10-09. |
| Scope | Full documentation audit and remediation for the somabrain repository |
| Audience | Engineering, QA, ISO document control, coding agents |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-10-09 | SomaTech Engineering | Initial audit findings and remediation plan. |

---

## 1. Audit Method

1. Enumerate every tracked `*.md` in the repository (excluding `node_modules`, `.venv`).
2. For each factual claim (file path, class name, default value, capacity, latency, compliance status), verify against the live code tree.
3. Classify findings: **FALSE**, **STALE**, **OVERCLAIM**, **AI-SLOP**, **BROKEN-LINK**.
4. Remediate: delete false claims, rewrite stale ones, replace overclaims with measured status, strip AI slop.
5. Re-run document control (`scripts/check_docs.py`) and code validators (ruff, black, pyright, cargo).

**Law:** Code is the source of truth. A document that contradicts code is defective and must be corrected or marked non-authoritative.

---

## 2. Findings Register

Severity: **P0** false claim that misleads operators or auditors · **P1** stale/incorrect technical fact · **P2** AI slop or unverified marketing · **P3** style/process.

### 2.1 P0 — False claims (must be removed or rewritten)

| ID | Location | False claim | Code evidence | Remediation |
|---|---|---|---|---|
| F-01 | `README.md` install | `pip install -r requirements.txt` | No `requirements.txt` exists. Install is `pyproject.toml` / `requirements-dev.txt` | Rewrite install to `pip install -e ".[dev]"` / `requirements-dev.txt` |
| F-02 | `README.md` config | "environment-driven settings" + env table (`SOMABRAIN_WM_SIZE`, `SOMABRAIN_HRR_DIM`, …) as authority | Settings law: `somabrain/settings/managed.py` — BrainSetting (DB) then Django; **never** `os.environ`. Secrets Vault-only (Covenant Art 26) | Replace with settings law + BrainSetting key table |
| F-03 | `README.md` compliance | "GDPR, HIPAA compliant", "SOC2-ready", "Audit logging (GDPR, HIPAA compliant)" | No certification artifacts. `docs/iso/SOMA-BR-SEC-001.md` says "Ready"/"In Progress", not certified | Rewrite to "controls mapped; not certified" |
| F-04 | `README.md` benchmarks | Measured table (Store 8ms/12k tps, Recall 15ms/5k tps, WM 2ms/50k tps, "Benchmarked on 32-core…") | No such benchmark run in repo. `tests/proofs/category_g/test_latency_slo.py` defines **SLO targets**, not published measurements | Replace with SLO targets and pointer to proof tests |
| F-05 | `README.md` diagram | "12M memories" as live capacity | Requirement target (`NFR-SCAL-001`), not a measured fact | Label as requirement target or remove |
| F-06 | `README.md` module table | `wm.py`, `salience.py` at claimed paths | `wm.py` does not exist (`somabrain/memory/wm/`); `salience.py` does not exist | Correct to real paths |
| F-07 | `README.md` badges | Python 3.11+, Django 5.0+, Build-Passing | `pyproject.toml`: `requires-python = ">=3.12,<3.13"`, `django>=5.1`. Build badge unverified | Correct versions; remove unverified build badge |
| F-08 | `AGENT.md` | `docs/technical/configuration_optimization.md` | Directory `docs/technical/` does not exist | Delete the reference; document presets in `AGENT.md` from `parameter_supervisor.py` |
| F-09 | `VIOLATIONS.md` | "VIBE Compliance Score: 100%", "Zero magic numbers", "All infrastructure settings from environment", "145 brain parameters" | Header of same file says NOT 100%. Settings law forbids env authority. BrainSetting DEFAULTS = **75** keys (`somabrain/brain_settings/models.py`) | Delete the false 100%/zero-magic/env block; record 75 keys and settings law |
| F-10 | `docs/USER_GUIDE.md` | `somabrain.quotas.QuotaManager`, `QuotaConfig` in `somabrain.config.Config` | Class is `TenantQuotaManager` in `somabrain/workers/quota_manager.py`. No `QuotaConfig`. Limits from `OUTBOX_TENANT_QUOTA_LIMIT` via `require_setting` | Correct names and configuration surface |
| F-11 | `docs/USER_GUIDE.md` | `SOMABRAIN_EMBED_DIM` default `256` | `somabrain/settings/cognitive.py:140` default **768** | Correct to 768 |
| F-12 | `docs/SRS_FULL.md` | `SOMABRAIN_HRR_DIM` default `1024`; `SOMABRAIN_EMBED_DIM` 256; `docs/technical/` tree | Code defaults: HRR 8192 (`BHDC_D`), embed 768. No `docs/technical/` | Correct defaults; mark `docs/technical/` sections obsolete |
| F-13 | `docs/iso/SOMA-BR-SEC-001.md` | GDPR ✅ Ready, HIPAA ✅ Ready | No formal certification or BAA in repo | Reword to "control mapping only; not certified" |
| F-14 | `docs/iso/SOMA-BR-ARCH-001.md` / `SOMA-BR-RISK-001.md` / `SOMA-BR-SRS-001.md` | "12M+ memories", "< 15ms" as achieved capacity | Requirement/SLO language is fine; presentation as achieved fact is not | Ensure all occurrences are labelled requirement or SLO target |

### 2.2 P1 — Stale / incorrect technical facts

| ID | Location | Issue | Remediation |
|---|---|---|---|
| S-01 | `README.md` Core Modules | Module names imply root-level modules | Map to real package paths (`somabrain/admin/cognitive/`, `somabrain/memory/wm/`, `somabrain/admin/core/`) |
| S-02 | `AGENT.md` "300+ parameters" | Unverified; BrainSetting DEFAULTS is 75 keys | State 75 registry keys + Django settings modules |
| S-03 | `docs/USER_GUIDE.md` env configuration tables | Multiple rows present ENV as the settings channel | Point every row at BrainSetting / Django settings / `managed_get` |
| S-04 | `docs/SOMABRAIN_ARCHITECTURE.md` env defaults table | Same ENV-as-authority pattern | Align with settings law |
| S-05 | Root math proofs | Already banner-marked NON-AUTHORITATIVE (DOC-A6) | Keep banner; ensure register status Obsolete/Archived is accurate |
| S-06 | `docs/ONBOARDING.md` | Mostly correct (Vault-only, `requirements-dev.txt`) | Spot-check remaining ENV examples |

### 2.3 P2 — AI slop / marketing (remove)

| ID | Location | Issue | Remediation |
|---|---|---|---|
| A-01 | `README.md` | Emoji walls, "cutting-edge research", star banner, "Built with 🧠", tagline | Strip to factual, ISO-acceptable prose; keep structure |
| A-02 | `README.md` badges | Decorative badges with unverifiable status | Remove Build-Passing; keep license and language badges only if accurate |
| A-03 | `docs/iso/SOMA-BR-AUDIT-001.md` scorecards | Letter grades without re-run evidence | Keep only if tied to dated audit method |
| A-04 | Code comments | "100% Django Ninja - VIBE compliant" marketing in `api/v1.py`, `config/urls.py` | Reduce to factual description |

### 2.4 P3 — Process

| ID | Issue | Remediation |
|---|---|---|
| P-01 | New remediation doc must enter `DOCUMENT-REGISTER.md` and pass `check_docs.py` | Register + DC header (done) |
| P-02 | Black reports 87 files unformatted; ruff 19 remaining findings | Run black + ruff fix; record residual |
| P-03 | Rust `cargo test` 17/17 green | Keep as evidence |
| P-04 | A2A claims must be logged | Claim appended to `CLAIMS.md`; ledger entry after work |

---

## 3. Remediation Phases

### Phase 1 — Delete or rewrite false claims (P0)
1. README install, config, compliance, benchmarks, diagram, badges, module table.
2. AGENT.md dead link and parameter count.
3. VIOLATIONS.md false "100% / zero magic / env settings / 145 params" block.
4. USER_GUIDE quota and embed-dimension facts.
5. SEC-001 compliance wording.
6. SRS_FULL stale defaults and `docs/technical/` tree.

### Phase 2 — Settings-law alignment (P1)
- Every doc that describes configuration must state: **Settings = Django + BrainSetting (administerable). Secrets = Vault only. Environment variables are not a settings or secrets channel.**
- Configuration tables must cite BrainSetting keys from `somabrain/brain_settings/models.py` DEFAULTS (75 keys as of 2026-10-09) or Django settings modules.

### Phase 3 — AI slop purge (P2)
- Remove unverifiable marketing claims, decorative status badges, and "100%" code comments.

### Phase 4 — Code validation (P2/P3)
```bash
.venv/bin/black somabrain/ scripts/ tests/
.venv/bin/ruff check somabrain/ scripts/ tests/ --fix
.venv/bin/pyright somabrain/          # record residual errors
cd rust_core && cargo test            # 17/17 required
python scripts/check_docs.py --strict # 43/43 + new doc
```

### Phase 5 — Register and ledger
- Add this document to `DOCUMENT-REGISTER.md`.
- Append A2A ledger row with results.

---

## 4. Acceptance Criteria

| # | Criterion | Evidence |
|---|---|---|
| 1 | No document claims `requirements.txt` exists | `rg requirements.txt README.md` empty (or only as negative note) |
| 2 | No document presents ENV as settings/secrets authority | Settings law banner in README, USER_GUIDE, AGENT, ARCHITECTURE |
| 3 | No GDPR/HIPAA/SOC2 "compliant" claim without "not certified" qualifier | SEC-001, README |
| 4 | No fabricated benchmark table | README points to SLO tests only |
| 5 | All referenced file paths exist | Path check pass |
| 6 | `check_docs.py` PASS with 0 findings | Script output |
| 7 | black/ruff clean or residual documented | Tool output |
| 8 | cargo test green | 17/17 |
| 9 | Register lists this document | DOCUMENT-REGISTER.md |

---

## 5. Out of Scope

- SomaAgent01 / SomaFractalMemory repos (coordinate via A2A `INBOX.md`).
- `somaAgent01/webui/` (partition rule: do not edit).
- Changing runtime behavior — this plan is documentation and comment accuracy only, plus formatting.

---

## 6. Residual Risk

| Risk | Mitigation |
|---|---|
| Docs still cite environment variable **names** for Django settings modules that read `django-environ` at boot | Clarify: env may bootstrap Django settings in dev; it is not the administerable settings channel and never holds secrets |
| External websites/badges | Removed or marked unverified |
| Historical VIOLATIONS narrative | Preserved as history with corrections, not deleted wholesale |

---

## 7. Execution Record (2026-10-09)

| Phase | Result | Evidence |
|---|---|---|
| Phase 1 — P0 false claims | **Done** | F-01..F-14 remediated in README, AGENT.md, VIOLATIONS.md, USER_GUIDE.md, SRS_FULL.md, SEC-001, PROD-001, ARCHITECTURE |
| Phase 2 — Settings-law alignment | **Done** | Settings law stated in README, USER_GUIDE, ARCHITECTURE; ENV-as-authority claims removed |
| Phase 3 — AI slop purge | **Done** | Emoji/marketing stripped from README; code comments factual |
| Phase 4 — Code validation | **Done** | black clean (412 files); ruff **All checks passed**; pyright 0 errors / 25 warnings; cargo test **17/17** |
| Phase 5 — Register + ledger | **Done** | `check_docs.py` **PASS 44/44 Compliant 0 findings**; QMS §8 row added; A2A ledger appended |

### Residual (tracked, not hidden)

| Item | Status |
|---|---|
| pyright 25 `reportUnsupportedDunderAll` warnings (`__all__` re-exports) | Pre-existing; low severity; not doc-claim defects |
| Historical narratives in `VIOLATIONS.md` and root math-proof files | Preserved with NON-AUTHORITATIVE / false-claim banners (DOC-A6 pattern) |
| SLO latency targets (8/15/2ms) | Targets only; re-measurement report required before any "measured" claim |
| `docs/technical/` references in older SRS sections | Marked obsolete; canonical map is `SOMA-BR-CONFIG-API-TEST-001.md` |

End of Document
