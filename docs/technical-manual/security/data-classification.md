# Data Classification and Handling Policy

**Purpose**: Define data classification levels, handling requirements, and protection measures for SomaBrain systems and information assets.

**Scope**: All SomaBrain data, including user data, system data, business information, and operational metrics.

**Audience**: All employees, contractors, and third-party vendors with access to SomaBrain data.

**Owner**: Security Team
**Reviewed**: Quarterly
**Last Updated**: 2024-10-16

---

## Quick Navigation

- [Classification Levels](#classification-levels)
- [Data Types and Classifications](#data-types-and-classifications)
- [Handling Requirements](#handling-requirements)
- [Technical Controls](#technical-controls)
- [Access Management](#access-management)
- [Data Lifecycle](#data-lifecycle)
- [Compliance Requirements](#compliance-requirements)

---

## Classification Levels

### Level 1: Public
**Definition**: Information that can be shared publicly without harm to SomaBrain.

**Examples**:
- Marketing materials
- Public API documentation
- Press releases
- Open source code components
- Public blog posts

**Protection Requirements**:
- No encryption required for transmission
- Standard backup procedures
- No access restrictions
- Can be stored on public repositories

### Level 2: Internal
**Definition**: Information intended for use within SomaBrain organization.

**Examples**:
- Internal documentation
- Employee directories
- Project timelines
- Non-sensitive operational metrics
- Training materials

**Protection Requirements**:
- TLS encryption in transit
- Standard access controls (authentication required)
- Regular backup and retention policies
- Authorized personnel only

### Level 3: Confidential
**Definition**: Sensitive information that could harm SomaBrain if disclosed.

**Examples**:
- Customer data and usage patterns
- Business strategies and plans
- Financial information
- Internal security policies
- System architecture details
- Vendor contracts

**Protection Requirements**:
- Encryption at rest and in transit
- Role-based access controls
- Audit logging for access
- Secure backup with encryption
- Need-to-know access
- Data loss prevention (DLP) monitoring

### Level 4: Highly Confidential
**Definition**: Critical information requiring maximum protection.

**Examples**:
- Authentication credentials and API keys
- Customer personally identifiable information (PII)
- Payment information
- Security incident details
- Source code for proprietary algorithms
- Customer conversation transcripts
- Medical or health-related data

**Protection Requirements**:
- Strong encryption (AES-256) at rest and in transit
- Multi-factor authentication for access
- Principle of least privilege
- Comprehensive audit logging
- Encrypted backups with separate key management
- Regular access reviews
- Zero-trust network architecture
- Data masking in non-production environments

---

## Data Types and Classifications

### User and Customer Data

#### Personal Information (Highly Confidential)
```yaml
Data Elements:
  - User names and contact information
  - IP addresses and device identifiers
  - Conversation transcripts
  - Usage patterns and behavior analytics
  - Account credentials and tokens

Protection Measures:
  - Encryption: AES-256-GCM at rest, TLS 1.3 in transit
  - Access: Role-based, need-to-know basis
  - Logging: All access logged and monitored
  - Retention: Per privacy policy and regulatory requirements
  - Anonymization: Required for analytics in non-production
```

#### Conversation Data (Highly Confidential)
```yaml
Data Elements:
  - Chat messages and responses
  - Memory content and associations
  - Cognitive process logs
  - User preferences and settings
  - Interaction metadata

Protection Measures:
  - End-to-end encryption where possible
  - Tokenization for referential data
  - Secure multi-tenant isolation
  - Regular security assessments
  - Incident response procedures
```

### System and Operational Data

#### Security Data (Highly Confidential)
```yaml
Data Elements:
  - API keys and service tokens
  - TLS certificates and private keys
  - Database credentials
  - Audit logs and security events
  - Vulnerability assessment results

Protection Measures:
  - Hardware Security Module (HSM) or Key Management Service
  - Separate encryption keys for different data types
  - Automated key rotation
  - Privileged access management
  - Security Information and Event Management (SIEM)
```

#### Business Intelligence (Confidential)
```yaml
Data Elements:
  - Aggregated usage metrics
  - Performance benchmarks
  - Financial reports
  - Customer analytics (anonymized)
  - Operational dashboards

Protection Measures:
  - Database-level encryption
  - Query auditing and monitoring
  - Role-based dashboard access
  - Data export controls
  - Regular access reviews
```

#### System Logs (Internal)
```yaml
Data Elements:
  - Application logs (non-sensitive)
  - System performance metrics
  - Error logs and stack traces
  - Deployment and configuration changes
  - Health check results

Protection Measures:
  - Log aggregation with access controls
  - Retention policies (typically 90 days)
  - Automated log analysis for security events
  - PII scrubbing in log processing
  - Secure log storage and transmission
```

---

## Handling Requirements

### Data Handling by Classification

| Requirement | Public | Internal | Confidential | Highly Confidential |
|-------------|--------|----------|--------------|-------------------|
| **Encryption at Rest** | Optional | Optional | Required (AES-256) | Required (AES-256) |
| **Encryption in Transit** | Optional | TLS 1.2+ | TLS 1.2+ | TLS 1.3 |
| **Access Control** | None | Authentication | RBAC + Approval | RBAC + MFA + Approval |
| **Audit Logging** | Optional | Basic | Detailed | Comprehensive |
| **Backup Encryption** | No | Optional | Required | Required + Separate Keys |
| **Data Residency** | Global | No Restriction | Region-specific | Country-specific |
| **Retention Period** | Indefinite | 7 years | Per policy | Minimal required |
| **Disposal Method** | Standard | Secure delete | Cryptographic erasure | Cryptographic erasure |

### Specific Handling Procedures

#### Creating and Storing Data
```bash
# For Highly Confidential data creation
# 1. Use appropriate encryption
openssl enc -aes-256-gcm -salt -in sensitive_data.txt -out sensitive_data.enc

# 2. Store encryption keys separately
aws kms encrypt --key-id alias/somabrain-data --plaintext "encryption-key" \
  --output text --query CiphertextBlob | base64 -d > encrypted_key.bin

# 3. Apply proper file permissions
chmod 600 sensitive_data.enc
chown root:somabrain-secure sensitive_data.enc

# 4. Log the data creation event
logger -p auth.info "Highly confidential data created: $(basename $PWD)/sensitive_data.enc"
```

#### Data Access Procedures
```bash
# Access request validation
echo "Access Request Checklist:"
echo "[ ] Business justification documented"
echo "[ ] Manager approval obtained"
echo "[ ] Minimum access period specified"
echo "[ ] Data classification confirmed"
echo "[ ] Security training completed"
echo "[ ] Access review scheduled"

# Implement time-limited access
# Add user to group with automatic expiration
usermod -G confidential-data-access user123
at now + 30 days <<< "usermod -G user123 user123"  # Remove after 30 days
```

#### Data Transmission
```bash
# For Confidential/Highly Confidential data
# 1. Use secure channels only
curl -X POST https://api.somabrain.com/secure-endpoint \
  --cert client.crt --key client.key \
  --cacert ca.crt \
  -H "Content-Type: application/json" \
  -d @encrypted_payload.json

# 2. Verify certificate and connection
openssl s_client -connect api.somabrain.com:443 -verify_return_error

# 3. Log transmission events
logger -p local0.info "Confidential data transmitted to: api.somabrain.com"
```

---

## Technical Controls

### Encryption Standards

#### Data at Rest
```yaml
Highly Confidential:
  Algorithm: AES-256-GCM
  Key Management: AWS KMS / Azure Key Vault / HashiCorp Vault
  Key Rotation: Automatic, every 90 days
  Implementation: Application-level + Database-level

Confidential:
  Algorithm: AES-256-CBC minimum
  Key Management: Centralized key management service
  Key Rotation: Every 1 year
  Implementation: Database-level encryption

Database Configuration:
  PostgreSQL:
    - Enable transparent data encryption (TDE)
    - Set ssl = on in postgresql.conf
    - Use encrypted tablespaces for sensitive tables

  Redis:
    - Enable TLS for client connections
    - Use Redis AUTH with strong passwords
    - Encrypt RDB/AOF files at filesystem level
```

#### Data in Transit
```yaml
All Classifications:
  Minimum: TLS 1.2
  Preferred: TLS 1.3
  Cipher Suites: ECDHE-RSA-AES256-GCM-SHA384, ECDHE-RSA-CHACHA20-POLY1305

HTTPS Configuration:
  HSTS: max-age=31536000; includeSubDomains; preload
  Certificate: RSA 2048-bit minimum, ECC P-256 preferred
  Certificate Authority: Let's Encrypt or internal CA

API Security:
  Authentication: JWT with RS256 signing
  Rate Limiting: Per endpoint and per user
  Request Validation: Schema validation and sanitization
```

### Access Control Implementation

#### Role-Based Access Control (RBAC)
```yaml
# Example RBAC configuration
Roles:
  customer_service:
    permissions:
      - read:user_profile
      - read:conversation_history
      - update:user_preferences
    data_access:
      - confidential: limited
      - highly_confidential: none

  data_scientist:
    permissions:
      - read:analytics_data
      - read:aggregated_metrics
    data_access:
      - confidential: anonymized_only
      - highly_confidential: none

  security_admin:
    permissions:
      - read:audit_logs
      - read:security_events
      - update:security_policies
    data_access:
      - confidential: full
      - highly_confidential: full

  system_admin:
    permissions:
      - read:system_logs
      - update:system_config
      - restart:services
    data_access:
      - confidential: operational_only
      - highly_confidential: encrypted_only
```

#### Database Access Controls
```sql
-- Create roles for different data access levels
CREATE ROLE somabrain_readonly;
CREATE ROLE somabrain_confidential_read;
CREATE ROLE somabrain_highly_confidential_read;

-- Grant appropriate permissions
GRANT SELECT ON public_data.* TO somabrain_readonly;
GRANT SELECT ON confidential_data.* TO somabrain_confidential_read;
GRANT SELECT ON highly_confidential_data.* TO somabrain_highly_confidential_read;

-- Create users with specific roles
CREATE USER analyst_user WITH PASSWORD 'strong_password';
GRANT somabrain_readonly TO analyst_user;

-- Enable row-level security for multi-tenant data
ALTER TABLE user_conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_data_isolation ON user_conversations
  FOR ALL TO application_role
  USING (tenant_id = current_setting('app.tenant_id'));
```

---

## Access Management

### Access Request Process

#### Standard Access Request
```markdown
# Access Request Template

**Requestor Information:**
- Name: [Full Name]
- Role: [Job Title/Department]
- Manager: [Manager Name]
- Employee ID: [ID Number]

**Access Details:**
- Data Classification: [Public/Internal/Confidential/Highly Confidential]
- Specific Data/Systems: [Detailed description]
- Business Justification: [Why access is needed]
- Access Duration: [Start date - End date]
- Access Level: [Read-only/Read-write/Admin]

**Approvals Required:**
- [ ] Direct Manager Approval
- [ ] Data Owner Approval (for Confidential+)
- [ ] Security Team Approval (for Highly Confidential)
- [ ] Privacy Team Approval (for PII access)

**Security Requirements:**
- [ ] Security training completed
- [ ] MFA enabled on account
- [ ] VPN access configured (if remote)
- [ ] Device compliance verified
```

#### Emergency Access Procedures
```bash
# Emergency access (Highly Confidential data)
# Requires approval from two executives + security team

# 1. Document emergency justification
cat > emergency_access_request.txt << EOF
Emergency Access Request: $(date)
Incident ID: INC-$(date +%Y%m%d)-001
Requestor: $USER
Justification: Critical production issue affecting customer data
Business Impact: Service unavailable, data integrity at risk
Duration Requested: 4 hours maximum
Emergency Contacts Notified: CTO, CISO, VP Engineering
EOF

# 2. Implement temporary access with monitoring
sudo usermod -G emergency_access $USER
logger -p auth.warning "Emergency access granted to $USER: $(cat emergency_access_request.txt)"

# 3. Schedule automatic revocation
at now + 4 hours <<< "sudo usermod -G $USER $USER && logger 'Emergency access revoked for $USER'"
```

### Access Review Process

#### Quarterly Access Reviews
```bash
# Generate access review reports
cat > access_review_script.sh << 'EOF'
#!/bin/bash

# Generate user access report
echo "=== SomaBrain Access Review - $(date) ==="
echo

echo "Users with Confidential Data Access:"
getent group confidential-data-access | cut -d: -f4 | tr ',' '\n' | while read user; do
  echo "  $user - Last login: $(last -1 $user | head -1 | awk '{print $4, $5, $6, $7}')"
done

echo
echo "Users with Highly Confidential Data Access:"
getent group highly-confidential-access | cut -d: -f4 | tr ',' '\n' | while read user; do
  echo "  $user - Last login: $(last -1 $user | head -1 | awk '{print $4, $5, $6, $7}')"
done

echo
echo "Database Access Summary:"
psql -h postgres-host -U admin -d somabrain -c "
SELECT
  usename as username,
  string_agg(rolname, ', ') as roles,
  valuntil as password_expiry
FROM pg_user u
JOIN pg_auth_members m ON u.usesysid = m.member
JOIN pg_roles r ON m.roleid = r.oid
WHERE u.usename NOT LIKE 'postgres%'
GROUP BY usename, valuntil;"

EOF

chmod +x access_review_script.sh
./access_review_script.sh > quarterly_access_review_$(date +%Y_Q%q).txt
```

---

## Data Lifecycle

### Data Creation and Collection

#### Data Minimization Principles
```yaml
Collection Guidelines:
  - Collect only data necessary for legitimate business purposes
  - Implement "privacy by design" in all systems
  - Document data collection purpose and legal basis
  - Provide clear privacy notices to users
  - Obtain explicit consent where required

Technical Implementation:
  - Schema validation to prevent over-collection
  - Automated data discovery and classification
  - Privacy impact assessments for new features
  - Regular data mapping exercises
```

#### Data Classification Assignment
```python
# Automated data classification example
def classify_data(data_field, content):
    """Automatically classify data based on content analysis"""

    classification_rules = {
        'email_patterns': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'phone_patterns': r'\b\d{3}-\d{3}-\d{4}\b|\b\(\d{3}\)\s?\d{3}-\d{4}\b',
        'ssn_patterns': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card_patterns': r'\b4[0-9]{12}(?:[0-9]{3})?\b|\b5[1-5][0-9]{14}\b'
    }

    # Check for PII patterns
    for pattern_name, pattern in classification_rules.items():
        if re.search(pattern, content):
            return 'HIGHLY_CONFIDENTIAL'

    # Check field names for sensitive indicators
    sensitive_fields = ['password', 'token', 'key', 'secret', 'credential']
    if any(field in data_field.lower() for field in sensitive_fields):
        return 'HIGHLY_CONFIDENTIAL'

    # Default classification based on data context
    if 'user_' in data_field or 'customer_' in data_field:
        return 'CONFIDENTIAL'
    elif 'internal_' in data_field:
        return 'INTERNAL'
    else:
        return 'PUBLIC'

# Usage in data ingestion pipeline
classification = classify_data('user_email', user_input)
apply_protection_controls(data, classification)
```

### Data Storage and Processing

#### Storage Security Requirements
```yaml
Highly Confidential Storage:
  Location:
    - Primary: Encrypted database with TDE
    - Backup: Separate encrypted storage with different keys
    - Geographic: Same country/region as data subject

  Access Controls:
    - Database: Row-level security, column encryption
    - File System: Access Control Lists (ACLs)
    - Application: Attribute-based access control

  Monitoring:
    - All access logged with user ID and timestamp
    - Automated anomaly detection
    - Real-time alerting for suspicious access patterns

  Performance:
    - Encrypted indexes where supported
    - Query optimization for encrypted columns
    - Caching strategies that maintain security
```

#### Processing Controls
```bash
# Data processing environment setup
# 1. Secure processing environment
export SECURE_PROCESSING_ENV=1
export DATA_CLASSIFICATION=HIGHLY_CONFIDENTIAL
export AUDIT_LOG_LEVEL=FULL

# 2. Input validation and sanitization
validate_input() {
  local input="$1"

  # Check for SQL injection patterns
  if echo "$input" | grep -qE "(SELECT|INSERT|UPDATE|DELETE|DROP|UNION)" ; then
    logger -p security.error "Potential SQL injection detected in input"
    return 1
  fi

  # Check for XSS patterns
  if echo "$input" | grep -qE "(<script|javascript:|vbscript:)" ; then
    logger -p security.error "Potential XSS detected in input"
    return 1
  fi

  return 0
}

# 3. Process with appropriate controls
process_confidential_data() {
  local data_file="$1"

  # Verify data classification
  if [[ ! -f "${data_file}.classification" ]]; then
    echo "ERROR: Missing data classification file"
    return 1
  fi

  classification=$(cat "${data_file}.classification")

  # Apply appropriate processing controls
  case "$classification" in
    "HIGHLY_CONFIDENTIAL")
      process_with_full_encryption "$data_file"
      ;;
    "CONFIDENTIAL")
      process_with_standard_encryption "$data_file"
      ;;
    *)
      process_standard "$data_file"
      ;;
  esac

  # Log processing activity
  logger -p local0.info "Data processed: file=$data_file, classification=$classification, user=$USER"
}
```

### Data Retention and Disposal

#### Retention Policies
```yaml
Retention Schedule:
  User Account Data:
    - Active accounts: Indefinite (while account active)
    - Closed accounts: 30 days after closure
    - Legal hold: Extended as required

  Conversation Data:
    - User conversations: Per user preference (default 1 year)
    - System logs: 90 days
    - Security logs: 7 years
    - Audit trails: 7 years

  Business Data:
    - Financial records: 7 years
    - Employee records: 7 years after termination
    - Contracts: 7 years after expiration
    - Marketing data: 3 years unless consent withdrawn

  Technical Data:
    - Application logs: 90 days
    - Performance metrics: 2 years
    - Security events: 7 years
    - Backup data: Same as source data retention
```

#### Secure Disposal Procedures
```bash
# Secure data disposal script
secure_disposal() {
  local data_path="$1"
  local classification="$2"

  case "$classification" in
    "HIGHLY_CONFIDENTIAL"|"CONFIDENTIAL")
      # Cryptographic erasure - delete encryption keys
      echo "Performing cryptographic erasure for $data_path"

      # 1. Identify encryption keys used
      key_id=$(get_encryption_key_id "$data_path")

      # 2. Securely delete keys
      aws kms schedule-key-deletion --key-id "$key_id" --pending-window-in-days 7

      # 3. Overwrite data multiple times
      shred -vfz -n 3 "$data_path"

      # 4. Verify deletion
      if [[ -f "$data_path" ]]; then
        echo "ERROR: File still exists after deletion"
        return 1
      fi

      # 5. Log disposal
      logger -p auth.info "Secure disposal completed: $data_path (classification: $classification)"
      ;;

    "INTERNAL"|"PUBLIC")
      # Standard deletion
      rm -f "$data_path"
      logger -p local0.info "Standard deletion completed: $data_path"
      ;;
  esac
}

# Database record disposal
dispose_database_records() {
  local table_name="$1"
  local where_clause="$2"
  local classification="$3"

  if [[ "$classification" == "HIGHLY_CONFIDENTIAL" ]]; then
    # For highly confidential data, overwrite before delete
    psql -h postgres-host -U admin -d somabrain -c "
    UPDATE $table_name
    SET
      data_column = '🗑️DISPOSED🗑️',
      created_at = NOW(),
      updated_at = NOW()
    WHERE $where_clause;

    -- Then delete the records
    DELETE FROM $table_name WHERE $where_clause;

    -- Vacuum to reclaim space
    VACUUM FULL $table_name;
    "
  else
    # Standard deletion
    psql -h postgres-host -U admin -d somabrain -c "DELETE FROM $table_name WHERE $where_clause;"
  fi

  logger -p auth.info "Database disposal completed: $table_name WHERE $where_clause"
}
```

---

## Compliance Requirements

### Regulatory Frameworks

#### GDPR Compliance (EU)
```yaml
Legal Basis for Processing:
  - Consent: Explicit, informed, revocable
  - Contract: Necessary for service provision
  - Legal Obligation: Compliance with law
  - Vital Interests: Protection of life
  - Public Task: Public interest or official authority
  - Legitimate Interest: Balanced against individual rights

Data Subject Rights:
  - Right to Information: Privacy notices and transparency
  - Right of Access: Data subject access requests (SAR)
  - Right to Rectification: Correct inaccurate data
  - Right to Erasure: "Right to be forgotten"
  - Right to Restrict Processing: Limit processing activities
  - Right to Data Portability: Export data in machine-readable format
  - Right to Object: Opt-out of certain processing
  - Rights related to Automated Decision Making: Human review of automated decisions

Technical Implementation:
  - Data Protection by Design and by Default
  - Data Protection Impact Assessments (DPIA)
  - Privacy-preserving technologies
  - Regular compliance audits
  - Breach notification procedures (72 hours)
```

#### CCPA Compliance (California)
```yaml
Consumer Rights:
  - Right to Know: What personal information is collected
  - Right to Delete: Request deletion of personal information
  - Right to Opt-Out: Opt-out of sale of personal information
  - Right to Non-Discrimination: Equal service regardless of privacy choices

Technical Requirements:
  - Privacy Policy Updates: Annual updates minimum
  - Consumer Request Processing: Verify identity, respond within 45 days
  - Do Not Sell My Personal Information: Global privacy control support
  - Sensitive Personal Information: Enhanced protections
```

#### SOC 2 Type II Controls
```yaml
Security Principle:
  - Access Controls: RBAC, MFA, regular reviews
  - Authorization: Principle of least privilege
  - Vulnerability Management: Regular scanning and patching
  - Network Security: Firewalls, intrusion detection
  - Data Encryption: At rest and in transit

Availability Principle:
  - Capacity Management: Resource monitoring and scaling
  - Backup and Recovery: Regular backups, tested recovery procedures
  - Incident Response: Documented procedures and regular testing
  - Monitoring: 24/7 system monitoring and alerting

Confidentiality Principle:
  - Data Classification: Formal classification system
  - Encryption: Strong encryption for confidential data
  - Secure Disposal: Secure data destruction procedures
  - Employee Training: Regular security awareness training
```

### Compliance Monitoring

#### Automated Compliance Checks
```bash
#!/bin/bash
# compliance_check.sh - Automated compliance verification

echo "=== SomaBrain Compliance Check - $(date) ==="

# Check encryption compliance
echo "1. Checking encryption compliance..."
check_encryption_compliance() {
  # Verify database encryption
  psql -h postgres-host -U admin -d somabrain -c "
  SELECT name, setting
  FROM pg_settings
  WHERE name IN ('ssl', 'ssl_cert_file', 'ssl_key_file');" | grep -q "on"

  if [[ $? -eq 0 ]]; then
    echo "✅ Database encryption: COMPLIANT"
  else
    echo "❌ Database encryption: NON-COMPLIANT"
  fi

  # Check Redis TLS
  redis-cli --tls --cert redis-client.crt --key redis-client.key ping &>/dev/null
  if [[ $? -eq 0 ]]; then
    echo "✅ Redis TLS: COMPLIANT"
  else
    echo "❌ Redis TLS: NON-COMPLIANT"
  fi
}

# Check access control compliance
echo "2. Checking access controls..."
check_access_controls() {
  # Verify no shared accounts
  shared_accounts=$(awk -F: '$3 >= 1000 && $1 ~ /shared|common|generic/ {print $1}' /etc/passwd | wc -l)
  if [[ $shared_accounts -eq 0 ]]; then
    echo "✅ No shared accounts: COMPLIANT"
  else
    echo "❌ Found $shared_accounts shared accounts: NON-COMPLIANT"
  fi

  # Check password policies
  if grep -q "minlen=12" /etc/security/pwquality.conf; then
    echo "✅ Password complexity: COMPLIANT"
  else
    echo "❌ Password complexity: NON-COMPLIANT"
  fi
}

# Check audit logging
echo "3. Checking audit logging..."
check_audit_logging() {
  # Verify audit service is running
  systemctl is-active auditd &>/dev/null
  if [[ $? -eq 0 ]]; then
    echo "✅ Audit service: COMPLIANT"
  else
    echo "❌ Audit service: NON-COMPLIANT"
  fi

  # Check log retention
  log_retention=$(grep "max_log_file_action" /etc/audit/auditd.conf | awk '{print $3}')
  if [[ "$log_retention" == "rotate" ]]; then
    echo "✅ Log retention: COMPLIANT"
  else
    echo "❌ Log retention: NON-COMPLIANT"
  fi
}

# Run all compliance checks
check_encryption_compliance
check_access_controls
check_audit_logging

echo
echo "=== Compliance Check Complete ==="
echo "Report generated: $(date)"
```

#### Data Subject Request Handling
```python
# data_subject_requests.py - Handle GDPR/CCPA requests

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class DataSubjectRequestHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def handle_access_request(self, user_id: str, email: str) -> Dict:
        """Handle data subject access request (GDPR Article 15)"""
        try:
            # 1. Verify identity
            if not self.verify_user_identity(user_id, email):
                raise ValueError("Identity verification failed")

            # 2. Collect all user data
            user_data = {
                'personal_info': self.get_user_profile(user_id),
                'conversations': self.get_user_conversations(user_id),
                'preferences': self.get_user_preferences(user_id),
                'audit_logs': self.get_user_audit_logs(user_id),
                'processing_activities': self.get_processing_activities(user_id)
            }

            # 3. Generate report
            report = {
                'request_id': f"SAR-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                'user_id': user_id,
                'generated_at': datetime.now().isoformat(),
                'data': user_data,
                'retention_periods': self.get_retention_periods(),
                'legal_basis': self.get_legal_basis_for_processing(user_id)
            }

            # 4. Log the request
            self.logger.info(f"Access request fulfilled for user {user_id}")

            return report

        except Exception as e:
            self.logger.error(f"Error processing access request: {e}")
            raise

    def handle_deletion_request(self, user_id: str, email: str) -> Dict:
        """Handle right to erasure request (GDPR Article 17)"""
        try:
            # 1. Verify identity
            if not self.verify_user_identity(user_id, email):
                raise ValueError("Identity verification failed")

            # 2. Check if deletion is legally permissible
            if not self.can_delete_user_data(user_id):
                return {
                    'status': 'rejected',
                    'reason': 'Legal obligation to retain data',
                    'retention_period': self.get_mandatory_retention_period(user_id)
                }

            # 3. Perform secure deletion
            deletion_log = []

            # Delete user conversations
            deleted_conversations = self.secure_delete_conversations(user_id)
            deletion_log.append(f"Deleted {deleted_conversations} conversations")

            # Delete user profile
            self.secure_delete_user_profile(user_id)
            deletion_log.append("Deleted user profile")

            # Delete preferences and settings
            self.secure_delete_user_preferences(user_id)
            deletion_log.append("Deleted user preferences")

            # Update audit logs (mark as deleted, don't delete)
            self.mark_user_deleted_in_audit_logs(user_id)
            deletion_log.append("Updated audit logs")

            # 4. Generate deletion certificate
            certificate = {
                'request_id': f"DEL-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                'user_id': user_id,
                'deleted_at': datetime.now().isoformat(),
                'deletion_log': deletion_log,
                'status': 'completed'
            }

            self.logger.info(f"Deletion request completed for user {user_id}")

            return certificate

        except Exception as e:
            self.logger.error(f"Error processing deletion request: {e}")
            raise

    def secure_delete_conversations(self, user_id: str) -> int:
        """Securely delete user conversations with cryptographic erasure"""
        # Implementation would include:
        # 1. Identify all conversation records
        # 2. Delete encryption keys for those records
        # 3. Overwrite data with random values
        # 4. Delete the records
        # 5. Return count of deleted conversations
        pass

    def get_legal_basis_for_processing(self, user_id: str) -> Dict:
        """Get legal basis for each type of data processing"""
        return {
            'service_provision': 'Contract (Article 6(1)(b))',
            'system_improvement': 'Legitimate Interest (Article 6(1)(f))',
            'security_monitoring': 'Legitimate Interest (Article 6(1)(f))',
            'legal_compliance': 'Legal Obligation (Article 6(1)(c))'
        }
```

---

## Verification and Monitoring

### Daily Security Checks
```bash
# daily_security_check.sh
#!/bin/bash

echo "=== Daily Security Check - $(date) ==="

# 1. Check for unauthorized access attempts
echo "Checking unauthorized access attempts..."
failed_logins=$(grep "Failed password" /var/log/auth.log | grep "$(date +%b\ %d)" | wc -l)
if [[ $failed_logins -gt 10 ]]; then
  echo "⚠️  WARNING: $failed_logins failed login attempts today"
else
  echo "✅ Failed logins within normal range: $failed_logins"
fi

# 2. Verify encryption status
echo "Verifying encryption status..."
if systemctl is-active --quiet postgresql && \
   psql -h localhost -U postgres -c "SHOW ssl;" | grep -q "on"; then
  echo "✅ Database encryption active"
else
  echo "❌ Database encryption issue detected"
fi

# 3. Check data classification compliance
echo "Checking data classification..."
unclassified_files=$(find /data -type f ! -name "*.classification" | wc -l)
if [[ $unclassified_files -eq 0 ]]; then
  echo "✅ All data files properly classified"
else
  echo "⚠️  WARNING: $unclassified_files unclassified files found"
fi

# 4. Verify backup encryption
echo "Checking backup encryption..."
latest_backup=$(ls -t /backups/*.enc 2>/dev/null | head -1)
if [[ -n "$latest_backup" ]] && [[ $(stat -c %Y "$latest_backup") -gt $(date -d "yesterday" +%s) ]]; then
  echo "✅ Recent encrypted backup found: $(basename $latest_backup)"
else
  echo "❌ No recent encrypted backup found"
fi

echo "=== Daily Security Check Complete ==="
```

### Compliance Reporting
```bash
# Generate monthly compliance report
generate_compliance_report() {
  local month=$(date +%Y-%m)
  local report_file="compliance_report_$month.json"

  cat > "$report_file" << EOF
{
  "report_period": "$month",
  "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "compliance_framework": ["GDPR", "CCPA", "SOC2"],
  "data_classification": {
    "total_data_objects": $(find /data -type f | wc -l),
    "classified_objects": $(find /data -name "*.classification" | wc -l),
    "classification_coverage": "$(echo "scale=2; $(find /data -name "*.classification" | wc -l) * 100 / $(find /data -type f | wc -l)" | bc)%"
  },
  "encryption_status": {
    "data_at_rest": "$(check_encryption_at_rest)",
    "data_in_transit": "$(check_encryption_in_transit)",
    "key_rotation": "$(check_key_rotation_status)"
  },
  "access_controls": {
    "mfa_enabled_users": "$(get_mfa_enabled_count)",
    "privileged_access_reviews": "$(get_last_access_review_date)",
    "shared_accounts": "$(get_shared_account_count)"
  },
  "data_subject_requests": {
    "access_requests": $(get_dsr_count "access" "$month"),
    "deletion_requests": $(get_dsr_count "deletion" "$month"),
    "average_response_time": "$(get_avg_dsr_response_time "$month")"
  }
}
EOF

  echo "Compliance report generated: $report_file"
}
```

---

## Summary

This data classification and handling policy provides:

✅ **Clear Classification Levels**: Four-tier system from Public to Highly Confidential
✅ **Specific Protection Requirements**: Technical controls for each classification level
✅ **Practical Implementation**: Code examples and operational procedures
✅ **Compliance Framework**: GDPR, CCPA, and SOC 2 alignment
✅ **Automated Monitoring**: Scripts for continuous compliance verification
✅ **Data Lifecycle Management**: Creation through secure disposal procedures

**Next Steps:**
1. Train all personnel on classification procedures
2. Implement automated data discovery and classification
3. Deploy monitoring scripts for continuous compliance
4. Conduct regular access reviews and policy updates
5. Test incident response procedures for data breaches

**Approval Required From:**
- [x] Security Team Lead
- [x] Privacy Officer
- [x] Legal Counsel
- [x] Chief Information Security Officer (CISO)