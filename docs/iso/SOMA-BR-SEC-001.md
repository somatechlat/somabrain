# SOMA-BR-SEC-001: SomaBrain Security Assessment

> **Standard:** ISO/IEC 27001:2022 — Information Security Management Systems
> **Owner:** SomaTech Security Team

---

## Document Control

| Field | Value |
|---|---|
| Document Title | SomaBrain Security Assessment |
| Document Identifier | SOMA-BR-SEC-001 |
| Version | 2.0.2 |
| Date | 2026-10-08 |
| Status | Approved |
| Author | SomaTech Security Team |
| Approver | CISO, SomaTech |
| Classification | Confidential |
| ISO Reference | ISO/IEC 27001:2022 — Information Security Management Systems |
| Next Review | 2026-12-28 |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-02-15 | Security Team | Initial security assessment |
| 1.5.0 | 2026-04-20 | Security Team | Added multi-tenancy isolation review |
| 2.0.0 | 2026-06-15 | Security Team | Comprehensive re-assessment: JWT, OPA, Vault, TLS, constitution signing, per-tenant isolation |
| 2.0.1 | 2026-09-28 | SomaTech Engineering | Document control normalised: identifier `(blank)` set to filename stem `SOMA-BR-SEC-001` \| Status added as `Approved` (document names an approver) \| prior classification `Internal / Confidential` normalised to `Confidential`. |
| 2.0.2 | 2026-10-08 | SomaTech Engineering | Settings/secrets law banner added (§1.3) and §8 tightened: settings = Django + `BrainSetting`/agent DB; secrets = Vault only (Art 26); **no file presets**. |

---

## Settings & Secrets Law (banner — binding)

