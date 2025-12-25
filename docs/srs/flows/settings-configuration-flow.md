# Settings & Configuration Flow

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Type:** End-to-End Flow Documentation

---

## 1. Overview

Complete settings flows: tenant config, API keys, integrations, themes.

---

## 2. Settings Navigation

```mermaid
flowchart LR
    A[/settings] --> B[General]
    A --> C[Subscription]
    A --> D[Billing]
    A --> E[Users]
    A --> F[API Keys]
    A --> G[Integrations]
    A --> H[Appearance]
```

---

## 3. Update Tenant Settings Flow

```mermaid
flowchart TD
    A[Navigate to /settings/general] --> B[Load Current Settings]
    B --> C[Display Form]
    C --> D{Edit Fields}
    D --> E[Organization Name]
    D --> F[Billing Email]
    D --> G[Contact Person]
    D --> H[Timezone]
    E --> I[Click 'Save']
    F --> I
    G --> I
    H --> I
    I --> J[PATCH /api/settings]
    J --> K[Update TenantMetadata]
    K --> L[Show Success ✓]
```

---

## 4. Manage API Keys Flow

```mermaid
flowchart TD
    A[Navigate to /settings/api-keys] --> B[List Existing Keys]
    B --> C{Action}
    C -->|Create| D[Click '+ New Key']
    D --> E[Enter Key Name]
    E --> F[Select Permissions]
    F --> G[Set Expiration]
    G --> H[POST /api/settings/api-keys]
    H --> I[Generate Key]
    I --> J[Show Key ONCE]
    J --> K[Copy to Clipboard]
    
    C -->|Revoke| L[Select Key]
    L --> M[Click 'Revoke']
    M --> N[Confirm Dialog]
    N --> O[DELETE /api/settings/api-keys/{id}]
    O --> P[Key Invalidated ✓]
```

---

## 5. API Key Sequence

```mermaid
sequenceDiagram
    participant User
    participant UI
    participant API
    participant Redis
    
    User->>UI: Create API Key
    UI->>API: POST /api/settings/api-keys
    API->>API: Generate Secure Key
    API->>Redis: Store Key Hash
    Redis-->>API: OK
    API-->>UI: {key: "YOUR_API_KEY_HERE", key_id: "..."}
    UI->>User: Display Key (show once)
    User->>UI: Copy Key
    
    Note over User: Later usage
    User->>API: Request with X-API-Key
    API->>Redis: Validate Key Hash
    Redis-->>API: Valid
    API->>User: Process Request
```

---

## 6. Configure Integrations Flow

```mermaid
flowchart TD
    A[Navigate to /settings/integrations] --> B[List Available Integrations]
    B --> C{Select Integration}
    C -->|Slack| D[Enter Webhook URL]
    C -->|GitHub| E[OAuth Connect]
    C -->|Custom Webhook| F[Enter Endpoint]
    D --> G[Test Connection]
    E --> H[Authorize App]
    F --> G
    G --> I{Test Passed?}
    I -->|No| J[Show Error]
    I -->|Yes| K[Save Integration]
    H --> K
    K --> L[Integration Active ✓]
```

---

## 7. Theme Selection Flow

```mermaid
flowchart TD
    A[Navigate to /settings/appearance] --> B[Show Theme Options]
    B --> C{Select Theme}
    C -->|Light| D[Apply Light Theme]
    C -->|Dark| E[Apply Dark Theme]
    C -->|System| F[Match OS Preference]
    D --> G[Save Preference]
    E --> G
    F --> G
    G --> H[PATCH /api/settings/preferences]
    H --> I[Update UI Immediately]
```

---

## 8. Settings State Machine

```mermaid
stateDiagram-v2
    [*] --> Loading
    Loading --> Viewing: Settings Loaded
    Viewing --> Editing: Change Field
    Editing --> Saving: Submit
    Saving --> Viewing: Success
    Saving --> Editing: Error
    Viewing --> [*]: Navigate Away
```

---

*Document prepared by ALL 7 PERSONAS per VIBE Coding Rules v5.1*
