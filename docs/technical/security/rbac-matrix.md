# Role-Based Access Control (RBAC) Matrix

**Purpose**: Define comprehensive role-based access control policies for SomaBrain environments, including permissions, responsibilities, and security boundaries.

**Audience**: Security architects, system administrators, and compliance teams implementing SomaBrain access controls.

**Prerequisites**: Understanding of [Architecture](../architecture.md) and [Secrets Policy](secrets-policy.md).

---

## RBAC Overview

SomaBrain implements multi-layered role-based access control across application, infrastructure, and administrative functions:

### Access Control Layers

**Application Layer**: API endpoints, memory operations, and tenant-specific resources
**Infrastructure Layer**: Container orchestration, networking, and storage access
**Administrative Layer**: System configuration, monitoring, and operational tasks
**Security Layer**: Secret management, audit access, and security controls

### RBAC Principles

**Principle of Least Privilege**: Users receive minimum permissions required for their role
**Separation of Duties**: Critical operations require multiple approvals or roles
**Role Inheritance**: Higher privilege roles inherit lower privilege permissions
**Temporal Access**: Time-limited access for elevated operations
**Audit Trail**: Complete logging of all access decisions and privilege escalations

---

## Role Definitions

### Application Roles

```yaml
# Application-level roles for SomaBrain API access
application_roles:

  memory_reader:
    description: "Read-only access to memory operations"
    permissions:
      - memory:read
      - memory:search
      - tenant:read_own
    api_endpoints:
      - "GET /health"
      - "POST /recall"
      - "GET /memories/{id}"
      - "POST /search"
    rate_limits:
      requests_per_minute: 60
      burst_limit: 10
    examples:
      - Analytics users
      - Read-only integrations
      - Monitoring systems

  memory_writer:
    description: "Full memory operations within tenant scope"
    inherits: [memory_reader]
    permissions:
      - memory:write
      - memory:update
    api_endpoints:
      - "POST /remember"
      - "PUT /memories/{id}"
      - "PATCH /memories/{id}/metadata"
    rate_limits:
      requests_per_minute: 300
      burst_limit: 50
    examples:
      - Application services
      - Content management systems
      - User-facing applications

  memory_admin:
    description: "Full memory management including deletion"
    inherits: [memory_writer]
    permissions:
      - memory:delete
      - memory:export
      - tenant:manage_own
    api_endpoints:
      - "DELETE /memories/{id}"
      - "DELETE /memories/batch"
      - "GET /export"
      - "POST /import"
    rate_limits:
      requests_per_minute: 1000
      burst_limit: 100
    requires_mfa: true
    examples:
      - Data administrators
      - Application owners

  reasoning_user:
    description: "Access to cognitive reasoning capabilities"
    inherits: [memory_reader]
    permissions:
      - reasoning:basic
      - reasoning:contextual
      - reasoning:temporal
    api_endpoints:
      - "POST /reason"
      - "POST /analyze/clusters"
      - "GET /memories/{id}/network"
    rate_limits:
      requests_per_minute: 100
      burst_limit: 20
    examples:
      - AI applications
      - Decision support systems
      - Research platforms

  reasoning_admin:
    description: "Advanced reasoning and analytics access"
    inherits: [reasoning_user, memory_admin]
    permissions:
      - reasoning:advanced
      - reasoning:cross_tenant
      - analytics:advanced
    api_endpoints:
      - "POST /reason/advanced"
      - "POST /analyze/cross_tenant"
      - "GET /analytics/patterns"
    requires_approval: true
    examples:
      - Research teams
      - System analysts
```

### Infrastructure Roles

