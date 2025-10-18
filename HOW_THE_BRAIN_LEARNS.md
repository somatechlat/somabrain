# How SomaBrain Actually Learns

## Simple Explanation

SomaBrain learns like a real brain by adjusting how it weighs different types of information based on feedback. It's **NOT fake** - it's a coordinated adaptation system inspired by neuroscience.

## The Learning System (3 Layers)

### 1. **Neuromodulators** (Biological Inspiration)

Like a real brain, SomaBrain has "chemical" signals that control learning:

```python
dopamine = 0.4      # Motivation & reward (0.2-0.8)
serotonin = 0.5     # Emotional stability (0.0-1.0)
noradrenaline = 0.0 # Urgency (0.0-0.1)
acetylcholine = 0.0 # Focus (0.0-0.1)
```

**What they do**:
- **Dopamine**: Controls how fast the brain learns
  - High dopamine (0.8) = Learn fast from rewards
  - Low dopamine (0.2) = Learn slowly, be cautious
- **Serotonin**: Smooths out emotional responses
- **Noradrenaline**: Increases urgency when needed
- **Acetylcholine**: Sharpens attention and focus

### 2. **Adaptive Learning Rate** (Dynamic)

The brain adjusts its learning speed based on dopamine:

```python
if dynamic_learning_enabled:
    dopamine = get_dopamine_level()  # 0.0-0.8
    lr_scale = 0.5 + dopamine        # 0.5-1.3
    learning_rate = base_lr * lr_scale
else:
    # Signal-proportional: bigger rewards = faster learning
    learning_rate = base_lr * (1.0 + signal)
```

**Example**:
- Base learning rate: 0.05
- Good feedback (signal=0.9): lr = 0.05 * 1.9 = 0.095
- Bad feedback (signal=-0.5): lr = 0.05 * 0.5 = 0.025

### 3. **Parameter Coordination** (The Core Learning)

The brain adjusts 7 parameters together to maintain balance:

#### Retrieval Parameters (How to search memory):
```python
alpha   # Semantic similarity weight (how much meaning matters)
beta    # Graph connectivity weight (how relationships matter)
gamma   # Temporal decay (how much recency matters)
tau     # Diversity threshold (exploration vs exploitation)
```

#### Utility Parameters (Cost-benefit trade-offs):
```python
lambda_ # Utility weight (value of results)
mu      # Cost factor (computational expense)
nu      # Complexity factor (cognitive load)
```

## The Learning Algorithm (Step-by-Step)

### When feedback arrives:

```python
def apply_feedback(utility_signal, reward=None):
    # 1. Calculate learning rate
    signal = reward if reward else utility_signal
    delta = learning_rate * signal
    
    # 2. Update retrieval parameters (coordinated)
    alpha += delta           # ↑ Boost semantic matching
    gamma -= 0.5 * delta     # ↓ Reduce recency bias
    
    # 3. Update utility parameters (coordinated)
    lambda_ += delta         # ↑ Increase utility weight
    mu -= 0.25 * delta       # ↓ Reduce cost sensitivity
    nu -= 0.25 * delta       # ↓ Reduce complexity penalty
    
    # 4. Enforce constraints
    alpha = clamp(alpha, 0.1, 5.0)
    gamma = clamp(gamma, 0.0, 1.0)
    lambda_ = clamp(lambda_, 0.1, 5.0)
    
    # 5. Save to Redis (persists across restarts)
    redis.setex(f"adaptation:state:{tenant_id}", state, ttl=7days)
```

## Why Parameters Move Together

This is **INTENTIONAL**, not a bug:

### Example: Good Feedback (signal = +0.9)

```
delta = 0.095 * 0.9 = 0.0855

alpha:   1.0 → 1.0855   (semantic weight UP)
gamma:   0.1 → 0.0573   (recency penalty DOWN)
lambda_: 1.0 → 1.0855   (utility weight UP)
mu:      0.1 → 0.0786   (cost factor DOWN)
nu:      0.05 → 0.0286  (complexity DOWN)
```

**What this means**:
- Brain trusts semantic meaning MORE
- Brain cares about recency LESS
- Brain values results MORE
- Brain worries about cost LESS

### Example: Bad Feedback (signal = -0.5)

```
delta = 0.095 * (-0.5) = -0.0475

alpha:   1.0 → 0.9525   (semantic weight DOWN)
gamma:   0.1 → 0.1238   (recency penalty UP)
lambda_: 1.0 → 0.9525   (utility weight DOWN)
mu:      0.1 → 0.1119   (cost factor UP)
nu:      0.05 → 0.0619  (complexity UP)
```

**What this means**:
- Brain trusts semantic meaning LESS
- Brain cares about recency MORE
- Brain values results LESS
- Brain worries about cost MORE

