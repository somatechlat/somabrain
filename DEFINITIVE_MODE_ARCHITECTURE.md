# DEFINITIVE MODE ARCHITECTURE - PRODUCTION-READY CENTRALIZATION

**Status:** 🔴 CRITICAL REFACTORING REQUIRED  
**Branch:** Mode Centralization & Cleanup  
**Goal:** World-class, production-ready configuration architecture

---

## EXECUTIVE SUMMARY

**CURRENT STATE:** Configuration chaos across 3 deployment systems with NO consistency:
- Docker Compose: Uses `SOMABRAIN_MODE=enterprise` + 6 redundant flags
- Helm (Kubernetes): Uses `values-{dev,staging,prod}.yaml` files but NO mode variable
- Code: Has mode system but it's ignored by deployments

**TARGET STATE:** Single unified mode system across ALL deployment methods with strict inheritance.

**IMPACT:** This is architectural debt that MUST be fixed before production.

---

## PART 1: CURRENT DEPLOYMENT ANALYSIS

### 1.1 Docker Compose (Local/Dev)

**File:** `docker-compose.yml` + `.env`

**Current Configuration:**
```bash
SOMABRAIN_MODE=enterprise              # ← Set but not consistently used
SOMABRAIN_FORCE_FULL_STACK=1           # ← Redundant
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1  # ← Redundant
SOMABRAIN_REQUIRE_MEMORY=1             # ← Redundant
SOMABRAIN_PREDICTOR_PROVIDER=mahal
SOMABRAIN_ENABLE_BEST=1                # ← Unclear purpose
```

**Issues:**
- ❌ Mode is set but overridden by explicit flags
- ❌ No dev/staging/prod separation
- ❌ Single .env file for all environments
- ❌ Hardcoded credentials (dev-token-allow, soma_pass)

---

### 1.2 Helm/Kubernetes (Production)

**Files:** 
- `infra/helm/charts/soma-infra/values-{dev,staging,prod}.yaml`
- `infra/helm/charts/soma-apps/values.yaml`

**Current Configuration:**

**Infrastructure (soma-infra):**
```yaml
# values-dev.yaml
localDev: true
auth.enabled: false
opa.enabled: true
redis.enabled: true
kube-prometheus-stack.enabled: false

# values-staging.yaml
auth.replicaCount: 2
kafka.replicaCount: 3
prometheus.retention: 30d

# values-prod.yaml
auth.replicaCount: 3
kafka.replicaCount: 5
kafka.persistence.enabled: true
redis.architecture: replication
prometheus.retention: 60d
```

**Applications (soma-apps):**
```yaml
featureFlags:
  enableCogThreads: true
  learnerEnabled: true

envCommon:
  SOMABRAIN_REDIS_URL: "redis://..."
  SOMABRAIN_KAFKA_URL: "kafka://..."
  # NO SOMABRAIN_MODE VARIABLE!

cog.env:
  ENABLE_COG_THREADS: "1"
  SOMA_HEAT_METHOD: "lanczos"
  SOMABRAIN_SEGMENT_MODE: "leader"
  # 15+ environment variables hardcoded
```

**Issues:**
- ❌ NO `SOMABRAIN_MODE` variable in Helm deployments
- ❌ Environment-specific behavior via separate values files
- ❌ Feature flags scattered in multiple places
- ❌ No inheritance - each env file duplicates config
- ❌ Helm values don't match .env structure

---

### 1.3 Code (Runtime)

**File:** `common/config/settings.py`

**Current Implementation:**
```python
mode: str = Field(default=os.getenv("SOMABRAIN_MODE", "enterprise"))

@property
def mode_normalized(self) -> str:
    # dev/development → dev
    # stage/staging → staging
    # enterprise/main/prod → prod
    
@property
def mode_api_auth_enabled(self) -> bool:
    return self.mode_normalized != "dev"

@property
def mode_require_external_backends(self) -> bool:
    return True  # All modes
```

**Issues:**
- ✅ Good foundation exists
- ❌ Not used by Helm deployments
- ❌ Overridden by explicit flags
- ❌ No validation that mode is respected

