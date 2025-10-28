# SomaBrain MODE CHAOS AUDIT & CENTRALIZATION ARCHITECTURE

**Date:** 2024  
**Scope:** Complete audit of ALL modes, feature flags, and configuration chaos  
**Status:** 🔴 CRITICAL - Multiple conflicting mode systems

---

## EXECUTIVE SUMMARY

**PROBLEM:** SomaBrain has **MULTIPLE OVERLAPPING MODE SYSTEMS** scattered across the codebase with no central authority. This creates:
- Configuration chaos
- Unpredictable behavior
- Security risks
- Maintenance nightmare
- Deployment confusion

**CURRENT STATE:** At least **7 DIFFERENT MODE SYSTEMS** operating independently:
1. Deployment Mode (`SOMABRAIN_MODE`)
2. Feature Flags (20+ flags)
3. Math/BHDC Binary Mode
4. Segmentation Mode
5. Scoring Mode
6. Canary Mode
7. Memory Client Mode

**SOLUTION NEEDED:** Single centralized mode system with clear hierarchy and inheritance.

---

## 1. DEPLOYMENT MODE SYSTEM (Primary)

### Current Implementation
**Location:** `common/config/settings.py`

**Environment Variable:** `SOMABRAIN_MODE`

**Supported Values:**
- `dev` / `development` → Development mode
- `stage` / `staging` → Staging mode
- `prod` / `enterprise` / `main` → Production mode (DEFAULT)

**Mode Properties (Computed):**
```
mode_normalized → {dev, staging, prod}
mode_api_auth_enabled → {False for dev, True for staging/prod}
mode_require_external_backends → True (all modes)
mode_memstore_auth_required → True (all modes)
mode_opa_fail_closed → {False for dev, True for staging/prod}
mode_log_level → {DEBUG for dev, INFO for staging, WARNING for prod}
mode_opa_policy_bundle → {allow-dev, staging, prod}
```

### Issues
- ❌ Default is "enterprise" (confusing legacy name)
- ❌ Not consistently enforced across codebase
- ❌ Many modules ignore this and use their own flags
- ❌ No validation that mode is respected

---

## 2. FEATURE FLAG CHAOS (20+ Flags)

### Backend Enforcement Flags
```
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1  (default: False)
SOMABRAIN_REQUIRE_MEMORY=1             (default: True)
SOMABRAIN_FORCE_FULL_STACK=1           (default: False)
SOMABRAIN_ALLOW_BACKEND_FALLBACKS=0    (default: False)
SOMABRAIN_ALLOW_BACKEND_AUTO_FALLBACKS=0 (default: False)
SOMABRAIN_FORCE_EXTERNAL_REDIS=0       (default: False)
```

**Problem:** These should be derived from `SOMABRAIN_MODE`, not separate flags.

### Authentication Flags
```
SOMABRAIN_DISABLE_AUTH=0               (default: False)
```

**Problem:** Conflicts with `mode_api_auth_enabled`. Two sources of truth.

### Cognitive Thread Feature Flags
```
ENABLE_COG_THREADS=0                   (default: False)
SOMABRAIN_FF_COG_INTEGRATOR=0          (default: False)
SOMABRAIN_FF_COG_ORCHESTRATOR=0        (default: False)
SOMABRAIN_FF_COG_SEGMENTATION=0        (default: False)
SOMABRAIN_FF_COG_UPDATES=0             (default: False)
SOMABRAIN_FF_WM_UPDATES_CACHE=0        (default: False)
```

**Problem:** Should be grouped under cognitive subsystem config, not scattered.

### Predictor Feature Flags
```
SOMABRAIN_FF_PREDICTOR_STATE=1         (default: True - always on)
SOMABRAIN_FF_PREDICTOR_AGENT=1         (default: True - always on)
SOMABRAIN_FF_PREDICTOR_ACTION=1        (default: True - always on)
SOMABRAIN_PREDICTOR_PROVIDER=mahal     (default: stub)
SOMABRAIN_RELAX_PREDICTOR_READY=0      (default: False)
```

**Problem:** Predictors default ON but provider defaults to "stub" - inconsistent.

### Memory Feature Flags
```
SOMABRAIN_MEMORY_ENABLE_WEIGHTING=1    (default: False)
SOMABRAIN_MEMORY_FAST_ACK=0            (default: False)
SOMABRAIN_DEBUG_MEMORY_CLIENT=0        (default: False)
ENABLE_TIERED_MEMORY=0                 (default: False)
```

