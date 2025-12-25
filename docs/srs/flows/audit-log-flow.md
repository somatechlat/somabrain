# Audit Log Flow

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Type:** End-to-End Flow Documentation

---

## 1. Overview

Complete audit log flows: view events, filter, search, export.

---

## 2. View Audit Log Flow

```mermaid
flowchart TD
    A[Navigate to /admin/audit] --> B[API: GET /api/admin/audit]
    B --> C[Fetch OutboxEvent + AuditLog]
    C --> D[Display Event Table]
    D --> E{Actions}
    E -->|Filter| F[Apply Filters]
    E -->|Search| G[Search Events]
    E -->|Export| H[Download CSV/JSON]
    E -->|View| I[Event Detail Modal]
```

---

## 3. Audit Log Sequence

```mermaid
sequenceDiagram
    participant Admin
    participant UI
    participant API
    participant DB as PostgreSQL
    participant Kafka
    
    Admin->>UI: Navigate to Audit Log
    UI->>API: GET /api/admin/audit?page=1&limit=50
    API->>DB: SELECT FROM outbox_events
    DB-->>API: Events
    API-->>UI: Paginated Events
    UI->>Admin: Display Table
    
    Admin->>UI: Click Event Row
    UI->>API: GET /api/admin/audit/{event_id}
    API->>DB: Fetch Full Event
    DB-->>API: Event Details
    API-->>UI: Full Payload
    UI->>Admin: Show Detail Modal
```

---

## 4. Filter Audit Events Flow

```mermaid
flowchart TD
    A[Open Filter Panel] --> B{Filter Options}
    B --> C[Date Range]
    B --> D[Event Type]
    B --> E[Actor/User]
    B --> F[Resource/Entity]
    B --> G[Status]
    
    C --> H[Apply Filters]
    D --> H
    E --> H
    F --> H
    G --> H
    
    H --> I[GET /api/admin/audit?filters=...]
    I --> J[Update Table View]
```

---

## 5. Export Audit Log Flow

```mermaid
flowchart TD
    A[Click 'Export'] --> B{Select Format}
    B -->|CSV| C[Generate CSV]
    B -->|JSON| D[Generate JSON]
    B -->|PDF Report| E[Generate PDF]
    
    C --> F[POST /api/admin/audit/export]
    D --> F
    E --> F
    
    F --> G{Large Dataset?}
    G -->|No| H[Direct Download]
    G -->|Yes| I[Background Job]
    I --> J[Email Download Link]
```

---

## 6. Audit Event Types

| Event Type | Description | Example |
|------------|-------------|---------|
| `user.login` | User authentication | Login via SSO |
| `user.logout` | Session ended | Manual logout |
| `tenant.created` | New tenant | Admin created org |
| `tenant.suspended` | Tenant paused | Payment failure |
| `memory.stored` | Memory created | API call |
| `subscription.changed` | Plan changed | Upgrade to Pro |
| `admin.action` | Admin operation | Impersonation |

---

## 7. Audit Retention Policy

```mermaid
flowchart LR
    A[Event Created] --> B[Active: 90 days]
    B --> C[Archived: 1 year]
    C --> D[Deleted: After 1 year]
```

---

*Document prepared by ALL 7 PERSONAS per VIBE Coding Rules v5.1*
