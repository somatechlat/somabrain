# SOMA COGNITIVE TRIAD — VERSION COMPATIBILITY MATRIX

## Document Control

| Field | Value |
|---|---|
| Document Title | Soma Cognitive Triad Version Compatibility Matrix |
| Document Identifier | SOMA-BR-COMPAT-001 |
| Version | 1.0.1 |
| Date | 2026-06-15 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0.0 | 2026-06-15 | SomaTech Engineering | Initial compatibility matrix |
| 1.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `SOMA-COMPAT-001` set to filename stem `SOMA-BR-COMPAT-001` \| prior status `Active` normalised to `Draft` (no approver named). |

---

## 1. Purpose

This document defines the **version compatibility contract** between the three repositories of the Soma Cognitive Triad. It is the single source of truth for which versions of each component are tested and guaranteed to work together.

Each repository maintains an identical copy of this file. When a version is bumped, **all three copies must be updated simultaneously**.

---

## 2. Component Registry

| Component | Repository | Current Version | Standalone Port | AAAS Port |
|-----------|-----------|----------------|-----------------|-----------|
| SomaAgent01 | somaAgent01 | 2.0.0 | 20020 | 63900 |
| SomaBrain | somabrain | 0.2.0 | 9696 | 63996 |
| SomaFractalMemory | somafractalmemory | 0.2.0 | 10101 | 63901 |

---

## 3. Compatibility Matrix

### 3.1 Tested Version Combinations

| Matrix ID | SomaAgent01 | SomaBrain | SomaFractalMemory | Status | Notes |
|-----------|-------------|-----------|-------------------|--------|-------|
| M-001 | 2.0.0 | 0.2.0 | 0.2.0 | **CURRENT** | ISO audit baseline, code-verified |
| M-002 | 1.1.0 | 0.2.0 | 0.2.0 | COMPATIBLE | Pre-audit agent, stable brain/SFM |
| M-003 | 1.0.0 | 0.1.x | 0.1.x | DEPRECATED | Initial release, no longer supported |

### 3.2 Per-Component Requirements

**SomaAgent01 v2.0.0 requires:**
```
somabrain >= 0.2.0, < 0.3.0
somafractalmemory >= 0.2.0, < 0.3.0
python >= 3.12, < 3.14
postgresql >= 15
redis >= 7.0
```

**SomaBrain v0.2.0 requires:**
```
somafractalmemory >= 0.2.0, < 0.3.0
python >= 3.12, < 3.13
postgresql >= 15
redis >= 7.0
milvus >= 2.3
kafka >= 3.7 (optional in standalone)
```

**SomaFractalMemory v0.2.0 requires:**
```
python >= 3.12, < 3.14
postgresql >= 15
redis >= 7.0
milvus >= 2.3
```

---

## 4. Mode Compatibility

### 4.1 Standalone Mode

Any component can run independently without the other two.

| Component | Standalone Config | Disabled Features |
|-----------|-------------------|-------------------|
| SomaAgent01 | `SA01_DEPLOYMENT_MODE=STANDALONE` | BrainBridge, SFM adapter, AAAS billing, neuromodulator sync |
| SomaBrain | `SOMABRAIN_MODE=standalone` | SFM HTTP transport, multi-tenant quotas, AAAS billing |
| SomaFractalMemory | Standalone Docker Compose | SomaBrain token validation (sbk_* keys), AAAS admin |

### 4.2 AAAS Mode

All three components run together as an integrated cognitive stack.

| Component | AAAS Config | Required Peers |
|-----------|-------------|----------------|
| SomaAgent01 | `SA01_DEPLOYMENT_MODE=AAAS` | SomaBrain (port 63996), SomaFractalMemory (port 63901) |
| SomaBrain | `SOMABRAIN_MODE=production` | SomaFractalMemory (port 63901) |
| SomaFractalMemory | AAAS Docker Compose | None (consumed by others) |

---

## 5. Integration Contracts

### 5.1 SomaAgent01 → SomaBrain