### Learning Flags
```
SOMABRAIN_LEARNING_RATE_DYNAMIC=0      (default: False)
SOMABRAIN_ENABLE_TEACH_FEEDBACK=1      (default: False)
```

### Other Flags
```
SOMABRAIN_MINIMAL_PUBLIC_API=0         (default: False)
SOMABRAIN_ENABLE_BEST=1                (default: False)
SOMABRAIN_INTEGRATOR_ENFORCE_CONF=1    (default: False)
SOMABRAIN_ENFORCE_FD_INVARIANTS=0      (default: False)
SOMABRAIN_ALLOW_FAKEREDIS=0            (default: False)
```

**TOTAL:** 20+ independent feature flags with no hierarchy or mode inheritance.

---

## 3. MATH/BHDC BINARY MODE

### Current Implementation
**Location:** `somabrain/quantum.py`, `somabrain/math/bhdc_encoder.py`

**Configuration:**
```python
math_bhdc_binary_mode: str = "pm_one"  # or "zero_one"
```

**Values:**
- `pm_one` → {-1, +1} binary encoding (DEFAULT)
- `zero_one` → {0, 1} binary encoding

**Usage:** Controls how hyperdimensional vectors are binarized.

**Issues:**
- ✅ Well-contained within math subsystem
- ⚠️ Not documented in main mode system
- ⚠️ No validation against deployment mode

---

## 4. SEGMENTATION MODE

### Current Implementation
**Location:** `somabrain/services/segmentation_service.py`

**Environment Variable:** `SOMABRAIN_SEGMENT_MODE`

**Values:**
- `leader` → Leader-change detection (DEFAULT)
- `cpd` → Change-point detection (statistical)
- `hazard` → Hazard-based detection

**Configuration:**
```
SOMABRAIN_SEGMENT_MODE=leader
SOMABRAIN_SEGMENT_MAX_DWELL_MS=0
SOMABRAIN_CPD_MIN_SAMPLES=10
SOMABRAIN_CPD_MIN_STD=0.01
SOMABRAIN_CPD_Z=2.0
SOMABRAIN_CPD_MIN_GAP_MS=1000
SOMABRAIN_HAZARD_MIN_SAMPLES=5
SOMABRAIN_HAZARD_LAMBDA=0.1
SOMABRAIN_HAZARD_VOL_MULT=2.0
```

**Issues:**
- ❌ Completely separate mode system
- ❌ No relationship to deployment mode
- ❌ Algorithm choice should be configurable per deployment

---

## 5. SCORING MODE

### Current Implementation
**Location:** `somabrain/api/memory_api.py`

**Field:** `scoring_mode: Optional[str]`

**Values:** (Not clearly documented)
- Appears to be passed through to memory service
- No validation or enum

**Issues:**
- ❌ Undocumented mode system
- ❌ No clear values or behavior
- ❌ Optional with no default

---

## 6. CANARY MODE

### Current Implementation
**Location:** `somabrain/autonomous/config.py`

**Field:** `canary_mode: bool = False`

**Purpose:** Enables canary deployments for autonomous config changes

**Behavior:**
- When enabled, config changes are staged as `canary::{param}`
- Requires explicit promotion after A/B testing
- Rollback support

**Issues:**
- ✅ Well-designed for its purpose
- ⚠️ Not integrated with deployment mode
- ⚠️ Should be deployment-mode aware (only in staging/prod)

---

## 7. MEMORY CLIENT MODE

### Current Implementation
**Location:** `somabrain/memory_client.py`

**Internal Field:** `self._mode = "http"`

**Values:**
- `http` → HTTP-based memory client (only mode currently)

**Issues:**
- ⚠️ Vestigial - only one mode exists
- ⚠️ Suggests historical gRPC or other modes were removed
- ✅ Not causing problems currently

---

## 8. HEAT DIFFUSION METHOD

### Current Implementation
**Environment Variable:** `SOMA_HEAT_METHOD`

**Values:**
- `chebyshev` → Chebyshev polynomial approximation
- `lanczos` → Lanczos iteration method

**Configuration:**
```
SOMA_HEAT_METHOD=chebyshev
SOMABRAIN_DIFFUSION_T=0.3
SOMABRAIN_CONF_ALPHA=0.95
SOMABRAIN_CHEB_K=10
SOMABRAIN_LANCZOS_M=20
```

**Issues:**
- ⚠️ Algorithm choice not tied to deployment mode
- ⚠️ Should have mode-specific defaults

---

## CURRENT .ENV CONFIGURATION ANALYSIS

