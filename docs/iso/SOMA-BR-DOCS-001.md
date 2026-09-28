# SOMA-BR-DOCS-001 — Document Control and Traceability Procedure

## Document Control

| Field | Value |
|---|---|
| Document Title | Document Control and Traceability Procedure |
| Document Identifier | SOMA-BR-DOCS-001 |
| Version | 1.0.0 |
| Date | 2026-09-28 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2026-12-28 |
| Related | `SOMA-BR-QMS-001.md`, `docs/VIBE_RULES.md`, `docs/iso/DOCUMENT-REGISTER.md` |
| Source of truth | This document, `docs/iso/DOCUMENT-REGISTER.md`, `scripts/check_docs.py` |
| Audience | All engineering contributors and any agent acting on this repository |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-09-28 | SomaTech Engineering | Initial issue for somabrain. Establishes mandatory document control, identifier scheme, register and automated compliance check. Derived from the somaAgent01 procedure of the same name and re-scoped to this repository's actual tree, filename exceptions and tooling. |

## Normative References

| ID | Reference | Role |
|---|---|---|
| N-1 | SOMA-BR-QMS-001 | Quality management system; its Document Reference Matrix is the QMS registry |
| N-2 | ISO 9001:2015 | Clause 7.5 Documented information — control of documents and records |
| N-3 | docs/VIBE_RULES.md | Standing engineering rules for this repository |

---

## 1. Purpose and Scope

### 1.1 Purpose

This procedure makes every documented artefact in `docs/` **controlled**: identified, registered, versioned, traceable and reviewable. It exists because ISO 9001:2015 clause 7.5 requires documented information to be controlled, and because this repository previously had **no automated enforcement** of that control.

Verification of the prior state (2026-09-28):

| Check | Result before this procedure |
|---|---|
| Document-control checker in `scripts/` | none — `check_docs.py` did not exist |
| Document register | none |
| `docs-check` / `docs-register` Make targets | none |
| `Next Review` field across the suite | absent from every document |
| CI job enforcing document control | none |

This procedure closes that gap.

### 1.2 Scope

Applies to **every** `*.md` file under `docs/`, without exception. The tree has three levels:

| Directory | Holds | Tier |
|---|---|---|
| `docs/` | Repository guides, index, coding rules | Guideline |
| `docs/iso/` | Controlled QMS-tier documents — the strictest tier | QMS |
| `docs/project/` | Project records: plans, specifications, matrices | Project |

Files outside `docs/` (source code, tests, infrastructure, the root `README.md`) are out of scope for registration, but any document they reference from `docs/` must itself be registered.

### 1.3 Out of Scope

- Source code comments and docstrings
- Generated documentation output (for example Sphinx `docs/build/`)
- Git commit messages and pull request bodies
- Third-party vendored documentation

---

## 2. Normative Requirements

Requirements use **SHALL** (mandatory) and **SHALL NOT** (prohibited).

| ID | Requirement | Priority | Source | Verification |
|---|---|---|---|---|
| REQ-DOCS-001 | Every `*.md` under `docs/` **SHALL** appear in `docs/iso/DOCUMENT-REGISTER.md` with a valid Document Identifier. Unregistered files **SHALL** fail the compliance check. | Must | N-2, 1.1 | Inspection (`scripts/check_docs.py`) |
| REQ-DOCS-002 | Every controlled document **SHALL** open with a `## Document Control` table containing, at minimum, the fields listed in §3.1. | Must | N-2 | Inspection |
| REQ-DOCS-003 | Every controlled document **SHALL** contain a `## Revision History` table with the exact columns `Version`, `Date`, `Author`, `Description`. | Must | N-2 | Inspection |
| REQ-DOCS-004 | Every controlled document **SHALL** carry a `Next Review` date. Documents past that date **SHALL** be flagged by the check. | Must | N-2 | Inspection |
| REQ-DOCS-005 | The `Approver` field **SHALL** always be present. When unsigned its value **SHALL** be `—`. A blank or missing Approver is non-compliant. | Must | N-2 | Inspection |
| REQ-DOCS-006 | `Status` **SHALL** be one of `Draft`, `In Review`, `Approved`, `Obsolete`. `Classification` **SHALL** be one of `Internal`, `Confidential`. | Must | N-1 | Inspection |
| REQ-DOCS-007 | Any edit to a document whose Status is `Approved` **SHALL** bump its `Version`, append a `Revision History` row, and record what changed. Approved content **SHALL NOT** be silently overwritten. | Must | N-2 | Analysis (diff review) |
| REQ-DOCS-008 | Identifiers **SHALL** match the patterns in §3.3. An identifier that does not match its declared kind **SHALL** fail the compliance check. | Must | N-1 | Inspection |
| REQ-DOCS-009 | The register **SHALL** agree with the QMS Document Reference Matrix on the set of QMS-tier identifiers. Divergence **SHALL** fail the compliance check. | Must | N-1 | Inspection |
| REQ-DOCS-010 | Requirements-bearing documents **SHALL** include a traceability matrix mapping each requirement identifier to its verification method and status. | Must | N-2 | Inspection |
| REQ-DOCS-011 | Evidence claims **SHALL** cite `file:line` or an equivalent reproducible reference. Unsourced assertions **SHALL NOT** be presented as verified fact. | Must | N-3 | Inspection |
| REQ-DOCS-012 | A document **SHALL NOT** claim a capability is complete without the evidence named in its acceptance criteria. | Must | N-3 | Analysis |
| REQ-DOCS-013 | The compliance check **SHALL** be runnable locally (`make docs-check`) and in continuous integration. | Must | this procedure | Test |
| REQ-DOCS-014 | Documents that do not yet comply **SHALL** be listed as tracked findings. They **SHALL NOT** be silently exempted from the register. | Must | this procedure | Inspection |
| REQ-DOCS-015 | A document **SHALL NOT** describe a capability as available when the repository does not implement it. Unavailable capabilities **SHALL** state their blocking reason. Placeholder copy such as "coming soon" **SHALL NOT** appear as a specification value. | Must | N-3 | Inspection |

