# SRS-02: Subscription & Billing Module

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Standard:** ISO/IEC/IEEE 29148:2018 Compatible  
**Module:** Subscription & Billing Subsystem (Lago Integration)

---

## 1. Overview

The Subscription & Billing module manages subscription tiers, usage metering, and billing integration with Lago for the SomaBrain SaaS platform.

### 1.1 Scope

| Component | Description |
|-----------|-------------|
| SubscriptionTier | Tier definitions (Free/Starter/Pro/Enterprise) |
| TenantSubscription | Tenant-to-tier mapping |
| UsageRecord | Usage metering data |
| LagoClient | Billing API integration |

---

## 2. How to Subscribe (User Journey)

```mermaid
flowchart TD
    A[User Visits Platform] --> B{Has Account?}
    B -->|No| C[Register via Keycloak/Google OAuth]
    B -->|Yes| D[Login to Dashboard]
    C --> D
    
    D --> E[View Current Plan]
    E --> F{Want to Upgrade?}
    F -->|No| G[Continue Using Free Tier]
    F -->|Yes| H[Click 'Upgrade Plan']
    
    H --> I[View Tier Comparison]
    
    subgraph TierSelection["Select Subscription Tier"]
        I --> J{Select Tier}
        J --> K[Free: $0/mo]
        J --> L[Starter: $49/mo]
        J --> M[Pro: $199/mo]
        J --> N[Enterprise: Custom]
    end
    
    K --> O[No Payment Needed]
    L --> P[Enter Payment Details]
    M --> P
    N --> Q[Contact Sales]
    
    P --> R[Lago Creates Subscription]
    R --> S[Webhook: subscription.started]
    S --> T[TenantSubscription Updated]
    T --> U[Access New Features ✓]
    
    O --> U
    Q --> V[Sales Contact Process]
```

---

## 3. How to Create a Tenant (God Mode Admin)

```mermaid
flowchart TD
    A[God Mode Admin] --> B[Login via Keycloak SSO]
    B --> C[Navigate to /platform/tenants]
    C --> D[View All Tenants Dashboard]
    D --> E[Click '+ Create Tenant']
    
    subgraph TenantForm["Tenant Creation Form"]
        E --> F[Enter Organization Name]
        F --> G[Enter Billing Email]
        G --> H[Select Initial Tier]
        H --> I[Configure Custom Limits?]
        I --> J[Set Trial Period?]
        J --> K[Mark as Exempt?]
    end
    
    K --> L[Submit Form]
    L --> M[POST /api/v1/admin/tenants]
    
    subgraph Backend["Backend Processing"]
        M --> N[Create TenantMetadata in Redis]
        N --> O[Lago: Create Customer]
        O --> P[Lago: Assign Subscription]
        P --> Q[Create TenantUser for Admin]
        Q --> R[Send Welcome Email]
    end
    
    R --> S[Tenant Active ✓]
    S --> T[Display Success Message]
```

---

## 4. Subscription Lifecycle Flowchart

```mermaid
flowchart TD
    subgraph Trial["Trial Period"]
        A[New Subscription] --> B[Trial Started]
        B --> C{Trial Expired?}
        C -->|No| D[Continue Trial]
        D --> C
        C -->|Yes| E{Payment Added?}
        E -->|Yes| F[Convert to Active]
        E -->|No| G[Downgrade to Free]
    end
    
    subgraph Active["Active Subscription"]
        F --> H[Subscription Active]
        H --> I{Invoice Due}
        I --> J[Lago: Generate Invoice]
        J --> K{Payment Successful?}
        K -->|Yes| L[Invoice Paid]
        L --> H
        K -->|No| M[Payment Failed]
    end
    
    subgraph Dunning["Dunning Process"]
        M --> N[Status: past_due]
        N --> O[Send Payment Reminder]
        O --> P{Retry Payment}
        P -->|Success| L
        P -->|Fail x3| Q[Status: cancelled]
        Q --> R[Suspend Tenant Access]
    end
    
    subgraph Changes["Plan Changes"]
        H --> S{User Action}
        S -->|Upgrade| T[Lago: Change Plan]
        T --> U[Proration Calculated]
        U --> V[New Tier Active]
        V --> H
        S -->|Downgrade| W[Queue for End of Period]
        W --> X[Apply at Renewal]
        X --> H
        S -->|Cancel| Y[Mark for Cancellation]
        Y --> Z[Access Until Period End]
        Z --> Q
    end
```