---

## PART 2: THE PROBLEM

### 2.1 Three Different Systems

```
Docker Compose          Helm/K8s              Code
     ↓                      ↓                   ↓
SOMABRAIN_MODE      values-{env}.yaml    mode_normalized
     +                     +                   +
6 explicit flags    featureFlags dict    mode properties
     ↓                     ↓                   ↓
  CONFLICT!            CONFLICT!          IGNORED!
```

**Result:** No one knows what's actually controlling behavior.

### 2.2 Configuration Explosion

**Current count:**
- 1 mode variable (ignored)
- 20+ feature flags
- 3 deployment systems
- 7 subsystem modes
- 0 consistency

**What should be:**
- 1 mode variable (enforced)
- 3 deployment profiles
- 1 configuration system
- 100% consistency

---

## PART 3: DEFINITIVE ARCHITECTURE

### 3.1 Single Source of Truth

```
                    SOMABRAIN_DEPLOYMENT_MODE
                    (dev | staging | production)
                              │
                              ├─────────────────────────────────┐
                              │                                 │
                              ▼                                 ▼
                    DEPLOYMENT PROFILE              RUNTIME CONFIGURATION
                    (Infrastructure)                (Application Behavior)
                              │                                 │
                    ┌─────────┴─────────┐            ┌─────────┴─────────┐
                    │                   │            │                   │
                    ▼                   ▼            ▼                   ▼
              Helm Values         Docker Compose   Settings.py      Feature Flags
              (K8s resources)     (.env file)      (Policies)       (Opt-in only)
```

### 3.2 Mode Definitions

**Three deployment modes. Period.**

| Mode | Purpose | Auth | Backends | Persistence | Replicas | Monitoring |
|------|---------|------|----------|-------------|----------|------------|
| **dev** | Local development | Optional | Required | No | 1 | Minimal |
| **staging** | Pre-production testing | Required | Required | Yes | 2-3 | Full |
| **production** | Live system | Required | Required | Yes | 3-5 | Full |

### 3.3 Configuration Inheritance

```yaml
# Base configuration (applies to ALL modes)
base:
  require_external_backends: true
  require_memory: true
  predictor_provider: mahal
  math_binary_mode: pm_one
  
# Mode-specific overrides
dev:
  auth_enabled: false  # Only exception
  log_level: DEBUG
  replicas: 1
  persistence: false
  
staging:
  auth_enabled: true
  log_level: INFO
  replicas: 2
  persistence: true
  
production:
  auth_enabled: true
  log_level: WARNING
  replicas: 3
  persistence: true
  opa_fail_closed: true
```

---

## PART 4: IMPLEMENTATION PLAN

### 4.1 New File Structure

```
config/
├── base.yaml                    # Base configuration (all modes)
├── modes/
│   ├── dev.yaml                 # Development overrides
│   ├── staging.yaml             # Staging overrides
│   └── production.yaml          # Production overrides
├── deployment/
│   ├── docker-compose/
│   │   ├── .env.dev             # Docker dev config
│   │   ├── .env.staging         # Docker staging config
│   │   └── .env.production      # Docker production config
│   └── helm/
│       ├── values-dev.yaml      # Helm dev config
│       ├── values-staging.yaml  # Helm staging config
│       └── values-production.yaml # Helm production config
└── README.md                    # Configuration guide
```

### 4.2 Centralized Mode Config Class

**File:** `somabrain/config/mode.py`