---

## 3. Document Control Requirements

### 3.1 Mandatory Document Control fields

Every controlled document opens with a `## Document Control` table using these field names **exactly**. The names are not interchangeable with synonyms.

| Field | Required | Allowed values | Notes |
|---|---|---|---|
| `Document Title` | yes | free text | Human-readable title |
| `Document Identifier` | yes | per §3.3 | Matches the filename stem, except where §3.3.3 waives it |
| `Version` | yes | `x.y.z` semver | Bumped per REQ-DOCS-007 |
| `Date` | yes | `YYYY-MM-DD` | Document issue date |
| `Status` | yes | `Draft` \| `In Review` \| `Approved` \| `Obsolete` | Closed set |
| `Author` | yes | free text | `SomaTech Engineering` by convention |
| `Approver` | yes | free text or `—` | Never blank, never omitted |
| `Classification` | yes | `Internal` \| `Confidential` | Closed set. This is the confidentiality marking; the field is **not** named "Confidentiality" |
| `ISO Reference` | yes | free text | Governing standard(s), or `—` where the document cites none |
| `Next Review` | yes | `YYYY-MM-DD` | Review due date |
| `Related` | no | document list | Cross-references |
| `Source of truth` | no | path or description | Authoritative artefact |
| `Audience` | no | free text | Intended readers |
| `Scope` | no | free text | Boundary of applicability |

**Fields that do not exist in this house style and SHALL NOT be invented:** `Effective Date`, `Distribution`, `Doc ID`, `Document ID`, `Revision` (use `Version`), `Confidentiality` (use `Classification`).

### 3.2 Revision History

Immediately after Document Control:

```markdown
## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-09-28 | SomaTech Engineering | Initial issue. |
```

Columns are exactly `Version`, `Date`, `Author`, `Description`. The heading is `## Revision History` — an `h2`, not `h3`. Every released version has one row. Rows are never deleted.

### 3.3 Identifier scheme

Every controlled document is named **by its Document Identifier**:

```
SOMA-<DOMAIN>-<TYPE>-<NNN>.md
         │       │      └── zero-padded sequence within (DOMAIN, TYPE)
         │       └── short uppercase token for the document's subject
         └── the domain token
```

`<TYPE>` and `<TOPIC>` are uppercase `A–Z` and `0–9` only. `<NNN>` is exactly three digits.

The **filename stem is the Document Identifier**. This is rule **C-12**.

#### 3.3.1 Domain tokens in this repository

| Domain | Meaning | Location | Pattern | Example |
|---|---|---|---|---|
| `BR` | somabrain ISO-series document | `docs/iso/` | `SOMA-BR-<TYPE>-<NNN>` | `SOMA-BR-QMS-001` |
| `BR` + `GUIDE` | Named repository guide under `docs/` | `docs/` | `SOMA-BR-GUIDE-<TOPIC>-<NNN>` | `SOMA-BR-GUIDE-USER-001` |
| `BR` + `INDEX` | The documentation tree index | `docs/` | `SOMA-BR-INDEX-<NNN>` | `SOMA-BR-INDEX-001` |
| `ARCH`, `FEAT`, `MOD`, `UI` | Project record | `docs/project/` | `SOMA-<TYPE>-<TOPIC>-<NNN>` | `SOMA-MOD-SPEC-001` |
| `BR` + `EXEC` | Project execution plan | `docs/project/` | `SOMA-BR-<TYPE>-<NNN>` | `SOMA-BR-EXEC-001` |

