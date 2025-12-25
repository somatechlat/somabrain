# User Management Flow

**Document Version:** 1.0.0  
**Date:** 2025-12-24  
**Type:** End-to-End Flow Documentation

---

## 1. Overview

Complete user management flows: invite users, assign roles, remove users, update profiles.

---

## 2. Invite User Flow

```mermaid
flowchart TD
    A[Navigate to /admin/users] --> B[Click 'Invite User']
    B --> C[Enter Email Address]
    C --> D[Select Role: Admin/Editor/Viewer]
    D --> E[Click 'Send Invite']
    E --> F[POST /api/users/invite]
    F --> G[Create Pending User]
    G --> H[Create Keycloak User]
    H --> I[Send Invitation Email]
    I --> J[Show Success ✓]
```

---

## 3. Invite Acceptance Sequence

```mermaid
sequenceDiagram
    participant Invitee
    participant Email
    participant UI
    participant API
    participant KC as Keycloak
    
    Invitee->>Email: Receive Invite Email
    Invitee->>Email: Click 'Accept Invitation'
    Email->>UI: /invite/accept?token=xxx
    UI->>API: GET /api/users/invite/verify?token=xxx
    API->>API: Validate Token
    API-->>UI: {valid: true, email: "..."}
    UI->>Invitee: Set Password Form
    Invitee->>UI: Enter Password
    UI->>API: POST /api/users/invite/accept
    API->>KC: Set User Password
    KC-->>API: OK
    API->>API: Activate User
    API-->>UI: Success
    UI->>Invitee: Redirect to Login
```

---

## 4. Role Assignment Flow

```mermaid
flowchart TD
    A[Select User from List] --> B[Click 'Edit Role']
    B --> C[Show Role Dropdown]
    C --> D{Select New Role}
    D -->|Admin| E[Full Access]
    D -->|Editor| F[Create/Edit Access]
    D -->|Viewer| G[Read-Only Access]
    E --> H[POST /api/users/{id}/role]
    F --> H
    G --> H
    H --> I[Update Keycloak Role]
    I --> J[Audit Log Entry]
    J --> K[Show Success ✓]
```

---

## 5. Remove User Flow

```mermaid
flowchart TD
    A[Select User] --> B[Click 'Remove']
    B --> C[Confirm Dialog]
    C --> D{Is Last Admin?}
    D -->|Yes| E[Error: Cannot Remove]
    D -->|No| F{Confirm?}
    F -->|No| G[Cancel]
    F -->|Yes| H[DELETE /api/users/{id}]
    H --> I[Deactivate in Keycloak]
    I --> J[Transfer Ownership?]
    J --> K[Audit Log Entry]
    K --> L[Show Success ✓]
```

---

## 6. User List State Machine

```mermaid
stateDiagram-v2
    [*] --> Loading
    Loading --> Loaded: Users Fetched
    Loaded --> Inviting: Click Invite
    Inviting --> Loaded: Invite Sent
    Loaded --> Editing: Select User
    Editing --> Loaded: Save/Cancel
    Loaded --> Removing: Click Remove
    Removing --> Loaded: Confirmed
```

---

## 7. Role Permissions Matrix

| Permission | Admin | Editor | Viewer |
|------------|-------|--------|--------|
| View Dashboard | ✓ | ✓ | ✓ |
| Use Chat | ✓ | ✓ | ✓ |
| Create Memory | ✓ | ✓ | ✗ |
| Delete Memory | ✓ | ✓ | ✗ |
| Manage Users | ✓ | ✗ | ✗ |
| View Billing | ✓ | ✗ | ✗ |
| Change Settings | ✓ | ✗ | ✗ |

---

## 8. Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `409 User Exists` | Email already registered | Use different email |
| `403 Cannot Remove` | Last admin in tenant | Assign another admin first |
| `400 Invalid Role` | Unknown role name | Select valid role |

---

*Document prepared by ALL 7 PERSONAS per VIBE Coding Rules v5.1*