```python
from enum import Enum
from dataclasses import dataclass
from typing import Literal

class DeploymentMode(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass(frozen=True)
class DeploymentProfile:
    """Immutable deployment profile derived from mode."""
    mode: DeploymentMode
    
    # Security
    auth_enabled: bool
    opa_fail_closed: bool
    
    # Infrastructure
    require_external_backends: bool
    require_memory: bool
    
    # Observability
    log_level: str
    metrics_detail: Literal["low", "medium", "high"]
    
    # Deployment
    min_replicas: int
    persistence_enabled: bool

@dataclass
class SubsystemConfig:
    """Configurable subsystem modes with mode-aware defaults."""
    math_binary_mode: Literal["pm_one", "zero_one"] = "pm_one"
    segmentation_algorithm: Literal["leader", "cpd", "hazard"] = "leader"
    heat_diffusion_method: Literal["chebyshev", "lanczos"] = "lanczos"
    predictor_provider: Literal["mahal", "llm"] = "mahal"

@dataclass
class FeatureFlags:
    """Explicit opt-in features (default OFF)."""
    cog_integrator: bool = False
    cog_segmentation: bool = False
    cog_orchestrator: bool = False
    memory_weighting: bool = False
    teach_feedback: bool = False
    tiered_memory: bool = False

class ModeConfig:
    """Central mode configuration with strict validation."""
    
    PROFILES = {
        DeploymentMode.DEV: DeploymentProfile(
            mode=DeploymentMode.DEV,
            auth_enabled=False,
            opa_fail_closed=False,
            require_external_backends=True,
            require_memory=True,
            log_level="DEBUG",
            metrics_detail="high",
            min_replicas=1,
            persistence_enabled=False,
        ),
        DeploymentMode.STAGING: DeploymentProfile(
            mode=DeploymentMode.STAGING,
            auth_enabled=True,
            opa_fail_closed=True,
            require_external_backends=True,
            require_memory=True,
            log_level="INFO",
            metrics_detail="medium",
            min_replicas=2,
            persistence_enabled=True,
        ),
        DeploymentMode.PRODUCTION: DeploymentProfile(
            mode=DeploymentMode.PRODUCTION,
            auth_enabled=True,
            opa_fail_closed=True,
            require_external_backends=True,
            require_memory=True,
            log_level="WARNING",
            metrics_detail="low",
            min_replicas=3,
            persistence_enabled=True,
        ),
    }
    
    def __init__(self, mode: str):
        self.mode = self._parse_mode(mode)
        self.profile = self.PROFILES[self.mode]
        self.subsystems = SubsystemConfig()
        self.features = FeatureFlags()
        self._validate()
    
    def _parse_mode(self, mode: str) -> DeploymentMode:
        """Parse and normalize mode string."""
        m = (mode or "").strip().lower()
        if m in ("dev", "development"):
            return DeploymentMode.DEV
        if m in ("stage", "staging"):
            return DeploymentMode.STAGING
        if m in ("prod", "production", "enterprise", "main"):
            return DeploymentMode.PRODUCTION
        raise ValueError(f"Invalid mode: {mode}")
    
    def _validate(self):
        """Validate configuration consistency."""
        errors = []
        
        # Production must have auth
        if self.mode == DeploymentMode.PRODUCTION:
            if not self.profile.auth_enabled:
                errors.append("CRITICAL: Auth cannot be disabled in production")
        
        # All modes must require backends
        if not self.profile.require_external_backends:
            errors.append("CRITICAL: External backends required in all modes")
        
        if errors:
            raise ValueError(f"Mode validation failed: {errors}")
    
    def to_env_dict(self) -> dict:
        """Export as environment variables."""
        return {
            "SOMABRAIN_DEPLOYMENT_MODE": self.mode.value,
            "SOMABRAIN_AUTH_ENABLED": str(int(self.profile.auth_enabled)),
            "SOMABRAIN_OPA_FAIL_CLOSED": str(int(self.profile.opa_fail_closed)),
            "SOMABRAIN_LOG_LEVEL": self.profile.log_level,
            "SOMABRAIN_MATH_BINARY_MODE": self.subsystems.math_binary_mode,
            "SOMABRAIN_SEGMENT_ALGORITHM": self.subsystems.segmentation_algorithm,
            "SOMABRAIN_HEAT_METHOD": self.subsystems.heat_diffusion_method,
            "SOMABRAIN_PREDICTOR_PROVIDER": self.subsystems.predictor_provider,
        }
```

### 4.3 Environment Variable Mapping

