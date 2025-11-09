# SomaBrain Documentation

**Purpose**: Single entry-point and navigation for all documentation sets, aligned to ISO/IEC guidance.

**Audience**: Users, operators, contributors, auditors, and AI agents.

**Prerequisites**: None - start here for all documentation needs.

---

## Documentation Structure

This documentation follows the ISO-aligned four-manual structure:

| Manual | Audience | Purpose | Path |
|--------|----------|---------|------|
| **User Manual** | End users, product managers | How to use SomaBrain API | [user-manual/](user-manual/index.md) |
| **Technical Manual** | SREs, operators, platform teams | How to deploy and operate | [technical-manual/](technical-manual/index.md) |
| **Development Manual** | Engineers, contributors | How to build and extend | [development-manual/](development-manual/index.md) |
| **Onboarding Manual** | New team members, contractors | How to get productive quickly | [onboarding-manual/](onboarding-manual/index.md) |

---

## Quick Navigation

### For Users
- [Installation Guide](user-manual/installation.md) - Get SomaBrain running
- [Quick Start Tutorial](user-manual/quick-start-tutorial.md) - Your first memory operations
- [API Features](user-manual/features/) - Complete feature documentation
- [FAQ](user-manual/faq.md) - Common questions and troubleshooting

### For Operators
- [Architecture Overview](technical-manual/architecture.md) - System design and components
- [Deployment Guide](technical-manual/deployment.md) - Production deployment
- [Environment Variables](technical-manual/environment-variables.md) - Configuration matrix
- [Services & Ports](technical-manual/services-and-ports.md) - Compose/K8s ports overview
- [Benchmarks Quickstart](technical-manual/benchmarks-quickstart.md) - Run live and micro benches
- [Monitoring Setup](technical-manual/monitoring.md) - Observability and alerts
- [Runbooks](technical-manual/runbooks/) - Operational procedures

### For Developers
- [Local Setup](development-manual/local-setup.md) - Development environment
- [Coding Standards](development-manual/coding-standards.md) - Code style and quality
- [Testing Guidelines](development-manual/testing-guidelines.md) - Test strategy
- [Contribution Process](development-manual/contribution-process.md) - How to contribute

### For New Team Members
- [Project Context](onboarding-manual/project-context.md) - Mission and goals
- [Codebase Walkthrough](onboarding-manual/codebase-walkthrough.md) - Architecture tour
- [First Contribution](onboarding-manual/first-contribution.md) - Your first PR
- [Domain Knowledge](onboarding-manual/domain-knowledge.md) - Technical deep-dive

---

## Standards Compliance

This documentation adheres to the following international standards:

| Standard | Scope | Application |
|----------|-------|-------------|
| **ISO/IEC 12207:2017** | Software lifecycle processes | Process documentation, configuration management |
| **ISO/IEC 15288:2015** | System lifecycle processes | System architecture, integration |
| **ISO/IEC 29148:2018** | Requirements engineering | Feature specifications, API contracts |
| **ISO/IEC 29119:2013** | Software testing | Test strategy, quality assurance |
| **ISO/IEC 42010:2011** | Architecture description | System design, component interactions |
| **ISO 21500:2012** | Project management | Documentation maintenance, review cycles |
| **ISO/IEC 27001:2013** | Information security | Security policies, access control |
| **IEEE 1016:2009** | Software design descriptions | Technical specifications |

---

## Documentation Metadata

- **Version**: See [front_matter.yaml](front_matter.yaml) and [metadata.json](metadata.json)
- **Last Updated**: 2025-01-26
- **Project Version**: 3.0.2-KARPATHY-INFLUENCE
- **Maintenance**: Quarterly review cycle (90-day stale threshold)

---

## Quality Assurance

All documentation undergoes:

- **Linting**: `markdownlint-cli2` for style compliance
- **Link Validation**: Automated checks for broken references
- **Accessibility**: WCAG 2.1 AA compliance
- **Review**: Peer review before publication
- **Feedback**: User feedback collection enabled

See [style-guide.md](style-guide.md) for formatting standards.

---

## Verification

- Confirm all links resolve correctly
- Check that version numbers match across metadata files
- Verify code examples are tested and working
- Ensure diagrams render properly

---

## Common Errors

| Issue | Symptom | Resolution |
|-------|---------|------------|
| Broken links | 404 errors when navigating | Update link targets in affected files |
| Outdated examples | Code samples don't work | Review and test examples against current codebase |
| Missing prerequisites | Users can't follow guides | Add prerequisite sections to affected documents |
| Version mismatch | Conflicting version information | Update front_matter.yaml and metadata.json |

---

## References

- [Global Glossary](glossary.md) - Terminology and definitions
- [Style Guide](style-guide.md) - Writing and formatting standards
- [Changelog](changelog.md) - Version history and changes
- [Root README](../README.md) - Project overview
