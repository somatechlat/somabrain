# SomaBrain AAAS - Documentation Index

**Version:** 3.0.0  
**Date:** 2025-12-24

---

## Quick Links

| Document | Description |
|----------|-------------|
| [Overview](./overview.md) | High-level product and runtime overview |
| [Master SRS](./srs/SOMABRAIN_AAAS_SRS.md) | High-level requirements |
| [User Journeys](./srs/user-journey-screens.md) | 12 use cases, 41 screens |
| [API Key Auth](./srs/api-key-authentication.md) | Authentication layer |

---

## SRS Documents

| # | Document | Content |
|---|----------|---------|
| 01 | [Multi-Tenancy](./srs/01-multi-tenancy.md) | Tenant lifecycle |
| 02 | [Subscription & Billing](./srs/02-subscription-billing.md) | Lago integration |
| 03 | [Authentication & SSO](./srs/03-authentication-sso.md) | Keycloak, OAuth |
| 04 | [God Mode Admin](./srs/04-god-mode-admin.md) | Platform admin |
| 05 | [Memory Management](./srs/05-memory-cognitive.md) | Cache, Store |
| 06 | [API Gateway](./srs/06-api-gateway.md) | Rate limiting |
| 07 | [Observability](./srs/07-observability.md) | Health, metrics |
| 08 | [Platform Admin](./srs/08-platform-administration-complete.md) | All settings |
| 09 | [Unified Platform](./srs/09-unified-memory-platform.md) | SomaBrain + SFM |
| 10 | [SomaFractalMemory](./srs/10-somafractalmemory-complete.md) | LTM system |
| 11 | [Docker Deployment](./srs/11-docker-deployment.md) | Containers |

---

## UI Documentation

| Document | Description |
|----------|-------------|
| [Screen Map](./srs/god-mode-screen-map.md) | 18 admin screens |
| [User Flows](./srs/flows/) | Journey documentation |

---

## Architecture

| Document | Description |
|----------|-------------|
| [Roadmap](./architecture/canonical_roadmap_oak.md) | Platform roadmap |

---

## Deployment

| Document | Description |
|----------|-------------|
| [Docker Guide](./deployment/docker_deployment.md) | Docker setup |
| [Production](./deployment/production_deployment.md) | Production deploy |

---

## Directory Structure

```
docs/
├── README.md                    # This file
├── overview.md                  # Product overview
├── srs/                         # Requirements (13 docs)
│   ├── flows/                   # User journeys (10 docs)
│   └── ...
├── api/                         # API documentation
├── architecture/                # Architecture docs
├── deployment/                  # Deployment guides
├── development/                 # Contributor and dev manuals
├── technical/                   # Technical manual
├── user/                        # User manual
├── onboarding/                  # Onboarding (incl. agents)
├── operations/                  # Operational guides + runbooks
├── governance/                  # VIBE rules and violations
└── reference/                   # Glossary + changelog
```

---

*SomaBrain AAAS Platform - ISO/IEC/IEEE 29148:2018*
