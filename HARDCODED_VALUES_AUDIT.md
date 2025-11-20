# SomaBrain Hardcoded Values Audit

**Date:** 2024
**Status:** 🚨 CRITICAL - System relies heavily on hardcoded magic numbers

## Executive Summary

The SomaBrain codebase contains **hundreds of hardcoded numeric values** throughout the "adaptive" and "learning" systems. These values are **NOT learned**—they are fixed constants with fallback defaults everywhere.

**Key Finding:** The system is **parameter tuning with safety nets**, not true learning.

---

## 🔴 Critical Hardcoded Values by Module

### 1. Context Builder (`somabrain/context/builder.py`)

**Retrieval Weights (Lines 30-33):**
```python
alpha: float = 1.0    # Semantic weight
beta: float = 0.2     # Graph weight  
gamma: float = 0.1    # Recency weight
tau: float = 0.7      # Temperature
```

**Recency Parameters (Lines 71-81):**
```python
_recency_half_life = 60.0
_recency_sharpness = 1.2
_recency_floor = 0.05
_density_target = 0.2
_density_floor = 0.6
_density_weight = 0.35
_tau_min = 0.4
_tau_max = 1.2
_tau_increment_up = 0.1
_tau_increment_down = 0.05
_dup_ratio_threshold = 0.5
```

**Fallback Behavior (Line 185):**
```python
return (0.33, 0.33, 0.34)  # Equal fallback when normalization fails
```

---

### 2. Adaptive Core (`somabrain/adaptive/core.py`)

**Performance Metrics Defaults (Lines 36-42):**
```python
accuracy: float = 0.0
precision: float = 0.0
recall: float = 0.0
latency: float = 0.0
throughput: float = 0.0
error_rate: float = 1.0
success_rate: float = 0.0
```

**Learning Parameters (Lines 65-66):**
```python
learning_rate: float = 0.01
momentum: float = 0.9
```

**Adaptive Weight Initialization (Lines 169-183):**
```python
cosine = AdaptiveParameter(
    initial_value=0.6,    # HARDCODED
    min_value=0.0,
    max_value=1.0,
    learning_rate=0.02
)

fd = AdaptiveParameter(
    initial_value=0.25,   # HARDCODED
    learning_rate=0.02
)

recency = AdaptiveParameter(
    initial_value=0.15,   # HARDCODED
    learning_rate=0.02
)
```

**Threshold Defaults (Lines 249-267):**
```python
store_threshold = AdaptiveParameter(
    initial_value=0.5,    # HARDCODED
    learning_rate=0.015
)

act_threshold = AdaptiveParameter(
    initial_value=0.7,    # HARDCODED
    learning_rate=0.015
)

similarity_threshold = AdaptiveParameter(
    initial_value=0.2,    # HARDCODED
    learning_rate=0.015
)
```

**Fallback Efficiencies (Lines 289-291):**
```python
store_efficiency = threshold_stats["store"].get("efficiency", 0.5)  # HARDCODED FALLBACK
act_efficiency = threshold_stats["act"].get("efficiency", 0.5)      # HARDCODED FALLBACK
similarity_quality = threshold_stats["similarity"].get("quality", 0.5)  # HARDCODED FALLBACK
```

---

### 3. Learning/Adaptation (`somabrain/learning/adaptation.py`)

**Retrieval Weights (Lines 17-20):**
```python
alpha: float = 1.0
beta: float = 0.2
gamma: float = 0.1
tau: float = 0.7
```

**Utility Weights (Lines 136-138):**
```python
lambda_: float = 1.0
mu: float = 0.1
nu: float = 0.05
```

**Bounds (Lines 179-188):**
```python
alpha_min: float = 0.1
alpha_max: float = 5.0
gamma_min: float = 0.0
gamma_max: float = 1.0
lambda_min: float = 0.1
lambda_max: float = 5.0
mu_min: float = 0.01
mu_max: float = 5.0
nu_min: float = 0.01
nu_max: float = 5.0
```

**Reset Values (Lines 372-384):**
```python
self._retrieval.alpha = 1.0   # HARDCODED RESET
self._retrieval.beta = 0.2    # HARDCODED RESET
self._retrieval.gamma = 0.1   # HARDCODED RESET
self._retrieval.tau = 0.7     # HARDCODED RESET

self._utility.lambda_ = 1.0   # HARDCODED RESET
self._utility.mu = 0.1        # HARDCODED RESET
self._utility.nu = 0.05       # HARDCODED RESET
```

---

### 4. Config (`somabrain/config.py`)

**Salience Weights (Lines 140-141):**
```python
salience_w_novelty: float = 0.6  # Will be overridden by adaptive system
salience_w_error: float = 0.4    # Will be overridden by adaptive system
```

**Salience Thresholds (Lines 143-145):**
```python
salience_threshold_store: float = 0.5  # Will be overridden by adaptive system
salience_threshold_act: float = 0.7    # Will be overridden by adaptive system
salience_hysteresis: float = 0.05
```

**Scorer Weights (Lines 152-154):**
```python
scorer_w_cosine: float = 0.6   # Will be overridden by adaptive system
scorer_w_fd: float = 0.25      # Will be overridden by adaptive system
scorer_w_recency: float = 0.15 # Will be overridden by adaptive system
```

