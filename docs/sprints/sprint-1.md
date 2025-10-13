> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Sprint 1 (Stabilize)

- **Cadence:** Oct 11 – Oct 24, 2025
- **Goal:** Establish reliable CI gating, document ownership, and capture truth-first regression coverage for memory recall.

## Backlog

| ID | Work Item | Owner | Status | Notes |
| --- | --- | --- | --- | --- |
| S1-01 | Harden CI gates (`ruff`, `mypy`, `pytest`, integration smoke) | Platform Eng | ✅ Done | Added `scripts/ci/run_ci.sh` mirroring pipeline and documented usage |
| S1-02 | Publish service ownership matrix | Platform Eng | ✅ Done | See `docs/ownership.md` |
| S1-03 | Capture golden datasets for Redis/Postgres/Memory | Memory Platform | ⛔ Blocked | External memory endpoint credentials pending; cannot refresh capture |
| S1-04 | Add failing regression test for `/remember` ➜ `/recall` truth gap | Memory Platform | ✅ Done | See `tests/integration/test_memory_truth.py` (fails until bug fixed) |
| S1-05 | Draft ADR-001 (Adopt dependency injection container) | Architecture | ✅ Done | `docs/adr/ADR-001-di-adoption.md` |
| S1-06 | Update runbooks with ingress/TLS validation steps | SRE | ✅ Done | Added ingress/TLS section to `docs/OPS_K8S_RUNBOOK.md` |

## Daily Journal

| Date | Update |
| --- | --- |
| 2025-10-11 | Sprint kick-off. Ownership matrix delivered (`docs/ownership.md`). Regression test design initiated (S1-04). |
| 2025-10-11 | CI script published (`scripts/ci/run_ci.sh`), ADR-001 drafted, ingress/TLS steps documented. Golden dataset scaffolding created. |
| 2025-10-12 | Golden dataset checksum documented (`tests/data/golden/README.md`); live capture blocked until external memory endpoint access is granted. |

## Risks & Mitigations

- **Recall regression persists:** Mitigate by writing failing test to capture current behavior before refactor.
- **CI gate gaps:** Audit `pyproject.toml`, ensure `uv run` commands run in GitHub Actions and local pre-commit.
- **Golden dataset drift:** Store datasets as fixtures checked by checksum; document refresh procedure.

## Definition of Done

- All backlog items marked ✅.
- CI pipeline fails on lint/type/test errors.
- Memory recall regression reproducible via automated test.
- Ownership doc and ADR accessible from root README links.
