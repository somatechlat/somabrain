# SOMA-BR-ISO-CERT-001 — ISO Documentation Certification Report

## Document Control

| Field | Value |
|---|---|
| Document Title | ISO Documentation Certification Report |
| Document Identifier | SOMA-BR-ISO-CERT-001 |
| Version | 1.0.0 |
| Date | 2026-10-09 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2026-12-28 |
| Related | `SOMA-BR-DOCS-001.md`, `SOMA-BR-QMS-001.md`, `DOCUMENT-REGISTER.md`, `scripts/check_docs.py` |
| Source of truth | `scripts/check_docs.py` + `scripts/gen_register.py` output |
| Audience | Quality assurance, auditors, Product Owner |
| Scope | Document control, tracking, and ISO standard mapping for `somabrain` and `somafractalmemory` |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-10-09 | SomaTech Engineering | Initial certification of the organized documentation suite against ISO 9001:2015 §7.5 and the house procedure SOMA-BR-DOCS-001. |

---

## 1. Certification statement

This report certifies that the **documented information** of the repositories below is under **document control** as required by ISO 9001:2015 clause 7.5 and the house procedure `SOMA-BR-DOCS-001`, as of **2026-10-09**.

| Repository | Register | Automated gate | Result |
|---|---|---|---|
| `somabrain` | `docs/iso/DOCUMENT-REGISTER.md` (47 rows) | `scripts/check_docs.py` | **PASS — 47/47 Compliant, 0 findings** |
| `somafractalmemory` | `docs/iso/DOCUMENT-REGISTER.md` (29 rows) | `scripts/check_docs.py` | **PASS — 29/29 Compliant, 0 findings** |

**Combined: 76 controlled documents, 0 non-compliant, 0 failing findings.**

> **Scope of certification:** Document *control* (identity, version, status, approver, classification, ISO reference, review date, register membership, QMS matrix agreement). This is **not** ISO 9001 organizational certification and is **not** a claim that products are certified to ISO 27001 / 25010 / 42010 — those are cited as *reference frameworks* on individual documents.

---

## 2. ISO standard mapping (all standards used)

| Standard | Role in this QMS | Documents citing it |
|---|---|---|
| **ISO 9001:2015** | Governing QMS — especially **§7.5 Documented information** | QMS-001, DOCS-001, DOC-REGISTER, most guides and plans |
| **ISO/IEC 42010:2011** | Architecture description | ARCH-001, ARCH-TRUTH-001 |
| **ISO/IEC/IEEE 29148:2018** | Requirements engineering | SRS-001 |
| **ISO/IEC/IEEE 12207:2017** | Software life cycle processes | SDP-001, MATH-TRUTH-001 |
| **ISO/IEC/IEEE 16085:2006** | Risk management (adapted for V&V) | VV-001 |
| **ISO/IEC 27001:2022** | Information security management | SEC-001 |
| **ISO/IEC 25010:2011** | Software quality / maintainability | PROD-001, DEBT-001 |
| **ISO 31000:2018** | Risk management guidelines | RISK-001 |
| **ISO 19011:2018** | Auditing management systems | AUDIT-001 |
| **ISO 9241-210:2019** | Human-centred design (UI docs) | UI-SPEC-001, UI-UX-001, UI-MODEL-ADMIN-001, UI-FIELD-PARITY-001 |

---

## 3. ISO 9001:2015 §7.5 clause evidence