```yaml
# Infrastructure and operational roles
infrastructure_roles:

  container_viewer:
    description: "Read-only access to container status and logs"
    permissions:
      - containers:read
      - logs:read
      - metrics:read
    k8s_permissions:
      - apiGroups: [""]
        resources: ["pods", "services", "configmaps"]
        verbs: ["get", "list", "watch"]
      - apiGroups: ["apps"]
        resources: ["deployments", "replicasets"]
        verbs: ["get", "list", "watch"]
    docker_permissions:
      - "docker ps"
      - "docker logs"
      - "docker stats"
    examples:
      - Developers
      - Support staff
      - Monitoring tools

  container_operator:
    description: "Container lifecycle management"
    inherits: [container_viewer]
    permissions:
      - containers:restart
      - containers:scale
      - containers:update
    k8s_permissions:
      - apiGroups: ["apps"]
        resources: ["deployments"]
        verbs: ["patch", "update"]
      - apiGroups: [""]
        resources: ["pods"]
        verbs: ["delete"]
    docker_permissions:
      - "docker restart"
      - "docker compose up/down"
    requires_approval: true
    examples:
      - DevOps engineers
      - Site reliability engineers

  infrastructure_admin:
    description: "Full infrastructure management"
    inherits: [container_operator]
    permissions:
      - infrastructure:full
      - networking:manage
      - storage:manage
    k8s_permissions:
      - apiGroups: ["*"]
        resources: ["*"]
        verbs: ["*"]
    requires_mfa: true
    break_glass: true
    examples:
      - Platform engineers
      - Infrastructure architects
```

### Administrative Roles

```yaml
# System and security administration roles
administrative_roles:

  tenant_viewer:
    description: "Read-only access to tenant information"
    permissions:
      - tenant:read_all
      - metrics:read_tenant
      - usage:read
    api_endpoints:
      - "GET /admin/tenants"
      - "GET /admin/tenants/{id}/stats"
      - "GET /admin/usage"
    examples:
      - Customer success
      - Billing systems
      - Usage analytics

  tenant_admin:
    description: "Tenant lifecycle and configuration management"
    inherits: [tenant_viewer]
    permissions:
      - tenant:create
      - tenant:update
      - tenant:configure
      - tenant:suspend
    api_endpoints:
      - "POST /admin/tenants"
      - "PUT /admin/tenants/{id}"
      - "POST /admin/tenants/{id}/suspend"
    requires_approval: true
    examples:
      - Account managers
      - Customer onboarding

  security_analyst:
    description: "Security monitoring and incident response"
    permissions:
      - audit:read
      - security:monitor
      - incidents:investigate
    api_endpoints:
      - "GET /admin/audit"
      - "GET /admin/security/events"
      - "POST /admin/security/investigate"
    vault_permissions:
      - path: "audit/*"
        capabilities: ["read"]
      - path: "somabrain/metadata/*"
        capabilities: ["read", "list"]
    examples:
      - Security operations center
      - Compliance team

  security_admin:
    description: "Full security administration"
    inherits: [security_analyst]
    permissions:
      - security:configure
      - secrets:manage
      - rbac:manage
    api_endpoints:
      - "PUT /admin/security/policies"
      - "POST /admin/rbac/roles"
    vault_permissions:
      - path: "*"
        capabilities: ["*"]
    requires_mfa: true
    requires_approval: true
    examples:
      - Security architects
      - CISO team

  system_admin:
    description: "Full system administration (break glass)"
    inherits: [infrastructure_admin, security_admin, tenant_admin]
    permissions:
      - system:full
      - break_glass:all
    requires_mfa: true
    requires_approval: true
    time_limited: "4h"
    emergency_only: true
    examples:
      - Emergency response
      - Critical incident resolution
```

---

## Permission Matrix

### API Endpoint Permissions

| Endpoint | memory_reader | memory_writer | memory_admin | reasoning_user | tenant_admin | security_admin |
|----------|:-------------:|:-------------:|:------------:|:--------------:|:------------:|:--------------:|
| `GET /health` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /remember` | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ |
| `POST /recall` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `DELETE /memories/{id}` | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| `POST /reason` | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| `GET /admin/tenants` | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| `POST /admin/tenants` | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| `GET /admin/audit` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

### Resource-Level Permissions

```yaml
# Detailed resource permissions
resource_permissions:

  memory_operations:
    read:
      roles: [memory_reader, memory_writer, memory_admin, reasoning_user]
      conditions:
        - tenant_scope: own
        - data_classification: non_sensitive

    write:
      roles: [memory_writer, memory_admin]
      conditions:
        - tenant_scope: own
        - content_size_limit: "10MB"
        - rate_limit: "1000/hour"

    delete:
      roles: [memory_admin]
      conditions:
        - tenant_scope: own
        - requires_confirmation: true
        - audit_retention: "7_years"

    cross_tenant_read:
      roles: [reasoning_admin, system_admin]
      conditions:
        - requires_approval: true
        - business_justification: required
        - time_limited: "24h"

  tenant_management:
    create:
      roles: [tenant_admin, system_admin]
      conditions:
        - business_case_required: true
        - resource_quota_defined: true

    update:
      roles: [tenant_admin, system_admin]
      conditions:
        - change_approval: required
        - impact_assessment: required

    delete:
      roles: [system_admin]
      conditions:
        - two_person_rule: true
        - data_export_completed: true
        - legal_approval: required

  infrastructure:
    container_restart:
      roles: [container_operator, infrastructure_admin, system_admin]
      conditions:
        - business_hours_only: true
        - change_window: preferred

    infrastructure_modify:
      roles: [infrastructure_admin, system_admin]
      conditions:
        - change_approval: required
        - rollback_plan: required
        - maintenance_window: required

  security:
    audit_access:
      roles: [security_analyst, security_admin, system_admin]
      conditions:
        - incident_ticket: required
        - retention_compliance: enforced

    security_config:
      roles: [security_admin, system_admin]
      conditions:
        - peer_review: required
        - security_impact_assessment: required
        - testing_completed: true