---

## 5. Lago Integration Sequence Diagram

```mermaid
sequenceDiagram
    participant Admin as God Mode Admin
    participant API as SomaBrain API
    participant TM as TenantManager
    participant Lago
    participant DB as PostgreSQL
    participant Redis
    
    Admin->>API: POST /api/admin/tenants (org_name, tier)
    API->>TM: create_tenant(display_name, tier)
    TM->>Redis: Store TenantMetadata
    Redis-->>TM: OK
    
    API->>Lago: POST /customers (external_id=tenant_id)
    Lago-->>API: customer_id
    
    API->>Lago: POST /subscriptions (customer_id, plan_code)
    Lago-->>API: subscription_id
    
    API->>DB: INSERT TenantSubscription
    DB-->>API: OK
    
    API-->>Admin: Tenant Created ✓
    
    Note over Lago: Later... Usage Events
    
    API->>Lago: POST /events (transaction_id, code, properties)
    Lago-->>API: 200 OK
    
    Note over Lago: End of Billing Period
    
    Lago->>API: Webhook: invoice.created
    API->>DB: Store Invoice Reference
    
    Lago->>API: Webhook: invoice.paid
    API->>TM: Confirm Subscription Active
```

---

## 6. UML Class Diagram (Proposed Models)

```mermaid
classDiagram
    class SubscriptionTier {
        +str tier_id PK
        +str name
        +Decimal monthly_price
        +int api_calls_limit
        +int memory_ops_limit
        +int embeddings_limit
        +Dict features
        +bool is_active
        +datetime created_at
    }
    
    class TenantSubscription {
        +int id PK
        +str tenant_id FK
        +str tier_id FK
        +str lago_subscription_id
        +str lago_customer_id
        +str status
        +datetime started_at
        +datetime ends_at
        +datetime trial_ends_at
        +datetime cancelled_at
    }
    
    class UsageRecord {
        +int id PK
        +str tenant_id FK
        +str metric_code
        +int quantity
        +datetime timestamp
        +str lago_event_id
        +bool synced_to_lago
    }
    
    class Invoice {
        +int id PK
        +str tenant_id FK
        +str lago_invoice_id
        +Decimal amount_cents
        +str currency
        +str status
        +datetime issued_at
        +datetime paid_at
        +str pdf_url
    }
    
    class QuotaInfo {
        +str tenant_id
        +int daily_limit
        +int remaining
        +int used_today
        +datetime reset_at
        +bool is_exempt
    }
    
    TenantSubscription --> SubscriptionTier : belongs_to
    UsageRecord --> TenantSubscription : tracked_for
    Invoice --> TenantSubscription : billed_to
    QuotaInfo ..> TenantSubscription : derived_from
```

---

## 7. Tier Structure

| Tier | API Calls/mo | Memory Ops/mo | Embeddings/mo | Price/mo | Features |
|------|-------------|---------------|---------------|----------|----------|
| **Free** | 1,000 | 500 | 100 | $0 | Basic memory, Community support |
| **Starter** | 10,000 | 5,000 | 1,000 | $49 | All Free + Priority support |
| **Pro** | 100,000 | 50,000 | 10,000 | $199 | All Starter + Custom models, SSO |
| **Enterprise** | Unlimited | Unlimited | Unlimited | Custom | All Pro + Dedicated support, SLA |

---

## 8. Functional Requirements

