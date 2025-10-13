> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Sprint 3 (Shared Infra Enablement)

- **Cadence:** Oct 18 – Nov 1, 2025
- **Goal:** Codify the SomaStack shared infrastructure playbook inside the repository and automate Kind → Helm deployment flows for agents.

## Backlog

| ID | Work Item | Owner | Status | Notes |
| --- | --- | --- | --- | --- |
| S3-01 | Convert shared infra playbook into repo docs | Platform Eng | ✅ Done | `docs/shared_infra/SomaStack_Shared_Infra_Playbook.md` |
| S3-02 | Author automation scripts (`scripts/shared_infra/*.sh`) | Platform Eng | ⏳ Planned | Scripts for reset, deploy, health snapshot |
| S3-03 | Template ExternalSecret + ConfigMap contracts | Platform Eng | ⏳ Planned | Align with playbook Section 3 |
| S3-04 | Provide sample GitHub Actions workflow | Platform Eng | ⏳ Planned | Derive from Section 4 blueprint |
| S3-05 | Document namespace/Vault onboarding runbook | Platform Eng | ⏳ Planned | Cross-link to `docs/OPS_K8S_RUNBOOK.md` |

## Daily Journal

| Date | Update |
| --- | --- |
| 2025-10-11 | Playbook ingested and published under `docs/shared_infra/`. |

## Risks & Mitigations

- **Kind resource limits**: Validate node allocatable values before deploy; document scaling knobs.
- **Image pull throttling**: Provide registry mirrors or caching instructions in scripts.
- **Playbook drift**: Tie updates to Helm chart changes; add CI check to confirm docs referenced in PRs touching infra.

## Definition of Done

- Shared infra playbook published and referenced from canonical roadmap.
- Automation scripts provision Kind cluster, preload images, deploy Helm charts, and validate readiness.
- Example GitHub Actions workflow committed with readiness gate.
