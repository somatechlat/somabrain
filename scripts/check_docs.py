#!/usr/bin/env python3
"""Document compliance check for somabrain.

Implements SOMA-BR-DOCS-001 §5.2 rules C-01..C-12.

Usage:
    python scripts/check_docs.py            # check and report
    python scripts/check_docs.py --strict   # also fail on non-compliant registered docs

Exit codes:
    0  no failing rules
    1  one or more failing rules
    2  tooling error (register or QMS matrix unreadable)
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
REGISTER_PATH = DOCS_DIR / "iso" / "DOCUMENT-REGISTER.md"
QMS_PATH = DOCS_DIR / "iso" / "SOMA-BR-QMS-001.md"

# SOMA-BR-DOCS-001 §3.1
REQUIRED_FIELDS = [
    "Document Title",
    "Document Identifier",
    "Version",
    "Date",
    "Status",
    "Author",
    "Approver",
    "Classification",
    "ISO Reference",
    "Next Review",
]

OPTIONAL_FIELDS = ["Related", "Source of truth", "Audience", "Scope"]
FORBIDDEN_FIELDS = ["Effective Date", "Distribution", "Doc ID", "Document ID", "Confidentiality"]

STATUS_VALUES = {"Draft", "In Review", "Approved", "Obsolete"}
CLASSIFICATION_VALUES = {"Internal", "Confidential"}

# SOMA-BR-DOCS-001 §3.3 — the filename is the identifier (C-12) in this repository.
# Every controlled document uses the repo's own SOMA-* namespace; the fixed machine
# contracts that cannot carry it are listed in FILENAME_EXCEPTIONS below.
_ID = re.compile(r"^SOMA-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}$")
ID_PATTERNS = {
    "docs/iso": _ID,
    "docs/project": _ID,
    "docs": _ID,
}

# SOMA-BR-DOCS-001 §3.3 filename exceptions — fixed machine/global contracts.
FILENAME_EXCEPTIONS = {
    "docs/iso/DOCUMENT-REGISTER.md",
    "docs/README.md",
    "docs/SOMABRAIN_ARCHITECTURE.md",
    "docs/SomabrainGMD.md",
    "docs/SRS_FULL.md",
    "docs/OPS_MANUAL.md",
    "docs/ONBOARDING.md",
    "docs/CONTRIBUTING.md",
    "docs/USER_GUIDE.md",
    "docs/THE-SOMA-COVENANT.md",
    "docs/VIBE_RULES.md",
}

# SOMA-BR-DOCS-001 §3.3.3 — annexed design artefacts. Mockups carry a sub-identifier
# (UI-S-NN, UI-X-NN) rather than a controlled-document identifier. They are inventoried by
# the suite's controlled INDEX, not by a Document Control table of their own.
ANNEX_PREFIX = "docs/design/mockups/"
ANNEX_ID_RE = re.compile(r"^UI-[SX]-\d{2}-[a-z0-9-]+$")


def is_annex(rel_path: str) -> bool:
    """True for annexed design artefacts (see SOMA-BR-DOCS-001 §3.3.3)."""
    return rel_path.startswith(ANNEX_PREFIX)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass
class Finding:
    rule: str
    path: str
    message: str
    #: Register-integrity rules always fail. Content rules fail only when the
    #: register claims the document is 'Compliant' (see SOMA-BR-DOCS-001 §5.2).
    integrity: bool = True
    warn_only: bool = False

    @property
    def failing(self) -> bool:
        return self.integrity and not self.warn_only


@dataclass
class DocControl:
    path: Path
    fields: dict[str, str] = field(default_factory=dict)
    forbidden: list[str] = field(default_factory=list)
    has_revision_history: bool = False
    revision_columns: list[str] = field(default_factory=list)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def parse_control_table(text: str) -> dict[str, str]:
    """Parse the first `## Document Control` two-column table."""
    fields: dict[str, str] = {}
    m = re.search(r"^##\s*Document Control\s*$", text, re.M | re.I)
    if not m:
        return fields
    # walk forward over table rows
    for line in text[m.end() :].splitlines():
        stripped = line.strip()
        if not stripped:
            if fields:
                break
            continue
        if stripped.startswith("##"):
            break
        if not stripped.startswith("|"):
            if fields:
                break
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        key, value = cells[0], cells[1]
        if key in {"Field", "---", ""} or set(key) <= {"-", " "}:
            continue
        fields[key] = value
    return fields


def parse_revision_history(text: str) -> tuple[bool, list[str]]:
    m = re.search(r"^##\s*Revision History\s*$", text, re.M | re.I)
    if not m:
        return False, []
    header: list[str] = []
    for line in text[m.end() :].splitlines():
        stripped = line.strip()
        if not stripped:
            if header:
                break
            continue
        if stripped.startswith("##"):
            break
        if not stripped.startswith("|"):
            if header:
                break
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not header:
            if set("".join(cells)) <= {"-", " "}:
                continue
            header = cells
            break
    return True, header


def collect_docs() -> list[Path]:
    return sorted(p for p in DOCS_DIR.rglob("*.md") if p.is_file())


def parse_register() -> dict[str, dict[str, str]]:
    """Return {relative_file_path: {column: value}} from DOCUMENT-REGISTER.md.

    The register file contains several tables (Document Control, Revision History,
    the register itself, a summary). The register table is identified by its header
    containing both 'Document Identifier' and 'File'.
    """
    if not REGISTER_PATH.exists():
        raise FileNotFoundError(f"register not found: {rel(REGISTER_PATH)}")
    text = REGISTER_PATH.read_text(encoding="utf-8")
    rows: dict[str, dict[str, str]] = {}
    header: list[str] = []
    in_register = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_register and header:
                break
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if set("".join(cells)) <= {"-", " "}:
            continue
        if not in_register:
            if "Document Identifier" in cells and "File" in cells:
                header = cells
                in_register = True
            continue
        if len(cells) < len(header):
            continue
        row = dict(zip(header, cells, strict=False))
        path = row.get("File", "").strip("`")
        if path:
            rows[path] = row
    return rows


def parse_qms_iso_ids() -> set[str]:
    """Extract ISO-series identifiers listed in QMS §7 Document Reference Matrix."""
    if not QMS_PATH.exists():
        raise FileNotFoundError(f"QMS not found: {rel(QMS_PATH)}")
    text = QMS_PATH.read_text(encoding="utf-8")
    m = re.search(r"^#{2,4}\s*(?:Section\s+)?(?:\d+[.:]\s*)?Document Reference Matrix\s*$", text, re.M)
    if not m:
        return set()
    section = text[m.end() :]
    nxt = re.search(r"^#{2,3}\s+(?:Section\s+)?(?:\d+[.:]\s*)?[A-Z]", section, re.M)
    if nxt:
        section = section[: nxt.start()]
    return set(re.findall(r"SOMA-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}", section))


def id_pattern_for(path: Path) -> re.Pattern[str] | None:
    rel_path = rel(path)
    for prefix, pattern in ID_PATTERNS.items():
        if rel_path.startswith(prefix):
            return pattern
    return None


def content_finding(rule: str, path: str, message: str, claim: str) -> Finding:
    """A content-rule finding. Fails only if the register claims 'Compliant'."""
    return Finding(rule, path, message, integrity=True, warn_only=(claim != "Compliant"))


def check(strict: bool) -> int:
    findings: list[Finding] = []

    try:
        register = parse_register()
    except FileNotFoundError as exc:
        print(f"TOOLING | {exc}", file=sys.stderr)
        return 2

    try:
        qms_ids = parse_qms_iso_ids()
    except FileNotFoundError as exc:
        print(f"TOOLING | {exc}", file=sys.stderr)
        return 2

    docs = collect_docs()

    # C-01 unregistered files
    for path in docs:
        r = rel(path)
        if r not in register:
            findings.append(Finding("C-01", r, "file is not listed in DOCUMENT-REGISTER.md"))

    # C-02 registered but missing
    for r in sorted(register):
        if not (REPO_ROOT / r).exists():
            findings.append(Finding("C-02", r, "listed in register but does not exist on disk"))

    register_ids: set[str] = set()
    # QMS-tier identifiers live under docs/iso/ (see the procedure §5.2 C-10).
    iso_ids: set[str] = set()
    ident_claims: dict[str, str] = {}
    noncompliant: list[tuple[str, str]] = []

    for path in docs:
        r = rel(path)
        text = path.read_text(encoding="utf-8")
        row = register.get(r, {})
        claim = (row.get("Compliance", "") or "Non-compliant").strip()
        fields = parse_control_table(text)
        has_rh, rh_cols = parse_revision_history(text)

        # Annexes (SOMA-BR-DOCS-001 §3.3.3): sub-identifier design artefacts.
        # They are inventoried in the register but carry no Document Control of their own.
        if is_annex(r):
            stem = Path(r).stem
            if not ANNEX_ID_RE.match(stem):
                findings.append(
                    content_finding(
                        "C-11",
                        r,
                        f"annex filename '{stem}' does not match UI-S-<NN>-<slug> / UI-X-<NN>-<slug>",
                        claim,
                    )
                )
            else:
                register_ids.add(stem)
            continue

        # C-11 identifier format
        ident = fields.get("Document Identifier", row.get("Document Identifier", "")).strip()
        if ident:
            register_ids.add(ident)
            if r.startswith("docs/iso/"):
                iso_ids.add(ident)
            ident_claims.setdefault(ident, claim)
            pattern = id_pattern_for(path)
            if pattern is not None and not pattern.match(ident):
                findings.append(
                    content_finding(
                        "C-11",
                        r,
                        f"identifier '{ident}' does not match the required pattern for its location",
                        claim,
                    )
                )
        elif r.startswith("docs/"):
            noncompliant.append((r, "no Document Identifier"))

        # C-12 filename IS the identifier (declared exceptions excepted)
        if ident and r not in FILENAME_EXCEPTIONS:
            stem = Path(r).stem
            if stem != ident:
                findings.append(
                    content_finding(
                        "C-12",
                        r,
                        f"filename stem '{stem}' != Document Identifier '{ident}'",
                        claim,
                    )
                )

        if not fields and not row:
            continue

        if not fields:
            findings.append(content_finding("C-03", r, "no '## Document Control' table", claim))
            noncompliant.append((r, "no Document Control"))
            continue

        # C-04 required fields
        for name in REQUIRED_FIELDS:
            if name not in fields or not fields[name].strip():
                findings.append(
                    content_finding("C-04", r, f"missing or empty required field '{name}'", claim)
                )

        # forbidden fields — always a content warning, never an integrity failure
        for name in FORBIDDEN_FIELDS:
            if name in fields:
                findings.append(
                    content_finding(
                        "C-04",
                        r,
                        f"uses non-house field '{name}' (see SOMA-BR-DOCS-001 §3.1)",
                        "Non-compliant",
                    )
                )

        # C-05 / C-06 closed sets
        status = fields.get("Status", "").strip()
        if status and status not in STATUS_VALUES:
            findings.append(
                content_finding(
                    "C-05", r, f"Status '{status}' is outside {sorted(STATUS_VALUES)}", claim
                )
            )
        classification = fields.get("Classification", "").strip()
        if classification and classification not in CLASSIFICATION_VALUES:
            findings.append(
                content_finding(
                    "C-06",
                    r,
                    f"Classification '{classification}' is outside {sorted(CLASSIFICATION_VALUES)}",
                    claim,
                )
            )

        # C-07 approver
        if "Approver" in fields and not fields["Approver"].strip():
            findings.append(
                content_finding("C-07", r, "Approver is blank (use '—' if unsigned)", claim)
            )

        # C-08 next review
        nr = fields.get("Next Review", "").strip()
        if not nr:
            findings.append(content_finding("C-08", r, "Next Review is missing", claim))
        elif not DATE_RE.match(nr):
            findings.append(
                content_finding("C-08", r, f"Next Review '{nr}' is not YYYY-MM-DD", claim)
            )
        else:
            try:
                if dt.date.fromisoformat(nr) < dt.date.today():
                    findings.append(
                        content_finding(
                            "C-08", r, f"Next Review '{nr}' is in the past", "Non-compliant"
                        )
                    )
            except ValueError:
                findings.append(
                    content_finding("C-08", r, f"Next Review '{nr}' is not a valid date", claim)
                )

        # C-09 revision history
        if not has_rh:
            findings.append(content_finding("C-09", r, "no '## Revision History' table", claim))
        else:
            expected = ["Version", "Date", "Author", "Description"]
            if rh_cols != expected:
                findings.append(
                    content_finding(
                        "C-09",
                        r,
                        f"Revision History columns {rh_cols} != {expected}",
                        claim,
                    )
                )

        if claim != "Compliant":
            noncompliant.append((r, f"register claim '{claim}'"))

    # C-10 register vs QMS §7 — divergence is fatal only for docs the register claims Compliant
    qms_only = qms_ids - register_ids
    register_only_iso = iso_ids - qms_ids
    for ident in sorted(qms_only):
        findings.append(
            Finding("C-10", rel(QMS_PATH), f"QMS §7 lists '{ident}' but it is not in the register")
        )
    for ident in sorted(register_only_iso):
        findings.append(
            content_finding(
                "C-10",
                rel(REGISTER_PATH),
                f"register lists QMS-tier doc '{ident}' but QMS §7 does not",
                ident_claims.get(ident, "Non-compliant"),
            )
        )

    # ---- report ----
    failing = [f for f in findings if f.failing]
    nonfailing = [f for f in findings if not f.failing]

    for f in findings:
        tag = "FAIL" if f.failing else "WARN"
        print(f"{tag} | {f.rule} | {f.path} | {f.message}")

    print()
    print(f"documents scanned      : {len(docs)}")
    print(f"registered             : {len(register)}")
    print(f"failing findings       : {len(failing)}")
    print(f"warnings               : {len(nonfailing)}")
    print(f"non-compliant (summary): {len({p for p, _ in noncompliant})}")

    if noncompliant:
        print("\nnon-compliant files (tracked findings, not silently exempted):")
        seen: set[str] = set()
        for p, why in sorted(set(noncompliant)):
            if p in seen:
                continue
            seen.add(p)
            print(f"  - {p}: {why}")

    if failing:
        print("\nRESULT: FAIL")
        return 1
    if strict and noncompliant:
        print("\nRESULT: FAIL (strict mode: non-compliant files present)")
        return 1
    print("\nRESULT: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict", action="store_true", help="also fail on non-compliant registered docs"
    )
    args = parser.parse_args()
    return check(strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