### Your Active .env File
```bash
SOMABRAIN_MODE=enterprise              # ← PRIMARY MODE
SOMABRAIN_FORCE_FULL_STACK=1           # ← Should be derived from mode
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1  # ← Should be derived from mode
SOMABRAIN_REQUIRE_MEMORY=1             # ← Should be derived from mode
SOMABRAIN_PREDICTOR_PROVIDER=mahal     # ← Good (not stub)
SOMABRAIN_ENABLE_BEST=1                # ← What does this even mean?
SOMABRAIN_MEMORY_ENABLE_WEIGHTING=1    # ← Feature flag
```

**Analysis:**
- ✅ Mode is set to "enterprise" (production)
- ❌ 6 additional flags that should be mode-derived
- ❌ Redundant configuration
- ❌ Risk of conflicting settings

---

## CENTRALIZED MODE ARCHITECTURE

### Proposed Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    SOMABRAIN_MODE                           │
│              (Single Source of Truth)                       │
│                                                             │
│  Values: dev | staging | prod                              │
│  Default: prod                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ├─────────────────────────────────┐
                            │                                 │
                            ▼                                 ▼
        ┌───────────────────────────────┐   ┌───────────────────────────────┐
        │   DEPLOYMENT POLICIES         │   │   SUBSYSTEM MODES             │
        │   (Auto-derived)              │   │   (Configurable)              │
        ├───────────────────────────────┤   ├───────────────────────────────┤
        │ • auth_enabled                │   │ • math_binary_mode            │
        │ • require_external_backends   │   │ • segmentation_algorithm      │
        │ • opa_fail_closed             │   │ • heat_diffusion_method       │
        │ • log_level                   │   │ • scoring_strategy            │
        │ • metrics_detail              │   │ • canary_enabled              │
        └───────────────────────────────┘   └───────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────────────────────┐
        │           FEATURE FLAGS                               │
        │           (Opt-in overrides only)                     │
        ├───────────────────────────────────────────────────────┤
        │ • Enable experimental features                        │
        │ • Disable specific subsystems                         │
        │ • Override mode defaults (with warnings)              │
        └───────────────────────────────────────────────────────┘
```

### Mode Inheritance Table

| Setting | dev | staging | prod | Override Allowed? |
|---------|-----|---------|------|-------------------|
| **Deployment Policies** |
| auth_enabled | False | True | True | ⚠️ Yes (with warning) |
| require_external_backends | True | True | True | ❌ No |
| require_memory | True | True | True | ❌ No |
| opa_fail_closed | False | True | True | ⚠️ Yes (with warning) |
| log_level | DEBUG | INFO | WARNING | ✅ Yes |
| metrics_detail | high | medium | low | ✅ Yes |
| **Subsystem Modes** |
| math_binary_mode | pm_one | pm_one | pm_one | ✅ Yes |
| segmentation_algorithm | leader | leader | leader | ✅ Yes |
| heat_diffusion_method | chebyshev | lanczos | lanczos | ✅ Yes |
| canary_enabled | False | True | True | ✅ Yes |
| **Feature Flags** |
| cog_integrator | False | False | False | ✅ Yes |
| cog_segmentation | False | False | False | ✅ Yes |
| memory_weighting | False | False | False | ✅ Yes |
| teach_feedback | False | False | False | ✅ Yes |

---

## PROPOSED CENTRALIZED CONFIGURATION

### Single Configuration Class

```
ModeConfig
├── deployment_mode: Literal["dev", "staging", "prod"]
├── deployment_policies: DeploymentPolicies (auto-derived)
│   ├── auth_enabled: bool
│   ├── require_external_backends: bool
│   ├── require_memory: bool
│   ├── opa_fail_closed: bool
│   ├── log_level: str
│   └── metrics_detail: str
├── subsystem_modes: SubsystemModes (configurable with defaults)
│   ├── math_binary_mode: Literal["pm_one", "zero_one"]
│   ├── segmentation_algorithm: Literal["leader", "cpd", "hazard"]
│   ├── heat_diffusion_method: Literal["chebyshev", "lanczos"]
│   ├── scoring_strategy: str
│   └── canary_enabled: bool
└── feature_flags: FeatureFlags (opt-in only)
    ├── cog_integrator: bool
    ├── cog_segmentation: bool
    ├── cog_orchestrator: bool
    ├── memory_weighting: bool
    ├── teach_feedback: bool
    └── experimental_*: bool