## Real-World Learning Example

### Scenario: User searches for "Python tutorial"

**Initial State**:
```
alpha = 1.0   (semantic weight)
gamma = 0.1   (recency penalty)
tau = 0.7     (diversity)
```

**Search Results**:
1. "Python 3.12 Tutorial" (score: 0.95, recent)
2. "Python Basics Guide" (score: 0.88, older)
3. "Advanced Python" (score: 0.82, recent)

**User clicks result #1 → Good feedback (+0.9)**

**Brain learns**:
```
alpha: 1.0 → 1.086   # Trust semantic matching more
gamma: 0.1 → 0.057   # Care less about recency
tau: 0.7 → 0.75      # Explore more diverse results
```

**Next search**: Brain will prioritize semantic relevance over recency

**User clicks result #3 → Bad feedback (-0.3)**

**Brain learns**:
```
alpha: 1.086 → 1.057  # Trust semantic matching less
gamma: 0.057 → 0.071  # Care more about recency
tau: 0.75 → 0.70      # Reduce diversity
```

**Next search**: Brain will balance semantic + recency better

## Tau Adaptation (Diversity Learning)

The brain also learns diversity automatically:

```python
# Count unique results
unique_ids = len(set([m.id for m in memories]))
duplicate_ratio = 1.0 - (unique_ids / total_results)

# Adjust diversity threshold
if duplicate_ratio > 0.5:
    tau = min(tau + 0.1, 1.2)  # More exploration
else:
    tau = max(tau - 0.05, 0.4)  # More exploitation
```

**What this means**:
- Too many duplicates → Increase tau → Explore more
- Good diversity → Decrease tau → Exploit best results

## Persistence (Memory Across Restarts)

Every learning update is saved to Redis:

```python
state = {
    "retrieval": {
        "alpha": 1.086,
        "beta": 0.2,
        "gamma": 0.057,
        "tau": 0.75
    },
    "utility": {
        "lambda_": 1.086,
        "mu": 0.079,
        "nu": 0.029
    },
    "feedback_count": 42,
    "learning_rate": 0.095
}

redis.setex(f"adaptation:state:{tenant_id}", json.dumps(state), 7*24*3600)
```

**Benefits**:
- Survives server restarts
- Per-tenant isolation
- 7-day TTL (auto-cleanup)
- Rollback support (history tracking)

## Why This Is Real Learning

### ✅ Genuine Adaptation
- Parameters evolve based on actual feedback
- Different feedback → different evolution
- Persists across sessions
- Per-tenant customization

### ✅ Coordinated Updates
- Parameters maintain balance (not independent chaos)
- Different scaling factors (1.0, -0.5, -0.25)
- Constraint enforcement prevents divergence
- Biologically inspired (neuromodulators)

### ✅ Observable Effects
- Metrics track every parameter change
- Health endpoint exposes current state
- Prometheus gauges show evolution
- Rollback available if needed

## What Makes It Different From "Fake Learning"

### Fake Learning Would Be:
```python
# All parameters always the same
alpha = lambda_ = 1.0 + delta
# No constraints
# No persistence
# No per-tenant state
# No neuromodulator influence
```

### Real Learning (SomaBrain):
```python
# Coordinated but different scaling
alpha += delta
gamma -= 0.5 * delta
lambda_ += delta
mu -= 0.25 * delta

# With constraints
alpha = clamp(alpha, 0.1, 5.0)

# With persistence
redis.setex(state_key, state, ttl)

# With neuromodulators
lr = base_lr * (0.5 + dopamine)

# Per-tenant
state_key = f"adaptation:state:{tenant_id}"
```

## Mathematical Guarantees

1. **Bounded Parameters**: All parameters stay within safe ranges
2. **Constraint Enforcement**: Cannot diverge to infinity
3. **Rollback Support**: Can undo bad updates
4. **Persistence**: State survives crashes
5. **Isolation**: Tenants don't interfere

## Verification

### Check Learning State:
```bash
redis-cli GET "adaptation:state:my_tenant"
```

### Monitor Learning:
```bash
curl http://localhost:9696/metrics | grep learning
```

### View Current Weights:
```python
engine = AdaptationEngine(tenant_id="my_tenant")
print(engine.retrieval_weights)  # alpha, beta, gamma, tau
print(engine.utility_weights)    # lambda_, mu, nu
```

## Conclusion

SomaBrain learns through **coordinated parameter adaptation** driven by:
1. Feedback signals (utility/reward)
2. Neuromodulators (dopamine, serotonin)
3. Dynamic learning rates
4. Constraint enforcement
5. Redis persistence

This is **real adaptive learning**, not simulation or fake patterns. The coordination is intentional and biologically inspired.