| REQ-ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| REQ-SUB-001 | Define subscription tiers (Free, Starter, Pro, Enterprise) | CRITICAL | ❌ MISSING |
| REQ-SUB-002 | Each tier MUST define feature flags and limits | CRITICAL | ❌ MISSING |
| REQ-SUB-003 | TenantSubscription model linking tenant to tier | CRITICAL | ❌ MISSING |
| REQ-SUB-004 | Subscription status (active, past_due, cancelled, trial) | HIGH | ❌ MISSING |
| REQ-SUB-005 | Trial period support with expiration | HIGH | ❌ MISSING |
| REQ-SUB-006 | Tier upgrade/downgrade API | HIGH | ❌ MISSING |
| REQ-SUB-007 | Proration handling on mid-cycle changes | MEDIUM | ❌ MISSING |
| REQ-BILL-001 | Lago API client for Python/Django | CRITICAL | ❌ MISSING |
| REQ-BILL-002 | Customer creation in Lago on tenant creation | CRITICAL | ❌ MISSING |
| REQ-BILL-003 | Subscription assignment in Lago | CRITICAL | ❌ MISSING |
| REQ-BILL-004 | Usage event ingestion to Lago | CRITICAL | ❌ MISSING |
| REQ-BILL-005 | Invoice retrieval from Lago | HIGH | ❌ MISSING |
| REQ-BILL-006 | Webhook receiver for Lago events | HIGH | ❌ MISSING |
| REQ-BILL-007 | Billing settings in `settings.py` | HIGH | ❌ MISSING |

---

## 9. Lago Webhook Events

```mermaid
flowchart LR
    subgraph LagoEvents["Lago Webhook Events"]
        A[customer.created]
        B[subscription.started]
        C[subscription.terminated]
        D[invoice.created]
        E[invoice.paid]
        F[invoice.payment_failed]
    end
    
    subgraph SomaBrainActions["SomaBrain Actions"]
        A --> G[Create TenantBillingRecord]
        B --> H[Activate Tenant]
        C --> I[Suspend Tenant]
        D --> J[Store Invoice Reference]
        E --> K[Update Payment Status]
        F --> L[Trigger Dunning Flow]
    end
```

---

## 10. Usage Metering Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as SomaBrain API
    participant Meter as UsageMeter
    participant DB as PostgreSQL
    participant Sync as LagoSyncJob
    participant Lago
    
    Client->>API: POST /api/memory/store
    API->>Meter: record_usage(tenant_id, "memory_op", 1)
    Meter->>DB: INSERT UsageRecord
    
    Note over Sync: Every 5 minutes (configurable)
    
    Sync->>DB: SELECT unsynced UsageRecords
    DB-->>Sync: batch of records
    
    loop For each batch
        Sync->>Lago: POST /events (batch)
        Lago-->>Sync: 200 OK
        Sync->>DB: UPDATE UsageRecord SET synced=true
    end
```

---

## 11. Key Files (To Be Created)

| File | Purpose | Status |
|------|---------|--------|
| `somabrain/billing/__init__.py` | Billing module init | ❌ MISSING |
| `somabrain/billing/models.py` | Django models for subscriptions | ❌ MISSING |
| `somabrain/billing/lago_client.py` | Lago API wrapper | ❌ MISSING |
| `somabrain/billing/webhooks.py` | Lago webhook handlers | ❌ MISSING |
| `somabrain/billing/usage_meter.py` | Usage metering service | ❌ MISSING |
| `somabrain/api/endpoints/billing.py` | Billing API endpoints | ❌ MISSING |

---

## 12. Existing Files (Partial)

| File | Description | Relevant Content |
|------|-------------|-----------------|
| [quotas.py](file:///Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain/somabrain/quotas.py) | Per-tenant quota enforcement | `QuotaManager`, `QuotaInfo` |
| [models.py](file:///Users/macbookpro201916i964gb1tb/Documents/GitHub/somabrain/somabrain/models.py) | Django models | `TokenLedger` (partial usage tracking) |

---

*Document prepared by ALL 7 PERSONAS: 🎓 PhD Developer, 🔍 PhD Analyst, ✅ PhD QA, 📚 ISO Documenter, 🔒 Security Auditor, ⚡ Performance Engineer, 🎨 UX Consultant + Django Architect/Expert/Evangelist*