```

### Environment Variable Mapping

**KEEP (Primary):**
```bash
SOMABRAIN_MODE=prod                    # Single source of truth
```

**KEEP (Subsystem Modes - with mode-aware defaults):**
```bash
SOMABRAIN_MATH_BINARY_MODE=pm_one      # Math subsystem
SOMABRAIN_SEGMENT_ALGORITHM=leader     # Segmentation subsystem
SOMABRAIN_HEAT_METHOD=lanczos          # Diffusion subsystem
SOMABRAIN_SCORING_STRATEGY=unified     # Scoring subsystem
```

**KEEP (Feature Flags - explicit opt-in):**
```bash
SOMABRAIN_FF_COG_INTEGRATOR=0          # Cognitive threads
SOMABRAIN_FF_COG_SEGMENTATION=0
SOMABRAIN_FF_MEMORY_WEIGHTING=0        # Memory features
SOMABRAIN_FF_TEACH_FEEDBACK=0          # Learning features
```

**DEPRECATE (Derived from mode):**
```bash
SOMABRAIN_DISABLE_AUTH                 # → mode.deployment_policies.auth_enabled
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS    # → mode.deployment_policies.require_external_backends
SOMABRAIN_REQUIRE_MEMORY               # → mode.deployment_policies.require_memory
SOMABRAIN_FORCE_FULL_STACK             # → mode.deployment_policies.require_external_backends
SOMABRAIN_ALLOW_BACKEND_FALLBACKS      # → !mode.deployment_policies.require_external_backends
SOMABRAIN_ALLOW_BACKEND_AUTO_FALLBACKS # → !mode.deployment_policies.require_external_backends
```

**CONSOLIDATE (Into feature flags):**
```bash
ENABLE_COG_THREADS                     # → SOMABRAIN_FF_COG_THREADS
ENABLE_TIERED_MEMORY                   # → SOMABRAIN_FF_TIERED_MEMORY
SOMABRAIN_ENABLE_BEST                  # → Remove (unclear purpose)
```

---

## MIGRATION STRATEGY

### Phase 1: Centralize Mode Logic (Week 1)
1. Create `somabrain/mode_config.py` with centralized ModeConfig class
2. Implement mode inheritance and validation
3. Add deprecation warnings for old flags
4. No breaking changes yet

### Phase 2: Update Subsystems (Week 2-3)
1. Refactor each subsystem to use ModeConfig
2. Add mode-aware defaults
3. Validate subsystem modes against deployment mode
4. Update documentation

### Phase 3: Deprecate Old Flags (Week 4)
1. Add loud warnings for deprecated flags
2. Update all .env files and examples
3. Update Helm charts and k8s configs
4. Migration guide for users

### Phase 4: Remove Old Flags (Month 2)
1. Remove deprecated flag support
2. Clean up code
3. Final testing
4. Release notes

---

## RECOMMENDED DEFAULT CONFIGURATIONS

### Development Mode
```bash
SOMABRAIN_MODE=dev

# Auto-derived:
# - auth_enabled=False
# - require_external_backends=True
# - opa_fail_closed=False
# - log_level=DEBUG

# Subsystem defaults:
SOMABRAIN_MATH_BINARY_MODE=pm_one
SOMABRAIN_SEGMENT_ALGORITHM=leader
SOMABRAIN_HEAT_METHOD=chebyshev
SOMABRAIN_PREDICTOR_PROVIDER=mahal

# Feature flags (opt-in):
SOMABRAIN_FF_COG_INTEGRATOR=0
SOMABRAIN_FF_MEMORY_WEIGHTING=0
```

### Staging Mode
```bash
SOMABRAIN_MODE=staging

# Auto-derived:
# - auth_enabled=True
# - require_external_backends=True
# - opa_fail_closed=True
# - log_level=INFO

# Subsystem defaults:
SOMABRAIN_MATH_BINARY_MODE=pm_one
SOMABRAIN_SEGMENT_ALGORITHM=leader
SOMABRAIN_HEAT_METHOD=lanczos
SOMABRAIN_PREDICTOR_PROVIDER=mahal

# Feature flags (testing):
SOMABRAIN_FF_COG_INTEGRATOR=1
SOMABRAIN_FF_MEMORY_WEIGHTING=1
```

### Production Mode (YOUR TARGET)
```bash
SOMABRAIN_MODE=prod

# Auto-derived:
# - auth_enabled=True
# - require_external_backends=True
# - opa_fail_closed=True
# - log_level=WARNING