```

---

## Access Control Implementation

### Kubernetes RBAC Configuration

```yaml
# k8s/rbac/somabrain-roles.yml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: somabrain
  name: container-viewer
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets", "daemonsets"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get", "list"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: somabrain
  name: container-operator
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["delete"]
- apiGroups: [""]
  resources: ["pods/exec"]
  verbs: ["create"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: infrastructure-admin
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]

---
# Role bindings for users and service accounts
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developers-container-viewers
  namespace: somabrain
subjects:
- kind: User
  name: dev-team
  apiGroup: rbac.authorization.k8s.io
- kind: ServiceAccount
  name: monitoring-agent
  namespace: somabrain
roleRef:
  kind: Role
  name: container-viewer
  apiGroup: rbac.authorization.k8s.io

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: devops-container-operators
  namespace: somabrain
subjects:
- kind: User
  name: devops-team
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: container-operator
  apiGroup: rbac.authorization.k8s.io
```

### SomaBrain Application RBAC

```python
# somabrain/security/rbac.py
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional
import jwt
from functools import wraps

class Permission(Enum):
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_DELETE = "memory:delete"
    REASONING_BASIC = "reasoning:basic"
    REASONING_ADVANCED = "reasoning:advanced"
    TENANT_READ = "tenant:read"
    TENANT_MANAGE = "tenant:manage"
    ADMIN_FULL = "admin:full"

@dataclass
class Role:
    name: str
    permissions: List[Permission]
    inherits: List[str] = None
    requires_mfa: bool = False
    requires_approval: bool = False
    time_limited: Optional[str] = None

class RBACManager:
    def __init__(self):
        self.roles = self._load_roles()
        self.user_roles = {}

    def _load_roles(self) -> Dict[str, Role]:
        return {
            "memory_reader": Role(
                name="memory_reader",
                permissions=[Permission.MEMORY_READ, Permission.TENANT_READ],
                requires_mfa=False
            ),
            "memory_writer": Role(
                name="memory_writer",
                permissions=[Permission.MEMORY_WRITE],
                inherits=["memory_reader"],
                requires_mfa=False
            ),
            "memory_admin": Role(
                name="memory_admin",
                permissions=[Permission.MEMORY_DELETE],
                inherits=["memory_writer"],
                requires_mfa=True
            ),
            "reasoning_user": Role(
                name="reasoning_user",
                permissions=[Permission.REASONING_BASIC],
                inherits=["memory_reader"],
                requires_mfa=False
            ),
            "system_admin": Role(
                name="system_admin",
                permissions=[Permission.ADMIN_FULL],
                inherits=["memory_admin", "reasoning_user"],
                requires_mfa=True,
                requires_approval=True,
                time_limited="4h"
            )
        }

    def get_effective_permissions(self, role_name: str) -> List[Permission]:
        """Get all permissions including inherited ones"""
        role = self.roles.get(role_name)
        if not role:
            return []

        permissions = set(role.permissions)

        # Add inherited permissions
        if role.inherits:
            for inherited_role in role.inherits:
                permissions.update(self.get_effective_permissions(inherited_role))

        return list(permissions)

    def check_permission(self, user_id: str, tenant_id: str, permission: Permission) -> bool:
        """Check if user has specific permission for tenant"""
        user_roles = self.get_user_roles(user_id, tenant_id)

        for role_name in user_roles:
            effective_permissions = self.get_effective_permissions(role_name)
            if permission in effective_permissions:
                return True

        return False

    def requires_mfa(self, user_id: str, tenant_id: str) -> bool:
        """Check if any user role requires MFA"""
        user_roles = self.get_user_roles(user_id, tenant_id)

        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role and role.requires_mfa:
                return True

        return False