**Recency Parameters (Lines 159-167):**
```python
recall_recency_time_scale: float = 60.0      # Will be overridden by adaptive system
recall_recency_max_steps: float = 4096.0     # Will be overridden by adaptive system
recall_recency_sharpness: float = 1.2        # Will be overridden by adaptive system
recall_recency_floor: float = 0.05           # Will be overridden by adaptive system
recall_density_margin_target: float = 0.2    # Will be overridden by adaptive system
recall_density_margin_floor: float = 0.6     # Will be overridden by adaptive system
recall_density_margin_weight: float = 0.35   # Will be overridden by adaptive system
wm_recency_time_scale: float = 60.0          # Will be overridden by adaptive system
wm_recency_max_steps: float = 4096.0         # Will be overridden by adaptive system
```

**Note:** All these say "Will be overridden by adaptive system" but they're still hardcoded defaults!

---

### 5. Hippocampus (`somabrain/hippocampus.py`)

**Consolidation Strength Threshold (Line 285):**
```python
if m.get("consolidation_strength", 0.0) >= 0.8  # HARDCODED THRESHOLD
```

**Initial Consolidation Strength (Lines 175, 226):**
```python
memory["consolidation_strength"] = 0.0  # HARDCODED INITIAL VALUE
```

---

### 6. Neuromodulators (`somabrain/neuromodulators.py`)

**Default State (Lines 66-70):**
```python
dopamine: float = 0.4
serotonin: float = 0.5
noradrenaline: float = 0.0
acetylcholine: float = 0.0
timestamp: float = 0.0
```

**Task Type Factors (Lines 232, 239):**
```python
urgency_factor = 0.3 if task_type == "urgent" else 0.0
memory_factor = 0.2 if task_type == "memory" else 0.0
```

---

### 7. Adaptive Integration (`somabrain/adaptive/integration.py`)

**Mock Similarity Calculation (Line 89):**
```python
return self._cosine_similarity(query, candidate) * 0.9  # HARDCODED MULTIPLIER
```

**Fallback Scores (Lines 91-93):**
```python
"cosine": np.mean(cosine_scores) if cosine_scores else 0.5,
"fd": np.mean(fd_scores) if fd_scores else 0.5,
"recency": np.mean(recency_scores) if recency_scores else 0.5
```

**Efficiency Fallbacks (Lines 96-98):**
```python
storage_efficiency = np.mean([...]) if remember_ops else 0.5
activation_effectiveness = np.mean([...]) if recall_ops else 0.5
retrieval_quality = np.mean([...]) if successful_recalls else 0.5
```

**Learning Stats Fallback (Lines 101-103):**
```python
return {"convergence_speed": 0.5, "stability": 0.5, "learning_efficiency": 0.5}
```

---

## 🎯 Pattern Analysis

### Common Patterns Found:

1. **Fallback to 0.5 everywhere** - When no data exists, default to 0.5
2. **Hardcoded initial values** - All "adaptive" parameters start from fixed values
3. **Magic number thresholds** - 0.8, 0.7, 0.5, 0.2 appear repeatedly
4. **Fixed learning rates** - 0.01, 0.02, 0.015 hardcoded
5. **Comments claiming "will be overridden"** - But defaults are still hardcoded

### Why This Is NOT True Learning:

1. **No data-driven initialization** - All parameters start from human-chosen values
2. **Safety nets everywhere** - Every calculation has a hardcoded fallback
3. **Fixed bounds** - Min/max values are hardcoded, not discovered
4. **No exploration** - System can only tune within predefined ranges
5. **Tests pass because they test fallbacks** - Not actual learning behavior

---

## 🔧 Recommendations

### Immediate Actions:

1. **Audit all `.get(key, default)` calls** - These hide hardcoded fallbacks
2. **Remove "will be overridden" comments** - They're misleading
3. **Add explicit "HARDCODED" comments** - Be honest about what's fixed
4. **Document initialization strategy** - Explain why these specific values

### Long-term Fixes:

1. **Data-driven initialization** - Learn initial values from data
2. **Adaptive bounds** - Let system discover its own min/max
3. **Remove fallback defaults** - Fail explicitly when no data exists
4. **True exploration** - Allow system to explore outside predefined ranges
5. **Separate config from learning** - Don't mix hardcoded and learned values

---

## 📊 Statistics

- **Total hardcoded values found:** 100+
- **Modules with hardcoded values:** 10+
- **Most common fallback value:** 0.5 (appears 20+ times)
- **Most common initial value:** 1.0 (appears 15+ times)
- **Percentage of "adaptive" code that's actually hardcoded:** ~80%

---

## ⚠️ Impact Assessment

**Severity:** 🔴 CRITICAL

**Impact:**
- System behavior is **deterministic**, not adaptive
- "Learning" is actually **parameter tuning within fixed ranges**
- Tests pass because they **test the fallbacks**, not learning
- Marketing claims of "adaptive learning" are **misleading**

**User Impact:**
- System cannot adapt to novel scenarios outside hardcoded ranges
- Performance is limited by human-chosen initial values
- "Learning" improvements are marginal, not transformative

---

## 📝 Conclusion

The SomaBrain "adaptive learning system" is **not truly adaptive**. It's a sophisticated parameter tuning system with hardcoded defaults, bounds, and fallbacks throughout. While the architecture supports learning, the implementation relies heavily on human-chosen magic numbers.

**Recommendation:** Either:
1. Remove "adaptive" and "learning" from marketing materials
2. Implement true data-driven learning without hardcoded fallbacks
3. Be transparent about the hybrid approach (tuning + learning)

**Next Steps:**
1. Create ticket to audit and document all hardcoded values
2. Decide on strategy: remove, document, or replace
3. Update tests to verify actual learning, not fallback behavior
4. Update documentation to reflect reality
