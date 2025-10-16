# Secrets Management Policy

**Purpose**: Define policies and procedures for secure management of secrets, API keys, certificates, and sensitive configuration data in SomaBrain environments.

**Audience**: DevOps engineers, security teams, and system administrators responsible for SomaBrain security.

**Prerequisites**: Understanding of [Architecture](../architecture.md) and security principles.

---

## Secrets Management Overview

SomaBrain requires secure handling of multiple types of sensitive information across development, staging, and production environments:

### Types of Secrets

**API Keys**: Authentication keys for SomaBrain API access and external service integration
**Database Credentials**: PostgreSQL and Redis authentication information  
**Encryption Keys**: Keys for at-rest and in-transit data encryption
**Certificates**: TLS/SSL certificates for secure communications
**JWT Secrets**: JSON Web Token signing and verification keys
**Service Tokens**: Integration tokens for monitoring, logging, and external APIs

### Security Requirements

**Encryption at Rest**: All secrets must be encrypted when stored
**Access Control**: Role-based access with principle of least privilege
**Rotation Policy**: Regular secret rotation with automated processes
**Audit Logging**: Complete audit trail of secret access and modifications
**Separation**: Different secrets for different environments (dev/staging/prod)

---

## Secret Classification and Handling

### Classification Levels

```yaml
# Secret classification matrix
classifications:
  CRITICAL:
    description: "Production encryption keys, root credentials"
    retention: "7 years"
    rotation: "90 days"
    access_approval: "CISO + 2 approvers"
    examples:
      - Production database master passwords
      - Encryption master keys
      - Root CA private keys
      
  HIGH:
    description: "Production API keys, service credentials"  
    retention: "3 years"
    rotation: "180 days"
    access_approval: "Security team + manager"
    examples:
      - Production SomaBrain API keys
      - External service API keys
      - JWT signing secrets
      
  MEDIUM:
    description: "Non-production credentials, certificates"
    retention: "1 year" 
    rotation: "365 days"
    access_approval: "Team lead approval"
    examples:
      - Staging environment credentials
      - Development certificates
      - Monitoring service tokens
      
  LOW:
    description: "Development secrets, test data"
    retention: "90 days"
    rotation: "No requirement"
    access_approval: "Self-service with logging"
    examples:
      - Local development API keys
      - Test environment passwords
```

### Handling Procedures

**Storage Requirements**:
- Use dedicated secret management systems (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault)
- Never store secrets in code repositories, configuration files, or documentation
- Encrypt secrets with AES-256 or equivalent encryption standards
- Implement redundancy and backup for secret stores

**Access Controls**:
- Implement role-based access control (RBAC) for all secret operations
- Require multi-factor authentication (MFA) for secret access
- Use service accounts for automated secret retrieval
- Log all secret access events with user attribution

---

## Vault-Based Secret Management

### HashiCorp Vault Configuration

Deploy Vault for centralized secret management:

```yaml
# docker-compose.vault.yml  
version: '3.8'
services:
  vault:
    image: vault:1.15.0
    container_name: somabrain-vault
    environment:
      - VAULT_DEV_ROOT_TOKEN_ID=myroot
      - VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200
      - VAULT_ADDR=http://127.0.0.1:8200
    ports:
      - "8200:8200"
    volumes:
      - vault_data:/vault/data
      - vault_config:/vault/config
    cap_add:
      - IPC_LOCK
    command: ["vault", "server", "-config=/vault/config/vault.hcl"]

  vault-agent:
    image: vault:1.15.0
    container_name: somabrain-vault-agent
    depends_on:
      - vault
    volumes:
      - vault_agent_config:/vault/config
      - somabrain_secrets:/vault/secrets
    command: ["vault", "agent", "-config=/vault/config/agent.hcl"]

volumes:
  vault_data:
  vault_config:  
  vault_agent_config:
  somabrain_secrets:
```

**Vault Configuration**:
```hcl
# vault/config/vault.hcl
storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address = "0.0.0.0:8200"
  tls_disable = false
  tls_cert_file = "/vault/config/vault.crt"
  tls_key_file = "/vault/config/vault.key"
}

api_addr = "https://vault:8200"
cluster_addr = "https://vault:8201"
ui = true

# Enable audit logging
audit {
  file {
    file_path = "/vault/logs/audit.log"
    log_raw = false
    format = "json"
  }
}
```

### Vault Secret Engines

Configure secret engines for different types of secrets:

```bash
# Enable KV secrets engine for static secrets
vault secrets enable -version=2 -path=somabrain kv

# Enable database secrets engine for dynamic credentials  
vault secrets enable database

# Configure PostgreSQL dynamic secrets
vault write database/config/postgres \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}}@postgres:5432/somabrain?sslmode=disable" \
  allowed_roles="somabrain-role" \
  username="vault_admin" \
  password="secure_password"

# Configure database role
vault write database/roles/somabrain-role \
  db_name=postgres \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

# Enable PKI engine for certificate management
vault secrets enable pki
vault secrets tune -max-lease-ttl=87600h pki

# Generate root CA
vault write -field=certificate pki/root/generate/internal \
  common_name="SomaBrain Internal CA" \
  ttl=87600h > /vault/config/ca.pem
```

### Vault Policies

Define access policies for different roles:

```hcl
# vault/policies/somabrain-app.hcl - Application access policy
path "somabrain/data/api-keys/*" {
  capabilities = ["read"]
}

path "somabrain/data/encryption/*" {
  capabilities = ["read"] 
}

path "database/creds/somabrain-role" {
  capabilities = ["read"]
}

path "pki/issue/somabrain-servers" {
  capabilities = ["create", "update"]
}

# vault/policies/somabrain-admin.hcl - Administrator policy  
path "somabrain/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "database/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "pki/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "auth/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# vault/policies/somabrain-readonly.hcl - Read-only policy
path "somabrain/data/*" {
  capabilities = ["read", "list"]
}

path "somabrain/metadata/*" {
  capabilities = ["read", "list"]
}
```

**Apply Policies**:
```bash
# Create policies
vault policy write somabrain-app /vault/policies/somabrain-app.hcl
vault policy write somabrain-admin /vault/policies/somabrain-admin.hcl
vault policy write somabrain-readonly /vault/policies/somabrain-readonly.hcl

# Enable AppRole authentication for applications
vault auth enable approle

# Create AppRole for SomaBrain services
vault write auth/approle/role/somabrain-api \
  token_policies="somabrain-app" \
  token_ttl=1h \
  token_max_ttl=4h \
  bind_secret_id=true

# Get role ID and secret ID
vault read auth/approle/role/somabrain-api/role-id
vault write -f auth/approle/role/somabrain-api/secret-id
```

---

## Secret Storage and Retrieval

### Storing Secrets in Vault

Store different types of secrets securely:

```bash
# Store API keys
vault kv put somabrain/api-keys/production \
  somabrain_master_key="sk_prod_abcd1234567890" \
  external_ai_api_key="ai_key_xyz789" \
  monitoring_token="mon_token_456"

# Store database credentials
vault kv put somabrain/database/production \
  postgres_host="prod-postgres.internal" \
  postgres_username="somabrain_prod" \
  postgres_password="complex_secure_password_123!" \
  redis_host="prod-redis.internal" \
  redis_password="redis_secure_password_456!"

# Store encryption keys
vault kv put somabrain/encryption/production \
  master_key="32_byte_base64_encoded_key_here" \
  jwt_signing_key="jwt_secret_key_for_token_signing" \
  data_encryption_key="aes256_key_for_memory_encryption"

# Store certificates
vault kv put somabrain/certificates/production \
  tls_cert=@/path/to/somabrain-prod.crt \
  tls_key=@/path/to/somabrain-prod.key \
  ca_cert=@/path/to/ca-bundle.crt

# Store external service credentials  
vault kv put somabrain/external/production \
  prometheus_url="https://prometheus.internal" \
  prometheus_token="prom_token_789" \
  grafana_api_key="grafana_key_abc123" \
  slack_webhook="https://hooks.slack.com/services/..."
```

### Application Secret Retrieval

Configure SomaBrain to retrieve secrets from Vault:

```bash
# vault/agent/agent.hcl - Vault Agent configuration
pid_file = "/vault/agent.pid"

vault {
  address = "https://vault:8200"
  ca_cert = "/vault/config/ca.pem"
}

auto_auth {
  method "approle" {
    mount_path = "auth/approle"
    config = {
      role_id_file_path = "/vault/config/role-id"
      secret_id_file_path = "/vault/config/secret-id"  
      remove_secret_id_file_after_reading = false
    }
  }

  sink "file" {
    config = {
      path = "/vault/secrets/token"
    }
  }
}

# Template for SomaBrain configuration
template {
  source = "/vault/templates/somabrain-config.tpl"
  destination = "/vault/secrets/somabrain-config.env"
  perms = 0600
  command = "/bin/sh -c 'docker compose restart somabrain-api'"
}

# Template for database configuration
template {
  source = "/vault/templates/database-config.tpl"  
  destination = "/vault/secrets/database.env"
  perms = 0600
}
```