# Subsystem defaults:
SOMABRAIN_MATH_BINARY_MODE=pm_one
SOMABRAIN_SEGMENT_ALGORITHM=leader
SOMABRAIN_HEAT_METHOD=lanczos
SOMABRAIN_PREDICTOR_PROVIDER=mahal

# Feature flags (stable only):
SOMABRAIN_FF_COG_INTEGRATOR=1
SOMABRAIN_FF_MEMORY_WEIGHTING=1
SOMABRAIN_FF_TEACH_FEEDBACK=1
```

---

## VALIDATION RULES

### Mode Consistency Checks
1. **Deployment mode must be valid:** `{dev, staging, prod}`
2. **Subsystem modes must be compatible with deployment mode**
3. **Feature flags cannot override critical security policies**
4. **Deprecated flags trigger warnings**
5. **Conflicting flags cause startup failure**

### Startup Validation
```python
def validate_mode_config(config: ModeConfig) -> List[str]:
    errors = []
    
    # Check deployment mode
    if config.deployment_mode not in ["dev", "staging", "prod"]:
        errors.append(f"Invalid deployment mode: {config.deployment_mode}")
    
    # Check security overrides
    if config.deployment_mode == "prod" and not config.deployment_policies.auth_enabled:
        errors.append("CRITICAL: Auth disabled in production mode")
    
    # Check deprecated flags
    if os.getenv("SOMABRAIN_DISABLE_AUTH"):
        warnings.warn("SOMABRAIN_DISABLE_AUTH is deprecated, use SOMABRAIN_MODE")
    
    return errors
```

---

## BENEFITS OF CENTRALIZATION

### 1. Predictability
- ✅ One mode variable controls all behavior
- ✅ Clear inheritance hierarchy
- ✅ No conflicting settings

### 2. Security
- ✅ Production mode enforces security by default
- ✅ Cannot accidentally disable auth in prod
- ✅ Clear audit trail of mode changes

### 3. Maintainability
- ✅ Single source of truth
- ✅ Easy to understand configuration
- ✅ Reduced code complexity

### 4. Deployment
- ✅ Simple environment-specific configs
- ✅ Clear dev/staging/prod separation
- ✅ Easy to promote between environments

### 5. Testing
- ✅ Consistent test configurations
- ✅ Easy to simulate production mode
- ✅ Clear feature flag testing

---

## CRITICAL FINDINGS

### 🔴 CRITICAL ISSUES
1. **Multiple conflicting mode systems** - No single source of truth
2. **Security bypass chaos** - Too many ways to disable auth
3. **Unpredictable behavior** - Mode interactions not defined
4. **Configuration explosion** - 20+ flags doing similar things

### 🟡 MODERATE ISSUES
1. **Subsystem modes not integrated** - Segmentation, scoring, etc. independent
2. **Feature flag sprawl** - No clear organization
3. **Default confusion** - "enterprise" mode name unclear
4. **Documentation gaps** - Mode behavior not documented

### ✅ GOOD PRACTICES FOUND
1. **Mode properties in settings.py** - Good foundation exists
2. **Canary mode design** - Well thought out
3. **Math binary mode** - Well contained
4. **Predictor defaults** - Always-on by default

---

## IMMEDIATE ACTIONS REQUIRED

### This Week
1. **Audit current production config** - What mode is actually running?
2. **Document all active flags** - What's enabled in production?
3. **Identify conflicts** - Are there contradictory settings?
4. **Create migration plan** - How to move to centralized mode?

### Next Sprint
1. **Implement ModeConfig class** - Centralized configuration
2. **Add validation** - Startup checks for mode consistency
3. **Add warnings** - Deprecation notices for old flags
4. **Update documentation** - Clear mode guide

### Next Month
1. **Migrate all subsystems** - Use ModeConfig
2. **Update deployment configs** - Helm, k8s, docker-compose
3. **Remove deprecated flags** - Clean up codebase
4. **Release v2.0** - Breaking change with migration guide

---

## CONCLUSION

**Current State:** MODE CHAOS - 7 independent mode systems, 20+ feature flags, no central authority

**Target State:** SINGLE MODE SYSTEM - One `SOMABRAIN_MODE` variable controls all deployment policies, with subsystem modes and feature flags as explicit overrides

**Impact:** HIGH - This affects every deployment, every environment, and every configuration decision

**Urgency:** CRITICAL - Current chaos creates security risks and unpredictable behavior

**Recommendation:** IMMEDIATE CENTRALIZATION - Start migration this sprint, complete within 2 months

---

**The current mode system is not sustainable. Centralization is not optional—it's critical for production readiness.**