| Clause | Requirement | Evidence | Status |
|---|---|---|---|
| 7.5.1 a | Documented info appropriate & available | `DOCUMENT-REGISTER.md` lists every `docs/**/*.md` | **PASS** |
| 7.5.1 b | Suitable for identification | Identifier = filename stem `SOMA-*-###` (C-12); required Document Control fields | **PASS** |
| 7.5.2 a | Suitable format & media | Markdown, versioned in Git | **PASS** |
| 7.5.2 b | Review & approval | `Status` + `Approver` fields; Approved when an approver is named | **PASS** |
| 7.5.3 a | Available where needed | Index `docs/README.md` (SOMA-BR-INDEX-001) by tier | **PASS** |
| 7.5.3 b | Adequately protected | Classification `Internal` \| `Confidential` | **PASS** |
| 7. Control of documented info | Version control, changes, retention | `Version`, `Revision History`, `Next Review`; register regenerated from tree | **PASS** |
| Automated enforcement | Control cannot silently drift | `check_docs.py` rules C-01..C-12 (47/47 + 29/29) | **PASS** |
| QMS cross-reference | Register ↔ QMS matrix agree | C-10: `SOMA-BR-QMS-001` Document Reference Matrix | **PASS** |
| Code is source of truth | Docs must match code | Truth sync 2026-10-09 (doc-updater); honesty banners on math proofs | **PASS** |

---

## 4. Document tracking (how control is maintained)

| Mechanism | Owner | Cadence |
|---|---|---|
| `scripts/gen_register.py` | Engineering | On every docs change |
| `scripts/check_docs.py` | Engineering / CI-ready | On every docs change (`--strict` for gate) |
| `DOCUMENT-REGISTER.md` | Regenerated data (not hand-edited) | Continuous |
| `SOMA-BR-QMS-001` Document Reference Matrix | QA | On QMS-tier document set change |
| `Next Review` field | Document owner | ≤ 6 months per document |
| Management review | VP Engineering | Semi-annual (QMS-001) |

---

## 5. Organizational structure (post-organization)

| Tier | Location | Count (somabrain) |
|---|---|---|
| QMS | `docs/iso/` | 23 (incl. register + this certificate) |
| Guideline | `docs/` root | 9 |
| Project | `docs/project/` | 10 |
| A2A records | `docs/plans/` | 5 |
| **Total registered** | | **47** |

`somafractalmemory` mirrors the same tiers under its own `SOMA-SFM-*` identifiers (29 documents).

---

## 6. Findings closed this certification cycle

| # | Finding | Resolution |
|---|---|---|
| 1 | Docs claimed DEBT-008 open / Python fallback | Marked CLOSED; Rust sole authority documented |
| 2 | Optional-path / dual-mode language in docs | Removed — code has zero optional paths |
| 3 | Violet brand tokens in UI docs | Corrected to `#FF4D00` / `#FF7A3D` / `#E64500` |
| 4 | Math proofs claimed 100% / guaranteed | Honesty banners + test citations |
| 5 | Stale `Last updated: 2026-04-01` on index | Removed; versioned revision history only |
| 6 | Index did not list ISO tier or tooling | Rebuilt as tiered index with register + gate commands |

---

## 7. Residual (tracked, not silent)

| Item | Disposition |
|---|---|
| `SOMA-ARCH-REDESIGN-001` illustrative `return []` sketches | Design sketch — not production; annotated in remediation plan |
| Historical DEBT-008 "what docs claimed" sections | Intentional audit trail |
| Learning math proof worked examples (Python algebra) | Banner only; live engine is `rust_math.py` / `somabrain_rs` |
| External ISO organizational certification | **Not claimed** — this is document-control conformity only |

---

## 8. Conclusion

**CERTIFIED for document control (ISO 9001:2015 §7.5 / SOMA-BR-DOCS-001):**

- Every `docs/**/*.md` file is identified, registered, versioned, status-controlled, classified, and review-dated.
- Automated tools prove the claim (`check_docs.py` PASS 47/47 and 29/29).
- QMS Document Reference Matrix agrees with the register.
- Documentation is organized by ISO tier and indexed at `docs/README.md`.
- Code is the source of truth; docs were truth-synced on 2026-10-09.

**Signature block (for Product Owner acceptance):**

| Role | Name | Date | Accept / Reject |
|---|---|---|---|
| Author | SomaTech Engineering | 2026-10-09 | Accept |
| QA / Reviewer | | | |
| Product Owner | | | |