**Configuration Templates**:
```bash
# vault/templates/somabrain-config.tpl
{{- with secret "somabrain/data/api-keys/production" -}}
SOMABRAIN_API_KEY={{ .Data.data.somabrain_master_key }}
EXTERNAL_AI_API_KEY={{ .Data.data.external_ai_api_key }}
MONITORING_TOKEN={{ .Data.data.monitoring_token }}
{{- end }}

{{- with secret "somabrain/data/encryption/production" -}}
SOMABRAIN_MASTER_KEY={{ .Data.data.master_key }}
JWT_SIGNING_KEY={{ .Data.data.jwt_signing_key }}  
DATA_ENCRYPTION_KEY={{ .Data.data.data_encryption_key }}
{{- end }}

{{- with secret "database/creds/somabrain-role" -}}
DATABASE_URL=postgresql://{{ .Data.username }}:{{ .Data.password }}@postgres:5432/somabrain
{{- end }}
```

---

## Kubernetes Secret Management

### Kubernetes Secrets Integration

For Kubernetes deployments, integrate with external secret management:

```yaml
# External Secrets Operator configuration
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-secret-store
  namespace: somabrain
spec:
  provider:
    vault:
      server: "https://vault.internal:8200"
      path: "somabrain"
      version: "v2"
      auth:
        appRole:
          path: "approle"
          roleId: "vault-role-id"
          secretRef:
            secretId:
              name: "vault-secret-id"
              key: "secret-id"

---
# External Secret for API keys
apiVersion: external-secrets.io/v1beta1  
kind: ExternalSecret
metadata:
  name: somabrain-api-keys
  namespace: somabrain
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-secret-store
    kind: SecretStore
  target:
    name: somabrain-api-keys
    creationPolicy: Owner
  data:
  - secretKey: api-key
    remoteRef:
      key: api-keys/production
      property: somabrain_master_key
  - secretKey: external-ai-key
    remoteRef:
      key: api-keys/production  
      property: external_ai_api_key

---
# External Secret for database credentials
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: somabrain-database
  namespace: somabrain
spec:
  refreshInterval: 30m
  secretStoreRef:
    name: vault-secret-store
    kind: SecretStore
  target:
    name: somabrain-database
    creationPolicy: Owner
  dataFrom:
  - extract:
      key: database/production
```

**Deployment with Secrets**:
```yaml
# k8s/somabrain-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: somabrain-api
  namespace: somabrain
spec:
  template:
    spec:
      containers:
      - name: somabrain-api
        image: somabrain/api:latest
        env:
        - name: SOMABRAIN_API_KEY
          valueFrom:
            secretKeyRef:
              name: somabrain-api-keys
              key: api-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: somabrain-database
              key: postgres_url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: somabrain-database
              key: redis_url
              
        # Mount certificates as files
        volumeMounts:
        - name: tls-certs
          mountPath: /etc/ssl/certs/somabrain
          readOnly: true
          
      volumes:
      - name: tls-certs
        secret:
          secretName: somabrain-tls-certs
          defaultMode: 0400
```

---

## Secret Rotation Procedures

### Automated Secret Rotation

Implement automated rotation for different secret types:

```bash
#!/bin/bash
# scripts/rotate-secrets.sh - Automated secret rotation

set -e

ENVIRONMENT=${1:-production}
VAULT_ADDR=${VAULT_ADDR:-https://vault.internal:8200}

echo "Starting secret rotation for environment: $ENVIRONMENT"

# Rotate API keys (every 90 days)
rotate_api_keys() {
  echo "Rotating API keys..."
  
  # Generate new API key
  NEW_API_KEY=$(openssl rand -hex 32)
  
  # Store new key in Vault
  vault kv put somabrain/api-keys/$ENVIRONMENT \
    somabrain_master_key="sk_${ENVIRONMENT}_${NEW_API_KEY}" \
    rotation_date="$(date -Iseconds)" \
    rotated_by="automated_rotation"
  
  # Update application configuration
  kubectl patch secret somabrain-api-keys \
    --type='json' \
    -p='[{"op": "replace", "path": "/data/api-key", "value":"'$(echo -n "sk_${ENVIRONMENT}_${NEW_API_KEY}" | base64)'"}]'
  
  # Restart services to pick up new key
  kubectl rollout restart deployment/somabrain-api
  
  echo "API key rotation completed"
}

# Rotate encryption keys (every 180 days)
rotate_encryption_keys() {
  echo "Rotating encryption keys..."
  
  # Generate new encryption keys
  NEW_MASTER_KEY=$(openssl rand -base64 32)
  NEW_JWT_KEY=$(openssl rand -base64 64)
  
  # Store new keys in Vault
  vault kv put somabrain/encryption/$ENVIRONMENT \
    master_key="$NEW_MASTER_KEY" \
    jwt_signing_key="$NEW_JWT_KEY" \
    rotation_date="$(date -Iseconds)"
  
  echo "Encryption keys rotation completed"
}

# Rotate database credentials (dynamic - every 24 hours)
rotate_database_credentials() {
  echo "Rotating database credentials..."
  
  # Database credentials are automatically rotated by Vault
  # Force renewal of current lease
  vault write -f database/rotate-role/somabrain-role
  
  echo "Database credential rotation completed"
}

# Rotate certificates (every 30 days)
rotate_certificates() {
  echo "Rotating TLS certificates..."
  
  # Generate new certificate from internal CA
  vault write -format=json pki/issue/somabrain-servers \
    common_name="somabrain-api.$ENVIRONMENT.internal" \
    alt_names="somabrain-api,localhost" \
    ttl="720h" > /tmp/cert_response.json
  
  # Extract certificate and key
  jq -r '.data.certificate' /tmp/cert_response.json > /tmp/somabrain.crt
  jq -r '.data.private_key' /tmp/cert_response.json > /tmp/somabrain.key
  jq -r '.data.issuing_ca' /tmp/cert_response.json > /tmp/ca.crt
  
  # Update Kubernetes secret
  kubectl delete secret somabrain-tls-certs --ignore-not-found
  kubectl create secret tls somabrain-tls-certs \
    --cert=/tmp/somabrain.crt \
    --key=/tmp/somabrain.key
  
  # Clean up temporary files
  rm -f /tmp/cert_response.json /tmp/somabrain.crt /tmp/somabrain.key /tmp/ca.crt
  
  echo "Certificate rotation completed"
}

# Main rotation logic
case "$2" in
  "api-keys")
    rotate_api_keys
    ;;
  "encryption")
    rotate_encryption_keys
    ;;
  "database")
    rotate_database_credentials
    ;;
  "certificates")
    rotate_certificates
    ;;
  "all")
    rotate_api_keys
    rotate_encryption_keys
    rotate_database_credentials
    rotate_certificates
    ;;
  *)
    echo "Usage: $0 <environment> [api-keys|encryption|database|certificates|all]"
    exit 1
    ;;
esac

echo "Secret rotation completed successfully for $ENVIRONMENT"
```

### Rotation Scheduling

Schedule automatic rotation with cron or Kubernetes CronJob:

```yaml
# k8s/secret-rotation-cronjob.yml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: secret-rotation
  namespace: somabrain
spec:
  schedule: "0 2 * * 0"  # Weekly on Sunday at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: rotate-secrets
            image: somabrain/secret-rotator:latest
            env:
            - name: VAULT_ADDR
              value: "https://vault.internal:8200"
            - name: ENVIRONMENT
              value: "production"
            command:
            - /scripts/rotate-secrets.sh
            - production
            - all
            
          restartPolicy: OnFailure
          serviceAccountName: secret-rotator
          
---
# Service account for secret rotation
apiVersion: v1
kind: ServiceAccount
metadata:
  name: secret-rotator
  namespace: somabrain

---
# RBAC for secret rotation
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: secret-rotator
  namespace: somabrain
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "patch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: secret-rotator
  namespace: somabrain
subjects:
- kind: ServiceAccount
  name: secret-rotator
  namespace: somabrain
roleRef:
  kind: Role
  name: secret-rotator
  apiGroup: rbac.authorization.k8s.io
```

---

## Emergency Procedures

### Emergency Secret Revocation

Procedures for immediate secret revocation in security incidents:

```bash
#!/bin/bash  
# scripts/emergency-revoke.sh - Emergency secret revocation

INCIDENT_ID=${1:-"INCIDENT_$(date +%s)"}
ENVIRONMENT=${2:-production}

echo "EMERGENCY: Revoking all secrets for incident $INCIDENT_ID"

# 1. Revoke all API keys immediately
vault kv patch somabrain/api-keys/$ENVIRONMENT \
  status="REVOKED" \
  revocation_reason="Security incident $INCIDENT_ID" \
  revoked_at="$(date -Iseconds)"

# 2. Rotate database credentials immediately  
vault write -f database/rotate-role/somabrain-role

# 3. Revoke all active tokens
vault token revoke -prefix somabrain/

# 4. Generate new emergency access credentials
EMERGENCY_KEY=$(openssl rand -hex 32)
vault kv put somabrain/emergency/$ENVIRONMENT \
  emergency_key="sk_emergency_${EMERGENCY_KEY}" \
  created_for_incident="$INCIDENT_ID" \
  expires_at="$(date -d '+24 hours' -Iseconds)"

# 5. Notify incident response team
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "🚨 SECURITY INCIDENT: All SomaBrain secrets revoked for incident '$INCIDENT_ID'",
    "channel": "#security-incidents",
    "username": "SomaBrain Security Bot"
  }'

echo "Emergency revocation completed. New emergency key: sk_emergency_${EMERGENCY_KEY}"
echo "Emergency key expires in 24 hours."
```

### Incident Response Checklist

```markdown
## Security Incident Response - Secrets Compromise

### Immediate Actions (0-30 minutes)
- [ ] Execute emergency secret revocation script
- [ ] Notify security team and incident commander  
- [ ] Isolate affected systems from network
- [ ] Preserve logs and forensic evidence
- [ ] Document timeline and initial findings

### Short-term Actions (30 minutes - 4 hours)  
- [ ] Generate new secrets for critical operations
- [ ] Update applications with emergency credentials
- [ ] Review audit logs for unauthorized access
- [ ] Identify scope of potential data exposure
- [ ] Communicate status to stakeholders

### Recovery Actions (4-24 hours)
- [ ] Complete secret rotation for all systems
- [ ] Implement additional security controls
- [ ] Conduct security assessment of affected systems
- [ ] Update incident response procedures
- [ ] Prepare incident report

### Follow-up Actions (1-7 days)
- [ ] Complete post-incident review
- [ ] Implement preventive measures
- [ ] Update security policies and procedures
- [ ] Conduct security training if needed
- [ ] Monitor for indicators of compromise
```

---

## Compliance and Auditing

### Audit Requirements

Maintain comprehensive audit trails for secret management:

```bash
# Enable Vault audit logging
vault audit enable file file_path=/vault/logs/audit.log log_raw=false

# Query audit logs for secret access
jq '.request.path | select(contains("somabrain"))' /vault/logs/audit.log | head -20

# Generate compliance reports
vault audit list -detailed
vault policy list
vault auth list -detailed
```

### Compliance Frameworks

Ensure secret management meets compliance requirements:

**SOC 2 Type II**:
- Access controls and authentication (CC6.1)
- Logical and physical access controls (CC6.2)  
- Network security (CC6.3)
- Data protection (CC6.7)

**ISO 27001**:
- Access control policy (A.9)
- Cryptography (A.10)
- Operations security (A.12)
- Information security incident management (A.16)

**PCI DSS** (if handling payment data):
- Requirement 3: Protect stored cardholder data
- Requirement 4: Encrypt transmission of cardholder data
- Requirement 7: Restrict access by business need-to-know
- Requirement 8: Identify and authenticate access to system components

---

## Common Errors and Troubleshooting

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Vault connection failed | Applications cannot retrieve secrets | Check Vault connectivity, certificates, and authentication |
| Secret not found | Key/value not available | Verify secret path and access permissions |
| Token expired | Authentication failures | Renew or rotate authentication tokens |
| Permission denied | Access denied to secret paths | Review and update Vault policies |
| Certificate validation failed | TLS connection errors | Update certificates and certificate bundles |

**Verification**: Secret management is working correctly when applications can retrieve secrets, audit logs capture all access, and rotation procedures execute successfully.

---

**Common Errors**: See [FAQ](../../user-manual/faq.md) for secret management troubleshooting.

**References**:
- [RBAC Matrix](rbac-matrix.md) for role-based access control
- [Architecture Guide](../architecture.md) for security architecture
- [Deployment Guide](../deployment.md) for production security setup
- [Monitoring Guide](../monitoring.md) for security metrics and alerting