def require_permission(permission: Permission):
    """Decorator to enforce permission requirements"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract user and tenant from JWT token
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            try:
                payload = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])
                user_id = payload['user_id']
                tenant_id = payload['tenant_id']
            except:
                return {"error": "Invalid token"}, 401

            # Check permission
            rbac = RBACManager()
            if not rbac.check_permission(user_id, tenant_id, permission):
                return {"error": "Insufficient permissions"}, 403

            # Check MFA requirement
            if rbac.requires_mfa(user_id, tenant_id) and not payload.get('mfa_verified'):
                return {"error": "MFA required"}, 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage in API endpoints
@app.route('/remember', methods=['POST'])
@require_permission(Permission.MEMORY_WRITE)
def remember_endpoint():
    # Implementation here
    pass

@app.route('/admin/tenants', methods=['GET'])
@require_permission(Permission.ADMIN_FULL)
def list_tenants():
    # Implementation here
    pass
```

---

## Multi-Factor Authentication (MFA)

### MFA Requirements by Role

```yaml
# MFA requirements configuration
mfa_requirements:

  standard_roles:
    - memory_reader
    - memory_writer
    - reasoning_user
  mfa_required: false
  authentication_methods:
    - api_key
    - jwt_token

  elevated_roles:
    - memory_admin
    - tenant_admin
    - reasoning_admin
  mfa_required: true
  authentication_methods:
    - totp  # Time-based One-Time Password
    - hardware_key  # YubiKey, etc.
    - sms_backup  # Backup method only

  administrative_roles:
    - security_admin
    - infrastructure_admin
    - system_admin
  mfa_required: true
  mfa_methods_required: 2  # Requires two factors
  authentication_methods:
    - totp
    - hardware_key
    - biometric  # If available
  session_timeout: "30m"
  re_authentication_required: "4h"
```

### MFA Implementation

```python
# somabrain/security/mfa.py
import pyotp
import qrcode
from typing import Optional, Dict, Any

class MFAManager:
    def __init__(self):
        self.totp_secrets = {}  # In production, store in secure database

    def setup_totp(self, user_id: str) -> Dict[str, Any]:
        """Set up TOTP for user"""
        secret = pyotp.random_base32()
        self.totp_secrets[user_id] = secret

        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_id,
            issuer_name="SomaBrain"
        )

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        return {
            "secret": secret,
            "qr_code": qr.make_image(fill_color="black", back_color="white"),
            "backup_codes": self._generate_backup_codes(user_id)
        }

    def verify_totp(self, user_id: str, token: str) -> bool:
        """Verify TOTP token"""
        secret = self.totp_secrets.get(user_id)
        if not secret:
            return False

        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)

    def _generate_backup_codes(self, user_id: str, count: int = 10) -> List[str]:
        """Generate backup recovery codes"""
        import secrets
        codes = []
        for _ in range(count):
            code = '-'.join([secrets.token_hex(2).upper() for _ in range(3)])
            codes.append(code)

        # Store backup codes (hashed) in database
        # Implementation depends on your storage solution

        return codes

# MFA middleware
def require_mfa(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        payload = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])

        user_id = payload['user_id']
        tenant_id = payload['tenant_id']

        rbac = RBACManager()
        if rbac.requires_mfa(user_id, tenant_id):
            # Check if MFA was completed in this session
            if not payload.get('mfa_verified'):
                return {"error": "MFA verification required", "mfa_required": True}, 403

            # Check if MFA verification is still valid (time-based)
            mfa_timestamp = payload.get('mfa_timestamp', 0)
            if time.time() - mfa_timestamp > 14400:  # 4 hours
                return {"error": "MFA verification expired", "mfa_required": True}, 403

        return f(*args, **kwargs)
    return decorated_function
```

---

## Approval Workflows

### Approval Requirements

```yaml
# Approval workflow configuration
approval_workflows:

  tenant_creation:
    required_for:
      - new_tenant_requests
      - tenant_resource_increases
    workflow:
      - step: "business_justification"
        required_info:
          - use_case_description
          - expected_usage_volume
          - compliance_requirements
        approver_role: "business_owner"

      - step: "technical_review"
        required_info:
          - resource_requirements
          - integration_plan
          - security_assessment
        approver_role: "technical_lead"

      - step: "security_approval"
        required_info:
          - security_review_completed
          - rbac_plan_approved
        approver_role: "security_admin"

      - step: "final_approval"
        approver_role: "tenant_admin"
        requires_all_previous: true

  elevated_access:
    required_for:
      - cross_tenant_operations
      - administrative_actions
      - security_configuration
    workflow:
      - step: "request_justification"
        required_info:
          - business_case
          - time_duration
          - specific_permissions_needed
        self_service: true

      - step: "manager_approval"
        approver_role: "team_lead"
        time_limit: "4h"

      - step: "security_review"
        approver_role: "security_analyst"
        required_for_roles: ["system_admin", "security_admin"]

  emergency_access:
    required_for:
      - break_glass_access
      - incident_response
    workflow:
      - step: "incident_declaration"
        required_info:
          - incident_severity
          - impact_description
          - immediate_actions_needed

      - step: "incident_commander_approval"
        approver_role: "incident_commander"
        emergency_bypass: true

      - step: "post_incident_review"
        required: true
        time_limit: "24h_after_access"
        approver_role: "security_admin"
```

### Approval System Implementation

```python
# somabrain/security/approvals.py
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class ApprovalRequest:
    request_id: str
    requester_id: str
    requested_role: str
    tenant_id: str
    justification: str
    duration: Optional[timedelta]
    created_at: datetime
    expires_at: datetime
    status: ApprovalStatus
    approvers: List[str]
    approved_by: List[str] = None

class ApprovalManager:
    def __init__(self):
        self.pending_requests = {}

    def create_request(self, requester_id: str, role: str, tenant_id: str,
                      justification: str, duration: Optional[timedelta] = None) -> str:
        """Create new approval request"""
        request_id = f"req_{int(datetime.now().timestamp())}"

        # Determine required approvers based on role
        required_approvers = self._get_required_approvers(role)

        request = ApprovalRequest(
            request_id=request_id,
            requester_id=requester_id,
            requested_role=role,
            tenant_id=tenant_id,
            justification=justification,
            duration=duration or timedelta(hours=8),
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24),
            status=ApprovalStatus.PENDING,
            approvers=required_approvers,
            approved_by=[]
        )

        self.pending_requests[request_id] = request

        # Send notifications to approvers
        self._notify_approvers(request)

        return request_id

    def approve_request(self, request_id: str, approver_id: str) -> bool:
        """Approve a pending request"""
        request = self.pending_requests.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False

        if approver_id not in request.approvers:
            return False  # Unauthorized approver

        if approver_id not in request.approved_by:
            request.approved_by.append(approver_id)

        # Check if all approvers have approved
        if set(request.approved_by) >= set(request.approvers):
            request.status = ApprovalStatus.APPROVED
            self._grant_temporary_access(request)

        return True

    def _get_required_approvers(self, role: str) -> List[str]:
        """Get list of required approvers for role"""
        approval_matrix = {
            "memory_admin": ["team_lead"],
            "tenant_admin": ["business_owner", "technical_lead"],
            "security_admin": ["security_manager", "ciso"],
            "system_admin": ["security_manager", "ciso", "cto"]
        }
        return approval_matrix.get(role, ["team_lead"])

    def _grant_temporary_access(self, request: ApprovalRequest):
        """Grant temporary access after approval"""
        # Implementation depends on your user management system
        # This would typically:
        # 1. Add role to user's active roles
        # 2. Set expiration time
        # 3. Log the access grant
        # 4. Send confirmation to requester
        pass
```

---

## Audit and Compliance

### Audit Logging Requirements

```yaml
# Audit logging configuration
audit_logging:

  events_to_log:
    authentication:
      - login_success
      - login_failure
      - mfa_verification
      - token_refresh
      - logout

    authorization:
      - permission_granted
      - permission_denied
      - role_assumption
      - privilege_escalation

    data_access:
      - memory_read
      - memory_write
      - memory_delete
      - cross_tenant_access
      - export_operations

    administrative:
      - role_creation
      - role_modification
      - user_role_assignment
      - configuration_changes

    security:
      - approval_requests
      - approval_decisions
      - emergency_access
      - policy_violations

  log_retention:
    security_events: "7_years"
    access_events: "3_years"
    administrative_events: "5_years"
    data_access_events: "7_years"

  compliance_frameworks:
    sox:
      events: ["administrative", "data_access", "financial_data"]
      retention: "7_years"

    gdpr:
      events: ["data_access", "personal_data", "consent"]
      retention: "6_years"
      right_to_erasure: true

    hipaa:
      events: ["all"]
      retention: "6_years"
      encryption_required: true
```

### Compliance Reporting

```python
# somabrain/security/compliance.py
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any

class ComplianceReporter:
    def __init__(self, audit_logger):
        self.audit_logger = audit_logger

    def generate_sox_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate SOX compliance report"""

        # Query audit logs for SOX-relevant events
        events = self.audit_logger.query_events(
            start_date=start_date,
            end_date=end_date,
            event_types=['administrative', 'data_access', 'privilege_escalation']
        )

        report = {
            "report_type": "SOX_404_Compliance",
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_administrative_actions": len([e for e in events if e.type == 'administrative']),
                "privileged_access_events": len([e for e in events if e.type == 'privilege_escalation']),
                "data_access_violations": len([e for e in events if e.severity == 'violation']),
                "unauthorized_access_attempts": len([e for e in events if e.result == 'denied'])
            },
            "key_controls": {
                "segregation_of_duties": self._check_segregation_of_duties(events),
                "least_privilege": self._check_least_privilege_compliance(events),
                "access_review": self._check_access_review_compliance(events),
                "audit_trail": self._check_audit_trail_completeness(events)
            },
            "violations": self._identify_compliance_violations(events),
            "recommendations": self._generate_recommendations(events)
        }

        return report

    def generate_rbac_effectiveness_report(self) -> Dict[str, Any]:
        """Generate RBAC effectiveness analysis"""

        # Analyze role usage and effectiveness
        role_usage = self._analyze_role_usage()
        permission_effectiveness = self._analyze_permission_effectiveness()

        return {
            "rbac_effectiveness": {
                "role_utilization": role_usage,
                "permission_coverage": permission_effectiveness,
                "over_privileged_users": self._identify_over_privileged_users(),
                "under_utilized_roles": self._identify_under_utilized_roles(),
                "recommended_optimizations": self._recommend_rbac_optimizations()
            }
        }