**SINGLE MODE VARIABLE:**
```bash
SOMABRAIN_DEPLOYMENT_MODE=production   # dev | staging | production
```

**AUTO-DERIVED (from mode):**
```bash
# These are SET BY CODE, not by user
SOMABRAIN_AUTH_ENABLED=1               # From profile
SOMABRAIN_OPA_FAIL_CLOSED=1            # From profile
SOMABRAIN_LOG_LEVEL=WARNING            # From profile
SOMABRAIN_MIN_REPLICAS=3               # From profile
```

**SUBSYSTEM MODES (configurable):**
```bash
SOMABRAIN_MATH_BINARY_MODE=pm_one
SOMABRAIN_SEGMENT_ALGORITHM=leader
SOMABRAIN_HEAT_METHOD=lanczos
SOMABRAIN_PREDICTOR_PROVIDER=mahal
```

**FEATURE FLAGS (explicit opt-in):**
```bash
SOMABRAIN_FF_COG_INTEGRATOR=1
SOMABRAIN_FF_COG_SEGMENTATION=1
SOMABRAIN_FF_MEMORY_WEIGHTING=1
```

**DEPRECATED (removed):**
```bash
SOMABRAIN_MODE                         # → SOMABRAIN_DEPLOYMENT_MODE
SOMABRAIN_DISABLE_AUTH                 # → Derived from mode
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS    # → Always true
SOMABRAIN_REQUIRE_MEMORY               # → Always true
SOMABRAIN_FORCE_FULL_STACK             # → Always true
SOMABRAIN_ALLOW_BACKEND_FALLBACKS      # → Never allowed
SOMABRAIN_ENABLE_BEST                  # → Unclear, removed
ENABLE_COG_THREADS                     # → SOMABRAIN_FF_COG_THREADS
```

---

## PART 5: DEPLOYMENT CONFIGURATIONS

### 5.1 Docker Compose

**File:** `config/deployment/docker-compose/.env.production`

```bash
# ============================================================================
# SOMABRAIN PRODUCTION CONFIGURATION
# ============================================================================

# DEPLOYMENT MODE (SINGLE SOURCE OF TRUTH)
SOMABRAIN_DEPLOYMENT_MODE=production

# Infrastructure Endpoints
SOMABRAIN_MEMORY_HTTP_ENDPOINT=https://memory.somabrain.prod
SOMABRAIN_MEMORY_HTTP_TOKEN=${MEMORY_TOKEN}  # From secrets
SOMABRAIN_REDIS_URL=redis://somabrain_redis:6379/0
SOMABRAIN_KAFKA_URL=kafka://somabrain_kafka:9092
SOMABRAIN_OPA_URL=http://somabrain_opa:8181
SOMABRAIN_POSTGRES_DSN=postgresql://${DB_USER}:${DB_PASS}@somabrain_postgres:5432/somabrain

# Subsystem Configuration
SOMABRAIN_PREDICTOR_PROVIDER=mahal
SOMABRAIN_MATH_BINARY_MODE=pm_one
SOMABRAIN_SEGMENT_ALGORITHM=leader
SOMABRAIN_HEAT_METHOD=lanczos

# Feature Flags (Production-stable only)
SOMABRAIN_FF_COG_INTEGRATOR=1
SOMABRAIN_FF_MEMORY_WEIGHTING=1
SOMABRAIN_FF_TEACH_FEEDBACK=1

# Application Settings
SOMABRAIN_DEFAULT_TENANT=production
SOMABRAIN_WORKERS=4

# DO NOT SET THESE (auto-derived from mode):
# - SOMABRAIN_AUTH_ENABLED
# - SOMABRAIN_OPA_FAIL_CLOSED
# - SOMABRAIN_LOG_LEVEL
```

### 5.2 Helm/Kubernetes

**File:** `infra/helm/charts/soma-apps/values-production.yaml`