The identifier's domain token records what the document **is**, not only where it sits. A `SOMA-BR-*` identifier outside `docs/iso/` is permitted for named project records and guides, and is listed in the register; it is **not** a QMS document and does not appear in the Document Reference Matrix (see §5.2 rule C-10).

#### 3.3.2 Filename exceptions (documented waivers)

These files carry names that predate this procedure or that a platform convention requires. Their identifiers are recorded in the register, and rule C-12 is waived for exactly these paths:

| File | Document Identifier | Why it is an exception |
|---|---|---|
| `docs/iso/DOCUMENT-REGISTER.md` | `SOMA-BR-DOC-REGISTER-001` | Fixed machine contract — `scripts/check_docs.py` and `scripts/gen_register.py` locate the register by this path. |
| `docs/README.md` | `SOMA-BR-INDEX-001` | The documentation tree index. `README.md` is the universal repository-index convention and is read before any identifier is known. |
| `docs/SOMABRAIN_ARCHITECTURE.md` | `SOMA-BR-GUIDE-ARCH-001` | Long-standing guide name referenced by external material. |
| `docs/SomabrainGMD.md` | `SOMA-BR-GUIDE-GMD-001` | Long-standing guide name referenced by external material. |
| `docs/SRS_FULL.md` | `SOMA-BR-GUIDE-SRS-001` | Long-standing guide name referenced by external material. |
| `docs/OPS_MANUAL.md` | `SOMA-BR-GUIDE-OPS-001` | Long-standing guide name referenced by external material. |
| `docs/ONBOARDING.md` | `SOMA-BR-GUIDE-ONBOARD-001` | Long-standing guide name referenced by external material. |
| `docs/CONTRIBUTING.md` | `SOMA-BR-GUIDE-CONTRIB-001` | `CONTRIBUTING.md` is the platform convention for contribution guidance. |
| `docs/USER_GUIDE.md` | `SOMA-BR-GUIDE-USER-001` | Long-standing guide name referenced by external material. |
| `docs/THE-SOMA-COVENANT.md` | `SOMA-BR-GUIDE-COVENANT-001` | Long-standing guide name referenced by external material. |
| `docs/VIBE_RULES.md` | `SOMA-BR-GUIDE-VIBE-001` | Standing rules file, referenced by name across the codebase. |

This list is closed. A new exception requires amending this table **and** `FILENAME_EXCEPTIONS` in `scripts/check_docs.py` in the same change, so that the waiver is visible in the controlled document and enforced by the tool.

#### 3.3.3 Annexed design artefacts

No annex tier exists in this repository today: there is no `docs/design/mockups/` tree.

`scripts/check_docs.py` nevertheless carries the reserved rules for one. If that directory appears, its files are annexes rather than standalone controlled documents: they are named by sub-identifier (`UI-S-<NN>-<slug>.md`, `UI-X-<NN>-<slug>.md`), are inventoried in the register with `Compliance = Annex`, and **SHALL NOT** carry their own `## Document Control` or `## Revision History` table. Rules C-03 … C-09 and C-12 do not apply to an annex; C-01 and C-11 do.

Until that directory exists, the annex rules match nothing and are inert.

### 3.4 Status transitions

```
Draft ──► In Review ──► Approved ──► Obsolete
  ▲                        │
  └────── on edit ─────────┘
```

An `Approved` document that is edited **SHALL** record the change in `Revision History` with a bumped `Version`. Where the edit changes meaning rather than correcting presentation, `Status` **SHALL** return to `Draft`.

---

## 4. The Document Register

`docs/iso/DOCUMENT-REGISTER.md` is the authoritative inventory. It **SHALL** list every `*.md` under `docs/` with:

| Column | Content |
|---|---|
| `Document Identifier` | per §3.3 |
| `File` | repository-relative path |
| `Title` | document title |
| `Version` | current version |
| `Status` | current status |
| `Approver` | approver or `—` |
| `Next Review` | review date or `MISSING` |
| `Compliance` | `Compliant` \| `Non-compliant` \| `Annex` |

The register is **derived data**, regenerated by `scripts/gen_register.py`. It **SHALL NOT** be hand-maintained and **SHALL NOT** contain prose analysis. Interpretation lives in this procedure.