```

---

## Security Best Practices

### Access Control Guidelines

1. **Regular Access Reviews**: Conduct quarterly reviews of user roles and permissions
2. **Just-in-Time Access**: Implement time-limited access for elevated privileges
3. **Break Glass Procedures**: Maintain emergency access procedures with audit requirements
4. **Principle of Least Privilege**: Grant minimum necessary permissions
5. **Separation of Duties**: Require multiple approvers for critical operations

### Implementation Checklist

```markdown
## RBAC Implementation Checklist

### Initial Setup
- [ ] Define organizational roles and responsibilities
- [ ] Map business functions to technical permissions
- [ ] Create role hierarchy and inheritance model
- [ ] Implement permission matrix
- [ ] Configure authentication and MFA requirements

### Technical Implementation
- [ ] Deploy Kubernetes RBAC configurations
- [ ] Implement application-level access controls
- [ ] Configure Vault policies and approvals
- [ ] Set up audit logging and monitoring
- [ ] Create approval workflow automation

### Operational Procedures
- [ ] Document role assignment procedures
- [ ] Create access request workflows
- [ ] Implement regular access reviews
- [ ] Establish incident response procedures
- [ ] Create compliance reporting automation

### Monitoring and Maintenance
- [ ] Set up access monitoring alerts
- [ ] Implement permission usage analytics
- [ ] Create automated compliance checks
- [ ] Schedule regular security assessments
- [ ] Maintain documentation and training
```

**Verification**: RBAC is properly implemented when users can only access resources appropriate for their role, all access is logged, and compliance requirements are met.

---

**Common Errors**: See [FAQ](../../user/faq.md) for RBAC troubleshooting.

**References**:
- [Secrets Policy](secrets-policy.md) for secret management integration
- [Architecture Guide](../architecture.md) for security architecture
- [Monitoring Guide](../monitoring.md) for access monitoring setup
- [Deployment Guide](../deployment.md) for production RBAC implementation