```yaml
# ============================================================================
# SOMABRAIN PRODUCTION HELM VALUES
# ============================================================================

global:
  deploymentMode: production  # ← SINGLE SOURCE OF TRUTH

# Infrastructure scaling (derived from mode)
sb:
  replicaCount: 3
  resources:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "2000m"
      memory: "4Gi"

# Environment variables (mode-aware)
envCommon:
  SOMABRAIN_DEPLOYMENT_MODE: "production"
  SOMABRAIN_MEMORY_HTTP_ENDPOINT: "https://memory.somabrain.prod"
  SOMABRAIN_REDIS_URL: "redis://soma-infra-redis-master.soma.svc:6379/0"
  SOMABRAIN_KAFKA_URL: "kafka://soma-infra-kafka:9092"
  SOMABRAIN_POSTGRES_DSN: "postgresql://postgres:${DB_PASS}@soma-postgres:5432/somabrain"
  SOMABRAIN_OPA_URL: "http://soma-infra-opa.soma.svc:8181"
  
  # Subsystem configuration
  SOMABRAIN_PREDICTOR_PROVIDER: "mahal"
  SOMABRAIN_MATH_BINARY_MODE: "pm_one"
  SOMABRAIN_SEGMENT_ALGORITHM: "leader"
  SOMABRAIN_HEAT_METHOD: "lanczos"
  
  # Feature flags
  SOMABRAIN_FF_COG_INTEGRATOR: "1"
  SOMABRAIN_FF_MEMORY_WEIGHTING: "1"
  SOMABRAIN_FF_TEACH_FEEDBACK: "1"

# Persistence (derived from mode)
persistence:
  enabled: true
  size: 100Gi

# Monitoring (derived from mode)
prometheus:
  podMonitor:
    enabled: true
    interval: 30s
  rules:
    enabled: true

# Security (derived from mode)
networkPolicy:
  enabled: true

podDisruptionBudget:
  enabled: true
  minAvailable: 2
```

---

## PART 6: MIGRATION STRATEGY

### Phase 1: Foundation (Week 1)

**Day 1-2: Create Mode Config**
- Create `somabrain/config/mode.py`
- Implement `ModeConfig` class
- Add validation logic
- Write unit tests

**Day 3-4: Update Settings**
- Refactor `common/config/settings.py`
- Use `ModeConfig` as source of truth
- Add deprecation warnings
- Update documentation

**Day 5: Validation**
- Add startup validation
- Test all three modes
- Verify inheritance works

### Phase 2: Deployment Configs (Week 2)

**Day 1-2: Docker Compose**
- Create `.env.dev`, `.env.staging`, `.env.production`
- Update `docker-compose.yml`
- Remove redundant flags
- Test locally

**Day 3-5: Helm/Kubernetes**
- Update `values-dev.yaml`
- Update `values-staging.yaml`
- Update `values-production.yaml`
- Add mode variable to all charts
- Test in k8s cluster

### Phase 3: Code Migration (Week 3)

**Day 1-2: Update App Initialization**
- Refactor `somabrain/app.py`
- Use `ModeConfig` everywhere
- Remove flag checks
- Add mode banner

**Day 3-4: Update Subsystems**
- Refactor segmentation service
- Refactor predictor services
- Refactor memory client
- Use mode-aware defaults

**Day 5: Integration Testing**
- Test dev mode
- Test staging mode
- Test production mode
- Verify no regressions

### Phase 4: Cleanup (Week 4)

**Day 1-2: Remove Deprecated Flags**
- Remove `SOMABRAIN_DISABLE_AUTH`
- Remove `SOMABRAIN_FORCE_FULL_STACK`
- Remove `SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS`
- Remove `ENABLE_COG_THREADS`
- Update all references

**Day 3-4: Documentation**
- Update README
- Update deployment guide
- Create migration guide
- Update API docs

**Day 5: Final Validation**
- Full regression test
- Security audit
- Performance test
- Sign-off

---

## PART 7: VALIDATION & ENFORCEMENT

### 7.1 Startup Validation

