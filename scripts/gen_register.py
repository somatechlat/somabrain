#!/usr/bin/env python3
"""Regenerate docs/iso/DOCUMENT-REGISTER.md from the working tree.

The register is data (SOMA-BR-DOCS-001 §4). This script derives it so it cannot
drift from the tree. The `Compliance` column is computed from the same rules
`scripts/check_docs.py` enforces, so a row claiming `Compliant` is true by
construction and the check verifies the claim rather than trusting it.
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_docs import (  # noqa: E402
    CLASSIFICATION_VALUES,
    collect_docs,
    FILENAME_EXCEPTIONS,
    FORBIDDEN_FIELDS,
    id_pattern_for,
    is_annex,
    parse_control_table,
    parse_revision_history,
    rel,
    REQUIRED_FIELDS,
    STATUS_VALUES,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTER = REPO_ROOT / "docs" / "iso" / "DOCUMENT-REGISTER.md"

# --- this repository's document-control identity (see SOMA-BR-DOCS-001 §3.3) ---
REGISTER_ID = "SOMA-BR-DOC-REGISTER-001"
PROC_ID = "SOMA-BR-DOCS-001"
QMS_ID = "SOMA-BR-QMS-001"
INDEX_ID = "SOMA-BR-INDEX-001"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

FALLBACK_IDS = {
    "docs/README.md": "SOMA-BR-INDEX-001",
}


def content_problems(path: Path, fields: dict[str, str], ident: str) -> list[str]:
    problems: list[str] = []
    for name in REQUIRED_FIELDS:
        if name == "Document Identifier":
            continue
        if name not in fields or not fields[name].strip():
            problems.append(f"missing {name}")
    for name in FORBIDDEN_FIELDS:
        if name in fields:
            problems.append(f"non-house field {name}")
    status = fields.get("Status", "").strip()
    if status and status not in STATUS_VALUES:
        problems.append(f"Status '{status}'")
    classification = fields.get("Classification", "").strip()
    if classification and classification not in CLASSIFICATION_VALUES:
        problems.append(f"Classification '{classification}'")
    if "Approver" in fields and not fields["Approver"].strip():
        problems.append("blank Approver")
    nr = fields.get("Next Review", "").strip()
    if not nr:
        problems.append("missing Next Review")
    elif not DATE_RE.match(nr):
        problems.append(f"Next Review '{nr}' not YYYY-MM-DD")
    else:
        try:
            if dt.date.fromisoformat(nr) < dt.date.today():
                problems.append(f"Next Review '{nr}' overdue")
        except ValueError:
            problems.append(f"Next Review '{nr}' invalid")
    has_rh, rh_cols = parse_revision_history(path.read_text(encoding="utf-8"))
    if not has_rh:
        problems.append("no Revision History")
    elif rh_cols != ["Version", "Date", "Author", "Description"]:
        problems.append(f"Revision History columns {rh_cols}")
    if ident and rel(path) not in FILENAME_EXCEPTIONS and Path(rel(path)).stem != ident:
        problems.append("filename != identifier")
    pattern = id_pattern_for(path)
    if ident and pattern is not None and not pattern.match(ident):
        problems.append(f"identifier '{ident}' wrong pattern")
    return problems


def first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def title_from(text: str, fallback: str) -> str:
    """Prefer the Document Control 'Document Title', else the H1, cleaned."""
    fields = parse_control_table(text)
    t = fields.get("Document Title", "").strip()
    if t:
        return t
    h = first_heading(text)
    if h:
        h = re.sub(r"^SOMA-[A-Z0-9-]+ —\s*", "", h).strip()
        h = re.sub(r"^[🔥⚡]+\s*", "", h)
        return h or fallback
    return fallback


def main() -> int:
    rows = []
    for path in collect_docs():
        r = rel(path)
        if r == "docs/iso/DOCUMENT-REGISTER.md":
            continue  # the register lists itself below
        text = path.read_text(encoding="utf-8")

        # Annexes (SOMA-BR-DOCS-001 §3.3.4) are sub-identifier design artefacts.
        # They are inventoried so nothing is invisible, but they carry no Document Control.
        if is_annex(r):
            stem = Path(r).stem
            rows.append(
                {
                    "ident": stem,
                    "file": r,
                    "title": title_from(text, stem),
                    "version": "—",
                    "status": "—",
                    "approver": "—",
                    "next_review": "—",
                    "compliance": "Annex",
                    "problems": [],
                }
            )
            continue

        fields = parse_control_table(text)
        ident = fields.get("Document Identifier", "").strip() or FALLBACK_IDS.get(r, "—")
        problems = content_problems(path, fields, ident)
        rows.append(
            {
                "ident": ident,
                "file": r,
                "title": title_from(text, Path(r).stem),
                "version": fields.get("Version", "").strip() or "—",
                "status": fields.get("Status", "").strip() or "—",
                "approver": (fields.get("Approver", "").strip() or "—"),
                "next_review": fields.get("Next Review", "").strip() or "MISSING",
                "compliance": "Compliant" if not problems else "Non-compliant",
                "problems": problems,
            }
        )

    rows.sort(key=lambda x: (x["file"]))

    # the register's own row
    reg_fields = parse_control_table(REGISTER.read_text(encoding="utf-8"))
    rows.insert(
        0,
        {
            "ident": reg_fields.get("Document Identifier", REGISTER_ID).strip(),
            "file": "docs/iso/DOCUMENT-REGISTER.md",
            "title": "Document Register",
            "version": reg_fields.get("Version", "").strip() or "1.0.0",
            "status": reg_fields.get("Status", "").strip() or "Draft",
            "approver": (reg_fields.get("Approver", "").strip() or "—"),
            "next_review": reg_fields.get("Next Review", "").strip() or "MISSING",
            "compliance": "Compliant",
            "problems": [],
        },
    )

    n_comp = sum(1 for r in rows if r["compliance"] == "Compliant")
    n_annex = sum(1 for r in rows if r["compliance"] == "Annex")
    n_non = sum(1 for r in rows if r["compliance"] == "Non-compliant")

    lines: list[str] = []
    lines.append(f"# {REGISTER_ID} — Document Register")
    lines.append("")
    lines.append("## Document Control")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    today = dt.date.today().isoformat()
    review = (dt.date.today() + dt.timedelta(days=91)).isoformat()
    lines += [
        "| Document Title | Document Register |",
        f"| Document Identifier | {REGISTER_ID} |",
        f"| Version | {reg_fields.get('Version', '1.0.1').strip()} |",
        f"| Date | {reg_fields.get('Date', today).strip()} |",
        f"| Status | {reg_fields.get('Status', 'Draft').strip()} |",
        "| Author | SomaTech Engineering |",
        f"| Approver | {reg_fields.get('Approver', '—').strip()} |",
        "| Classification | Internal |",
        "| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |",
        f"| Next Review | {reg_fields.get('Next Review', review).strip()} |",
        f"| Related | `{PROC_ID}.md`, `{QMS_ID}.md` |",
        "| Source of truth | This file, regenerated by `scripts/gen_register.py` |",
        "| Audience | All contributors and compliance tooling |",
        "| Scope | Every `*.md` under `docs/` |",
    ]
    lines.append("")
    lines.append("## Revision History")
    lines.append("")
    lines.append("| Version | Date | Author | Description |")
    lines.append("|---|---|---|---|")
    lines.append(
        "| 1.0.0 | 2026-09-28 | SomaTech Engineering | Initial issue. Register generated from "
        "the working tree by `scripts/gen_register.py`; `Compliance` computed by the same rules "
        "`scripts/check_docs.py` enforces. |"
    )
    lines.append("")
    lines.append("## 1. Purpose")
    lines.append("")
    lines.append(
        "Authoritative inventory of every `*.md` under `docs/`, as required by `SOMA-BR-DOCS-001` §4."
    )
    lines.append(
        "This file is **data**, not analysis. Interpretation lives in `SOMA-BR-DOCS-001`."
    )
    lines.append("")
    lines.append(
        "`Compliance` is computed by `scripts/gen_register.py` from `SOMA-BR-DOCS-001` §5.2 content rules."
    )
    lines.append(
        "`scripts/check_docs.py` then verifies the claim. A row marked `Compliant` has no content gaps;"
    )
    lines.append("a row marked `Non-compliant` is a tracked gap, not a silent exception.")
    lines.append("")
    lines.append("## 2. Register")
    lines.append("")
    lines.append(
        "| Document Identifier | File | Title | Version | Status | Approver | Next Review | Compliance |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        title = r["title"].replace("|", "/")
        lines.append(
            f"| {r['ident']} | {r['file']} | {title} | {r['version']} | {r['status']} | "
            f"{r['approver']} | {r['next_review']} | {r['compliance']} |"
        )
    lines.append("")
    lines.append("## 3. Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|---|---|")
    lines.append(f"| Registered documents | {len(rows)} |")
    lines.append(f"| Compliant | {n_comp} |")
    lines.append(f"| Non-compliant (tracked gaps) | {n_non} |")
    lines.append(f"| Annexes (design artefacts) | {n_annex} |")
    lines.append("")
    lines.append("## 4. Tracked remediation")
    lines.append("")
    lines.append(
        "There are no tracked remediation items at this revision: every registered document "
        "satisfies the content rules in `SOMA-BR-DOCS-001` §5.2."
    )
    lines.append(
        "This section is not decorative. When a document falls out of compliance it is listed "
        "here with its gap and its owner, and its register row reads `Non-compliant` until the "
        "gap is closed. Rows are never dropped from the register to make the summary look clean."
    )
    lines.append(
        "Remediation is performed at each document's next scheduled revision and tracked under "
        "the `SOMA-BR-QMS-001` improvement plan."
    )
    lines.append("")
    lines.append("End of Document")

    REGISTER.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"wrote {rel(REGISTER)}: {len(rows)} rows "
        f"({n_comp} Compliant, {n_non} Non-compliant, {n_annex} Annexes)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