---

## 5. Automated Compliance Check

### 5.1 Tooling

| Artefact | Location | Role |
|---|---|---|
| Check script | `scripts/check_docs.py` | Parses the register and every `docs/**/*.md`; emits findings; exits non-zero on failure |
| Register generator | `scripts/gen_register.py` | Regenerates `docs/iso/DOCUMENT-REGISTER.md` from the tree |
| Make targets | `make docs-check` / `make docs-register` | Local entry point. The existing `make docs` target builds Sphinx HTML and is unrelated. |

### 5.2 Check rules

The script **SHALL** fail the build on any of:

| Rule | Condition |
|---|---|
| C-01 | A `docs/**/*.md` file is not listed in the register |
| C-02 | A registered file does not exist on disk |
| C-03 | A controlled document lacks a `## Document Control` table |
| C-04 | A required field from §3.1 is missing or empty |
| C-05 | `Status` is outside the closed set |
| C-06 | `Classification` is outside the closed set |
| C-07 | `Approver` is blank (an em dash `—` is valid) |
| C-08 | `Next Review` is missing, malformed, or in the past |
| C-09 | A `## Revision History` table is missing or has the wrong columns |
| C-10 | The register and the QMS Document Reference Matrix disagree on the set of **QMS-tier identifiers** — the documents under `docs/iso/` |
| C-11 | A `Document Identifier` does not match the §3.3 pattern for its file location |
| C-12 | A document's filename stem is not its `Document Identifier` (§3.3.2 waivers excepted) |

**Scope of C-10.** The Document Reference Matrix in `SOMA-BR-QMS-001` is the registry of the **QMS document set**: every document under `docs/iso/`. Guides under `docs/` and project records under `docs/project/` are registered in `DOCUMENT-REGISTER.md` but are not QMS documents, so they are not listed in the matrix and C-10 does not expect them there.

The script **SHALL** also report, without failing the build, documents that are registered but non-compliant, so that gaps remain visible rather than hidden.

### 5.3 Failure output

Findings are printed one per line as `TAG | RULE | file | message`, where `TAG` is `FAIL` or `WARN`. A summary reports documents scanned, registered, failing findings, warnings and non-compliant count. Exit code is `0` only when there are no failing rules; `--strict` additionally fails when any registered document is non-compliant.

---

## 6. Traceability

### 6.1 Chain

Requirements-bearing documents trace through:

```
REQ-* ──► document section ──► named evidence (file:line or command) ──► verification status
```

The matrix uses the house format:

```markdown
| Requirement Category | Count | Implemented | Tested | Coverage |
|---|---|---|---|---|
| … | … | … | … | … |
| **TOTAL** | **…** | **…** | **…** | **…** |
```

### 6.2 Bidirectionality

- Every `REQ-*` **SHALL** name its verification method and current status.
- A requirement with no evidence is `NOT YET`, not omitted.
- Evidence that cannot be reproduced **SHALL NOT** be recorded as verified.

---

## 7. Relationship to Other Rules

| Document | Relationship |
|---|---|
| `SOMA-BR-QMS-001` Document Reference Matrix | QMS registry. This procedure is registered there. The matrix and `DOCUMENT-REGISTER.md` **SHALL** agree on the QMS-tier set (REQ-DOCS-009). |
| `docs/VIBE_RULES.md` | Standing day-to-day engineering rules. It **SHALL** reference this procedure rather than restate it. |

---

## 8. Acceptance Criteria

| Criterion | Target | Current |
|---|---|---|
| `scripts/check_docs.py` exists and exits non-zero on a violation | yes | Met |
| `make docs-check` runs the check | yes | Met |
| `make docs-register` regenerates the register | yes | Met |
| Register lists every `docs/**/*.md` | 100% | Met |
| Every controlled document has Document Control and Revision History | 100% | Met |
| Every controlled document has `Approver` and `Next Review` | 100% | Met |
| Register and QMS Document Reference Matrix agree | zero divergence | Met |
| Gaps listed as tracked findings, not silently exempted | yes | Met |

---

## 9. Document Reference Matrix

This procedure is registered in `SOMA-BR-QMS-001`'s Document Reference Matrix and in `docs/iso/DOCUMENT-REGISTER.md`.

| Document | Identifier | ISO Reference | File |
|---|---|---|---|
| Document Control and Traceability Procedure | SOMA-BR-DOCS-001 | ISO 9001:2015 — Quality Management Systems — Requirements | `docs/iso/SOMA-BR-DOCS-001.md` |

End of Document