```python
def validate_deployment_config():
    """Validate configuration at startup."""
    errors = []
    warnings = []
    
    # Check mode is set
    mode_env = os.getenv("SOMABRAIN_DEPLOYMENT_MODE")
    if not mode_env:
        errors.append("SOMABRAIN_DEPLOYMENT_MODE not set")
    
    # Check for deprecated flags
    deprecated = {
        "SOMABRAIN_MODE": "Use SOMABRAIN_DEPLOYMENT_MODE",
        "SOMABRAIN_DISABLE_AUTH": "Auth controlled by deployment mode",
        "SOMABRAIN_FORCE_FULL_STACK": "Always enforced",
        "ENABLE_COG_THREADS": "Use SOMABRAIN_FF_COG_THREADS",
    }
    
    for flag, msg in deprecated.items():
        if os.getenv(flag):
            warnings.append(f"{flag} is deprecated: {msg}")
    
    # Check production security
    if mode_env == "production":
        if os.getenv("SOMABRAIN_AUTH_ENABLED") == "0":
            errors.append("CRITICAL: Cannot disable auth in production")
    
    # Log results
    if errors:
        logger.error("Configuration validation FAILED:\n" + "\n".join(errors))
        sys.exit(1)
    
    if warnings:
        logger.warning("Configuration warnings:\n" + "\n".join(warnings))
```

### 7.2 Runtime Checks

```python
def enforce_mode_policies(config: ModeConfig):
    """Enforce mode policies at runtime."""
    
    # Production checks
    if config.mode == DeploymentMode.PRODUCTION:
        assert config.profile.auth_enabled, "Auth required in production"
        assert config.profile.opa_fail_closed, "OPA must fail-closed in production"
        assert config.profile.persistence_enabled, "Persistence required in production"
    
    # All modes
    assert config.profile.require_external_backends, "External backends always required"
    assert config.profile.require_memory, "Memory service always required"
```

---

## PART 8: BENEFITS

### 8.1 Clarity
- ✅ One variable controls everything
- ✅ Clear dev/staging/production separation
- ✅ No conflicting settings possible

### 8.2 Security
- ✅ Production mode enforces security by default
- ✅ Cannot accidentally disable auth
- ✅ Clear audit trail

### 8.3 Maintainability
- ✅ Single source of truth
- ✅ Easy to understand
- ✅ Reduced code complexity

### 8.4 Deployment
- ✅ Consistent across Docker and K8s
- ✅ Easy environment promotion
- ✅ Clear configuration files

### 8.5 Testing
- ✅ Easy to test each mode
- ✅ Predictable behavior
- ✅ No hidden flags

---

## PART 9: SUCCESS CRITERIA

### 9.1 Code Metrics
- ✅ Reduce config variables by 70% (20+ → 6)
- ✅ Single mode variable
- ✅ Zero deprecated flags
- ✅ 100% test coverage on mode logic

### 9.2 Deployment Metrics
- ✅ Identical structure for Docker and Helm
- ✅ Mode variable in all deployment configs
- ✅ No hardcoded credentials
- ✅ Clear dev/staging/prod separation

### 9.3 Security Metrics
- ✅ Auth always enabled in production
- ✅ No bypass flags
- ✅ OPA fail-closed in production
- ✅ Audit logging for mode changes

---

## PART 10: FINAL RECOMMENDATION

**THIS IS NOT OPTIONAL. THIS IS CRITICAL.**

The current configuration system is:
- Unmaintainable (3 different systems)
- Insecure (too many bypasses)
- Unpredictable (conflicting settings)
- Unprofessional (not production-ready)

**IMMEDIATE ACTIONS:**

1. **This Week:** Create `ModeConfig` class and validate it works
2. **Next Week:** Migrate Docker Compose to use it
3. **Week 3:** Migrate Helm/K8s to use it
4. **Week 4:** Remove all deprecated flags and ship v2.0

**TIMELINE:** 4 weeks to world-class configuration architecture.

**EFFORT:** High upfront, massive long-term payoff.

**RISK:** Low - this is pure refactoring with clear validation.

**REWARD:** Production-ready, maintainable, secure configuration system.

---

**This is the definitive architecture. No compromises. No shortcuts. World-class or nothing.**