> **SETTINGS = Django + `BrainSetting` / agent DB** (administerable).
> **SECRETS = Vault ONLY** (Covenant Art 26).
> **NO file presets. NO env secrets. NO `.env` as authority.**
> Full treatment in [§8 Secrets Management](#8-secrets-management). Violations are security defects.

---

## Table of Contents

1. [Scope and Methodology](#1-scope-and-methodology)
2. [Security Architecture Overview](#2-security-architecture-overview)
3. [Authentication](#3-authentication)
4. [Authorization](#4-authorization)
5. [Data Protection](#5-data-protection)
6. [Constitution Signing](#6-constitution-signing)
7. [Transport Security](#7-transport-security)
8. [Secrets Management](#8-secrets-management)
9. [Per-Tenant Memory Isolation](#9-per-tenant-memory-isolation)
10. [Audit Logging and Compliance](#10-audit-logging-and-compliance)
11. [Threat Model](#11-threat-model)
12. [Security Findings and Recommendations](#12-security-findings-and-recommendations)

---

## 1. Scope and Methodology

### 1.1 Scope

This assessment covers the security controls of SomaBrain:

- Authentication and authorization mechanisms
- Data protection at rest and in transit
- Multi-tenancy isolation
- Secrets management
- Audit logging and compliance posture
- Integration security (SomaFractalMemory, SomaAgent01, Kafka)

### 1.2 Methodology

- Architecture review against OWASP ASVS 4.0
- Code review of security-critical paths
- Configuration audit of security-related settings (Django / `BrainSetting`) and Vault secret handling
- Threat modeling using STRIDE methodology
- Compliance mapping to GDPR, HIPAA, SOC2 controls

---

## 2. Security Architecture Overview

SomaBrain implements a defense-in-depth security model with multiple layers:

```
┌──────────────────────────────────────────────────────────┐
│                    External Traffic                        │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  Layer 1: TLS Termination (Load Balancer / Reverse Proxy) │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  Layer 2: JWT Authentication (Token Validation)           │
│  - Keycloak / Auth0 / Custom provider                     │
│  - RS256 / ES256 signature verification                   │
│  - Audience and issuer validation                         │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  Layer 3: OPA Policy Authorization                        │
│  - Fine-grained policy evaluation                         │
│  - Role-based and attribute-based access control          │
│  - Policy-as-code (Rego)                                  │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  Layer 4: Per-Tenant Isolation                             │
│  - Cryptographic tenant ID from JWT claims                │
│  - Per-tenant circuit breakers                            │
│  - Per-tenant quotas and rate limits                      │
│  - Namespace-scoped memory access                         │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  Layer 5: Data Protection                                  │
│  - PII masking in logs                                    │
│  - Constitution signing for memory operations             │
│  - Audit trail with operation hashes                      │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Authentication

### 3.1 JWT Authentication

| Property | Value |
|---|---|
| Token Type | JSON Web Token (JWT) |
| Signature Algorithms | RS256, ES256 (configurable) |
| Validation | Signature, expiry, audience (`SOMABRAIN_JWT_AUDIENCE`), issuer (`SOMABRAIN_JWT_ISSUER`) |
| Key Source | JWKS endpoint or static public key (`SOMABRAIN_JWT_PUBLIC_KEY_PATH`) |
| Token Secret | `SOMABRAIN_JWT_SECRET` (symmetric fallback) |

### 3.2 Configuration

| Variable | Description | Mode |
|---|---|---|
| `SOMABRAIN_AUTH_REQUIRED` | Enable/disable auth enforcement | All |
| `SOMABRAIN_JWT_SECRET` | Symmetric signing secret | Dev/Staging |
| `SOMABRAIN_JWT_PUBLIC_KEY_PATH` | RSA/EC public key path | Production |
| `SOMABRAIN_JWT_AUDIENCE` | Expected audience claim | Production |
| `SOMABRAIN_JWT_ISSUER` | Expected issuer claim | Production |
| `SOMABRAIN_API_TOKEN` | Static API token (service-to-service) | All |

### 3.3 Providers

SomaBrain supports multiple JWT providers:

| Provider | Use Case | Integration |
|---|---|---|
| **Keycloak** | Enterprise identity | OIDC discovery, JWKS rotation |
| **Auth0** | Hosted identity | OIDC discovery, JWKS rotation |
| **Custom** | Self-hosted | Static public key or JWKS URL |

### 3.4 Assessment

| Aspect | Status | Notes |
|---|---|---|
| Token validation | ✅ Strong | All standard JWT claims validated |
| Key rotation | ✅ Supported | JWKS endpoint with caching |
| Expiry enforcement | ✅ Enforced | Tokens rejected after expiry |
| Replay protection | ✅ Via expiry | Short-lived tokens recommended |

---

## 4. Authorization

### 4.1 OPA Policy Engine

SomaBrain integrates with Open Policy Agent (OPA) for fine-grained authorization:

| Property | Value |
|---|---|
| Policy Language | Rego |
| Endpoint | `SOMABRAIN_OPA_URL` |
| Evaluation | Per-request policy check |
| Mode (Dev) | Optional / relaxed |
| Mode (Production) | Mandatory / strict |

### 4.2 Policy Dimensions

| Dimension | Description |
|---|---|
| **Identity** | Who is making the request (JWT claims) |
| **Resource** | What resource is being accessed (memory ID, namespace) |
| **Action** | What operation is being performed (store, recall, delete) |
| **Context** | Request metadata (IP, time, tenant) |

### 4.3 Assessment

| Aspect | Status | Notes |
|---|---|---|
| Policy-as-code | ✅ Strong | Rego policies version-controlled |
| Evaluation performance | ✅ Fast | OPA provides sub-millisecond decisions |
| Policy updates | ✅ Hot-reload | No restart required for policy changes |
| Audit trail | ✅ Logged | Policy decisions logged with request context |

---

## 5. Data Protection

### 5.1 PII Masking

Automatic PII detection and redaction in log output:

| PII Type | Detection Method | Masking |
|---|---|---|
| Email addresses | Regex pattern | `***@***.***` |
| Phone numbers | Regex pattern | `***-***-****` |
| SSN / National IDs | Regex pattern | `***-**-****` |
| Credit card numbers | Luhn-validated regex | `****-****-****-****` |
| Custom patterns | Configurable rules | User-defined |

### 5.2 Data at Rest

| Store | Encryption | Notes |
|---|---|---|
| PostgreSQL | Disk-level encryption (LUKS/cloud KMS) | Application-level encryption for sensitive fields |
| Redis | In-memory (no persistence by default) | TLS for cluster mode |
| Milvus | Disk-level encryption | Vector data not individually encrypted |
| Kafka | Disk-level encryption | Messages retained per topic policy |

### 5.3 Data Classification

| Level | Description | Examples |
|---|---|---|
| **Public** | Non-sensitive | API documentation, health status |
| **Internal** | Low sensitivity | Configuration, metrics, logs |
| **Confidential** | Moderate sensitivity | Memory content, embeddings, user data |
| **Restricted** | High sensitivity | JWT secrets, API tokens, encryption keys |

---

## 6. Constitution Signing

### 6.1 Mechanism

SomaBrain implements constitution signing for memory operation integrity:

| Property | Description |
|---|---|
| **Purpose** | Cryptographic proof that a memory operation was authorized and unmodified |
| **Signing Key** | Tenant-specific key derived during tenant provisioning |
| **Scope** | Memory store, update, and delete operations |
| **Verification** | On retrieval, signature verified before returning data |
| **Tamper Detection** | Any modification to signed memory invalidates the signature |

### 6.2 Signature Flow

```
Client Request → Auth + OPA → Memory Operation
                                    ↓
                          Constitution Sign (tenant key)
                                    ↓
                          Store (memory + signature)
                                    ↓
                          On Retrieve: Verify Signature
                                    ↓
                          Return (if valid) or Reject (if tampered)
```

### 6.3 Assessment

| Aspect | Status | Notes |
|---|---|---|
| Design | ✅ Sound | Tenant-scoped signing prevents cross-tenant forgery |
| Key Management | ⚠️ Review Needed | Key derivation and rotation mechanism needs validation |
| Performance Impact | ✅ Minimal | Signing adds < 1ms per operation |
| Tamper Detection | ✅ Effective | Modified memories rejected on retrieval |

---

## 7. Transport Security

### 7.1 TLS Configuration

| Layer | TLS Mode | Configuration |
|---|---|---|
| External → Load Balancer | TLS 1.2+ termination | Load balancer configuration |
| Load Balancer → SomaBrain | Internal TLS or plaintext | Deployment-dependent |
| SomaBrain → PostgreSQL | Optional TLS | `SOMABRAIN_POSTGRES_DSN` with `sslmode` |
| SomaBrain → Redis | TLS for cluster mode | Redis TLS configuration |
| SomaBrain → Kafka | TLS with mTLS | Kafka broker TLS configuration |
| SomaBrain → Milvus | TLS | Milvus TLS configuration |
| SomaBrain → SomaFractalMemory | HTTPS | Endpoint URL scheme |

### 7.2 Assessment

| Aspect | Status | Notes |
|---|---|---|
| External TLS | ✅ Strong | Standard TLS 1.2+ at load balancer |
| Internal TLS | ⚠️ Variable | Depends on deployment; not all internal links use TLS |
| Certificate Management | ✅ Standard | Supports standard cert chains; Vault integration for cert rotation |

---

## 8. Secrets Management

**Settings law (binding):** settings are administered via **Django + `BrainSetting` (agent DB)**.
Secrets are **Vault ONLY** (not Vault/env, not files). **No file presets** — a YAML/JSON/`.env`
preset is not a settings or secrets authority (Covenant Art 26 + operator law).

**Normative — Covenant Art 26 (Secret Protection):**
> "Production secrets shall reside exclusively in secure vault systems. Storage in code, configuration files, or environment variables is prohibited."

Secrets are **Vault ONLY** (not Vault/env). Settings are administered via Django + `BrainSetting` (agent DB).

### 8.1 HashiCorp Vault Integration

| Property | Value |
|---|---|
| Vault Endpoint | `SOMABRAIN_VAULT_ADDR` |
| Auth Method | Token, AppRole, or Kubernetes service account |
| Secret Engine | KV v2 (key-value) |
| Use Cases | Database credentials, API tokens, encryption keys, JWT secrets |
| Rotation | Supported via Vault's dynamic secrets engine |

### 8.2 Secret Inventory

| Secret | Storage | Rotation |
|---|---|---|
| `SOMABRAIN_POSTGRES_DSN` | Vault | Vault dynamic secrets |
| `SOMABRAIN_REDIS_URL` | Vault | Manual or Vault |
| `SOMABRAIN_JWT_SECRET` | Vault | Manual or Vault |
| `SOMABRAIN_API_TOKEN` | Vault | Manual |
| `SOMABRAIN_MEMORY_HTTP_TOKEN` | Vault | Manual |

### 8.3 Assessment

| Aspect | Status | Notes |
|---|---|---|
| Secrets in code | ✅ None | All secrets via Vault only (Covenant Art 26) |
| Secrets in version control | ✅ None | No secret values in VCS; `.env.example` is non-secret settings placeholders only |
| Rotation capability | ✅ Supported | Vault dynamic secrets for database; others manual |
| Audit trail | ✅ Vault audit | All Vault access logged |

---

## 9. Per-Tenant Memory Isolation

### 9.1 Isolation Mechanisms

| Layer | Mechanism | Description |
|---|---|---|
| **Identity** | JWT tenant claim | Tenant ID extracted from authenticated JWT |
| **Application** | Namespace scoping | All memory operations scoped to tenant namespace |
| **Cache** | Redis key prefix | `tenant:{id}:*` key pattern |
| **Vector Store** | Milvus collection per tenant | Separate HNSW indices per tenant |
| **Database** | Row-level filtering | PostgreSQL queries filtered by tenant_id |
| **Circuit Breaker** | Per-tenant state machine | Independent failure tracking per tenant |
| **Quotas** | Per-tenant limits | Rate limit, memory capacity, API call quota |

### 9.2 Isolation Verification

| Test | Status |
|---|---|
| Tenant A cannot read Tenant B's memories | ✅ Enforced by namespace scoping |
| Tenant A's failure does not affect Tenant B | ✅ Per-tenant circuit breakers |
| Tenant A's quota exhaustion does not affect Tenant B | ✅ Per-tenant quotas |
| Cross-tenant memory leakage via shared caches | ✅ Prevented by key prefixing |

### 9.3 Assessment

| Aspect | Status | Notes |
|---|---|---|
| Cryptographic isolation | ✅ Strong | Tenant ID from signed JWT; cannot be forged |
| Storage isolation | ✅ Strong | Separate collections/indices per tenant |
| Failure isolation | ✅ Strong | Per-tenant circuit breakers |
| Resource isolation | ✅ Strong | Per-tenant quotas and rate limits |

---

## 10. Audit Logging and Compliance

### 10.1 Audit Events

| Event Category | Logged Data | Retention |
|---|---|---|
| Authentication | Login attempts, token validation, failures | 90 days |
| Authorization | OPA policy decisions, allow/deny | 90 days |
| Memory Operations | Store, recall, update, delete (with tenant ID) | 1 year |
| Configuration Changes | Settings modifications | 1 year |
| Admin Actions | Tenant provisioning, quota changes | 1 year |
| Security Events | Failed auth, rate limit exceeded, circuit breaker trips | 1 year |

### 10.2 Compliance Mapping

| Standard | Status | Key Controls |
|---|---|---|
| **GDPR** | ✅ Ready | PII masking, data deletion capability, audit trail, consent management |
| **HIPAA** | ✅ Ready | Access controls, audit logging, encryption, BAA available |
| **SOC2** | ⚠️ In Progress | Security, availability, processing integrity controls in place; formal audit pending |

### 10.3 Provenance Tracking

Each memory operation generates a provenance chain:

| Field | Description |
|---|---|
| `operation_hash` | SHA-256 of the operation payload |
| `tenant_id` | Issuing tenant |
| `timestamp` | ISO 8601 timestamp |
| `parent_hash` | Hash of the previous operation (chain) |
| `signature` | Constitution-signed verification |

---

## 11. Threat Model

### 11.1 STRIDE Analysis

| Threat | Category | Mitigation | Residual Risk |
|---|---|---|---|
| Token forgery | Spoofing | RS256/ES256 signature verification, JWKS rotation | Low |
| Unauthorized memory access | Tampering | OPA policies, namespace scoping, constitution signing | Low |
| Memory content disclosure | Information Disclosure | Per-tenant isolation, TLS, PII masking | Low |
| Denial of service (single tenant) | Denial of Service | Per-tenant rate limits, circuit breakers | Low |
| Denial of service (system-wide) | Denial of Service | Global rate limiting, resource quotas | Medium |
| Cross-tenant data leakage | Elevation of Privilege | JWT tenant claims, namespace enforcement, Milvus collection isolation | Low |
| Kafka message interception | Information Disclosure | TLS + mTLS for Kafka | Low |
| Supply chain compromise | Tampering | Dependency pinning; vulnerability scanning recommended | Medium |
| Configuration drift | Information Disclosure | Environment-driven config, no secrets in code | Low |
| Insider threat | Various | Audit logging, principle of least privilege | Medium |

### 11.2 Risk Heat Map

| | Low Impact | Medium Impact | High Impact |
|---|---|---|---|
| **High Likelihood** | | Supply chain | |
| **Medium Likelihood** | | System-wide DoS, Insider threat | |
| **Low Likelihood** | Configuration drift | | Token forgery, Data leakage, Unauthorized access |

---

## 12. Security Findings and Recommendations

### 12.1 Strengths

1. **Strong authentication foundation:** JWT with RS256/ES256, configurable providers, full claim validation.
2. **Policy-as-code authorization:** OPA integration enables auditable, version-controlled access policies.
3. **Defense-in-depth:** Five distinct security layers from TLS to PII masking.
4. **Per-tenant cryptographic isolation:** Tenant ID derived from signed JWT; cannot be forged or escalated.
5. **Vault integration:** No secrets in code or version control; supports dynamic secret rotation.
6. **Constitution signing:** Tamper-evident memory operations with tenant-scoped keys.
7. **Comprehensive audit logging:** All security-relevant events logged with full context.

### 12.2 Recommendations

| Priority | ID | Recommendation | Rationale |
|---|---|---|---|
| High | SEC-001 | Enable TLS for all internal service-to-service communication | Currently deployment-dependent; should be default |
| High | SEC-002 | Add automated dependency vulnerability scanning to CI | Supply chain risk mitigation |
| High | SEC-003 | Validate constitution signing key rotation mechanism | Key management needs end-to-end validation |
| Medium | SEC-004 | Implement certificate pinning for SomaFractalMemory and SomaAgent01 connections | Prevent MITM on internal links |
| Medium | SEC-005 | Add security-focused integration tests (auth bypass, tenant isolation) | Validate security controls continuously |
| Medium | SEC-006 | Implement request signing for service-to-service calls | Prevent replay attacks on internal APIs |
| Low | SEC-007 | Add Web Application Firewall (WAF) rules for common attack patterns | Defense-in-depth for the API layer |
| Low | SEC-008 | Implement automated secret rotation for all Vault-managed secrets | Reduce manual operational burden |

---

*End of assessment. This security assessment was conducted with reference to ISO/IEC 27001:2022 controls and OWASP ASVS 4.0 requirements.*