| Contract | Value |
|----------|-------|
| Protocol | HTTP/1.1 + Server-Sent Events |
| Auth | Bearer token (`SOMA_API_TOKEN`) |
| Endpoints | `POST /api/v1/memory/store`, `POST /api/v1/memory/recall`, `POST /v1/context/evaluate`, `PUT /v1/neuromodulators`, `POST /v1/learning/reward` |
| Health | `GET /health` |
| Timeout | 30s (circuit breaker: 5 failures → open, 30s reset) |
| Fallback | SomaFractalMemory (direct) + PendingMemory queue |

### 5.2 SomaAgent01 → SomaFractalMemory

| Contract | Value |
|----------|-------|
| Protocol | HTTP/1.1 |
| Auth | Bearer token (`SOMA_API_TOKEN`) |
| Endpoints | `POST /memories`, `POST /memories/search`, `GET /memories/{coord}`, `GET /healthz` |
| Health | `GET /healthz` |
| Timeout | 10s |
| Fallback | PendingMemory queue for later sync |

### 5.3 SomaBrain → SomaFractalMemory

| Contract | Value |
|----------|-------|
| Protocol | HTTP/1.1 |
| Auth | Bearer token (sbk_* prefix validated by SFM) |
| Endpoints | `POST /memories`, `POST /memories/search`, `POST /graph/link`, `GET /graph/neighbors` |
| Health | `GET /healthz` |
| Timeout | 10s (circuit breaker: per-tenant) |
| Fallback | Degraded queue (`SOMABRAIN_MEMORY_DEGRADE_QUEUE=1`) |

---

## 6. Port Authority

### 6.1 Standalone Ports (20xxx / native)

| Service | SomaAgent01 | SomaBrain | SomaFractalMemory |
|---------|-------------|-----------|-------------------|
| API | 20020 | 9696 | 10101 |
| PostgreSQL | 20432 | 5432 | 10432 |
| Redis | 20379 | 6379 | 10379 |
| Keycloak | 20880 | — | — |
| Vault | 20882 | — | 10200 |
| Milvus | — | 19530 | 10530 |
| Kafka | — | 9092 | — |
| OPA | 20181 | 8181 | 10818 |
| SpiceDB | 20051 | — | — |

### 6.2 AAAS Ports (63xxx)

| Service | Port | Component |
|---------|------|-----------|
| SomaAgent01 API | 63900 | SomaAgent01 |
| SomaBrain | 63996 | SomaBrain |
| SomaFractalMemory | 63901 | SomaFractalMemory |
| PostgreSQL | 63932 | Shared |
| Redis | 63979 | Shared |
| Keycloak | 63980 | Shared |
| Vault | 63982 | Shared |

---

## 7. Shared Infrastructure (AAAS Mode)

When running in AAAS mode, the three components share:

| Resource | Isolation Strategy |
|----------|-------------------|
| PostgreSQL | Shared server, separate schemas per component |
| Redis | Shared server, separate DB numbers (Agent=0, Brain=1, SFM=2) |
| Kafka | Shared cluster, separate topics per component |
| Keycloak | Shared realm (`somaagent`), separate clients per component |
| Vault | Shared server, separate secret paths per component |

---

## 8. Version Bumping Procedure

When releasing a new version of any component:

1. **Bump version** in the component's `pyproject.toml`
2. **Run compatibility tests** against all supported peer versions
3. **Update this file** in ALL THREE repositories simultaneously
4. **Tag the release** with semantic version
5. **Publish Docker image** with version tag
6. **Update AAAS deployment manifest** with new image tags

---

## 9. Deprecation Policy

- **Major version bump** (X.0.0): Breaking changes, requires coordinated release
- **Minor version bump** (0.X.0): New features, backward compatible within range
- **Patch version bump** (0.0.X): Bug fixes, fully backward compatible
- **Minimum support window**: 6 months after deprecation notice
- **Compatibility matrix**: Retains last 3 tested combinations

---

End of Document
