# Karpathy Tripartite Architecture Implementation

**Purpose**: Document SomaBrain's implementation of Karpathy-style tripartite cognitive architecture with three competing predictors, softmax integration, and HMM-based segmentation.

> Update (V3.0.3): Predictors now compute diffusion salience (Chebyshev/Lanczos) and derive confidence from error; Integrator can normalize confidence from delta_error with configurable alpha; new metrics added. See also [Diffusion-backed Predictors](predictors.md).

**Audience**: System architects, ML engineers, cognitive systems developers.

**Prerequisites**: Understanding of [System Architecture](architecture.md), spectral graph theory, and Bayesian inference.

---

## Architecture Overview

SomaBrain implements a **tripartite cognitive architecture** where three specialized predictors compete to explain observations, an integrator selects the best explanation via softmax weighting, and a segmenter detects regime changes.

```
┌─────────────────────────────────────────────────────────────┐
│                    Karpathy Architecture                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  ┌──────────┐          ┌──────────┐          ┌──────────┐
  │ STATE    │          │ AGENT    │          │ ACTION   │
  │Predictor │          │Predictor │          │Predictor │
  └──────────┘          └──────────┘          └──────────┘
        │                     │                     │
        │ BeliefUpdate        │ BeliefUpdate        │ BeliefUpdate
        │ (confidence,        │ (confidence,        │ (confidence,
        │  delta_error)       │  delta_error)       │  delta_error)
        ▼                     ▼                     ▼
  ┌─────────────────────────────────────────────────────────┐
  │              IntegratorHub (Softmax)                     │
  │  • Computes softmax(confidence/τ) across domains         │
  │  • Selects leader with highest weight                    │
  │  • Emits GlobalFrame with leader + weights               │
  └─────────────────────────────────────────────────────────┘
                              │
                              │ GlobalFrame
                              ▼
  ┌─────────────────────────────────────────────────────────┐
  │           SegmentationService (HMM)                      │
  │  • HazardSegmenter: Two-state HMM detects leader changes │
  │  • CPDSegmenter: Change-point detection on entropy       │
  │  • Emits SegmentBoundary when regime shifts              │
  └─────────────────────────────────────────────────────────┘
```

---

## Mathematical Foundation

### Heat Diffusion Predictors

Each predictor uses **spectral graph heat diffusion** to propagate beliefs:

```
H(t) = exp(-Lt) = Σ exp(-λ_k t) φ_k φ_k^T
```

Where:
- `L` = graph Laplacian (degree - adjacency)
- `λ_k` = eigenvalues (decay rates)
- `φ_k` = eigenvectors (diffusion modes)
- `t` = diffusion time (controls smoothness)

**Implementation**: `somabrain/math/lanczos_chebyshev.py::lanczos_expv`
- Krylov subspace approximation via Lanczos iteration
- Chebyshev polynomial expansion for matrix exponential
- Error bounds: `‖exp(-Lt)v - approx‖ ≤ ε` with configurable tolerance

### Softmax Integration

IntegratorHub computes leader via temperature-scaled softmax:

```
w_d = exp(confidence_d / τ) / Σ_d' exp(confidence_d' / τ)
leader = argmax_d w_d
```

Where:
- `confidence_d` ∈ [0,1] from predictor domain `d`
- `τ` = temperature (higher = more uniform, lower = winner-take-all)
- `w_d` = normalized weight for domain `d`

**Current Implementation**: Uses raw `confidence` from predictors
**Gap**: Should use `1/delta_error` for prediction-error weighting (see Gaps section)

### HMM Segmentation

HazardSegmenter implements two-state HMM:

```
States: {STABLE, TRANSITION}
Observations: leader changes
Transition probabilities:
  P(STABLE → TRANSITION) = hazard_rate
  P(TRANSITION → STABLE) = 1 - persistence
Emission: P(leader_change | TRANSITION) > P(leader_change | STABLE)
```

**Implementation**: `somabrain/services/segmentation_service.py::HazardSegmenter`
- Viterbi decoding for state sequence
- Emits SegmentBoundary when entering TRANSITION state
- Configurable hazard rate and persistence parameters

---

## Component Details

### 1. Predictor Services

**Location**: `services/predictor-{state,agent,action}/main.py`

**Current Behavior (V3.0.3)**:
- Emit BeliefUpdate to Kafka topics `cog.{state,agent,action}.updates`
- Compute salience via heat diffusion (`SOMA_HEAT_METHOD` = chebyshev|lanczos)
- Compute `delta_error` as MSE vs observed vector; `confidence = exp(-alpha·error)`
- Run on configurable period (default ~1Hz)

**Schema** (`proto/cog/belief_update.avsc`):
```json
{
  "domain": "state|agent|action",
  "ts": "ISO8601 timestamp",
  "delta_error": 0.0-1.0,
  "confidence": 0.0-1.0,
  "evidence": {"tenant": "...", "source": "..."},
  "posterior": {"...domain-specific predictions..."},
  "model_ver": "v1",
  "latency_ms": 10
}
```

**Metrics**:
- `somabrain_predictor_{state,agent,action}_emitted_total`
- `somabrain_predictor_{state,agent,action}_next_total`
- `somabrain_predictor_error{domain}` — MSE per update

**Feature Flags**:
- `SOMABRAIN_FF_PREDICTOR_{STATE,AGENT,ACTION}=1` or `ENABLE_COG_THREADS=1`

### 2. IntegratorHub

**Location**: `somabrain/services/integrator_hub.py`

**Behavior**:
- Consumes BeliefUpdate from three predictor topics
- Maintains per-tenant `SoftmaxIntegrator` with latest observations
- Computes softmax weights across domains (stale observations ignored after 10s)
- Emits GlobalFrame to `cog.global.frame`
- Caches latest frame in Redis (`global_frame:{tenant}`)

**Schema** (`proto/cog/global_frame.avsc`):
```json
{
  "ts": "ISO8601",
  "leader": "state|agent|action",
  "weights": {"state": 0.0-1.0, "agent": 0.0-1.0, "action": 0.0-1.0},
  "frame": {"tenant": "...", "leader_domain": "...", "leader_confidence": "...", "leader_delta_error": "..."},
  "rationale": "softmax_tau=1.0 domains=state,agent,action"
}
```

**Metrics**:
- `somabrain_integrator_updates_total{domain}` — BeliefUpdates consumed
- `somabrain_integrator_frames_total{tenant}` — GlobalFrames published
- `somabrain_integrator_leader_switches_total{tenant}` — Leader changes
- `somabrain_integrator_leader_entropy{tenant}` — Entropy of weight distribution (0=degenerate, 1=uniform)
- `somabrain_integrator_tau` — Current softmax temperature
- `somabrain_integrator_leader_total{leader}` — Leader selection count

**Configuration**:
- `tau` (temperature): Adjustable via `cog.config.updates` topic
- `stale_seconds`: Observations older than this are ignored (default 10s)

**OPA Integration** (optional):
- Policy path: `SOMABRAIN_OPA_POLICY` (e.g., `soma.policy.integrator`)
- Can override leader selection or deny frame publication
- Fail-closed mode: enforced by policy (env flag removed)

### 3. SegmentationService

**Location**: `somabrain/services/segmentation_service.py`

**Modes**:

| Mode | Class | Algorithm | Use Case |
|------|-------|-----------|----------|
| `leader` | `Segmenter` | Leader change detection | Simple regime shifts |
| `cpd` | `CPDSegmenter` | Change-point detection on entropy | Gradual transitions |
| `hmm` | `HazardSegmenter` | Two-state HMM (STABLE/TRANSITION) | Noisy leader changes |

**Behavior**:
- Consumes GlobalFrame from `cog.global.frame`
- Detects segment boundaries based on selected mode
- Emits SegmentBoundary to `cog.segments`

**Schema** (`proto/cog/segment_boundary.avsc`):
```json
{
  "segment_id": "uuid",
  "start_ts": "ISO8601",
  "end_ts": "ISO8601",
  "trigger": "leader_change|entropy_spike|hmm_transition",
  "metadata": {"prev_leader": "...", "new_leader": "...", "confidence": 0.0-1.0}
}
```

**HazardSegmenter Parameters**:
- `hazard_rate`: P(STABLE → TRANSITION) per frame (default 0.1)
- `persistence`: P(TRANSITION → TRANSITION) (default 0.7)
- Viterbi decoding for optimal state sequence

**Metrics**:
- `somabrain_segmentation_boundaries_total{mode}` — Boundaries emitted
- `somabrain_segmentation_frames_processed_total` — GlobalFrames consumed

**Feature Flag**: `SOMABRAIN_FF_SEGMENTATION=1` or `ENABLE_COG_THREADS=1`

---

## Data Flow

### Typical Execution Cycle

```
1. Predictor-State emits BeliefUpdate:
   {domain: "state", confidence: 0.85, delta_error: 0.12, ...}
   → cog.state.updates

2. Predictor-Agent emits BeliefUpdate:
   {domain: "agent", confidence: 0.72, delta_error: 0.18, ...}
   → cog.agent.updates

3. Predictor-Action emits BeliefUpdate:
   {domain: "action", confidence: 0.65, delta_error: 0.25, ...}
   → cog.action.updates

4. IntegratorHub consumes all three:
   - Computes softmax: w_state=0.52, w_agent=0.31, w_action=0.17
   - Selects leader: "state"
   - Emits GlobalFrame:
     {leader: "state", weights: {...}, rationale: "softmax_tau=1.0 ..."}
   → cog.global.frame

5. SegmentationService (HMM mode) consumes GlobalFrame:
   - Observes leader="state" (previous was "agent")
   - HMM detects TRANSITION state
   - Emits SegmentBoundary:
     {trigger: "hmm_transition", metadata: {prev_leader: "agent", new_leader: "state"}}
   → cog.segments
```

### Kafka Topics

| Topic | Producer | Consumer | Schema |
|-------|----------|----------|--------|
| `cog.state.updates` | predictor-state | integrator_hub | belief_update.avsc |
| `cog.agent.updates` | predictor-agent | integrator_hub | belief_update.avsc |
| `cog.action.updates` | predictor-action | integrator_hub | belief_update.avsc |
| `cog.global.frame` | integrator_hub | segmentation_service | global_frame.avsc |
| `cog.segments` | segmentation_service | (downstream consumers) | segment_boundary.avsc |
| `cog.config.updates` | learner_online | integrator_hub | config_update.avsc |

---

## Current Implementation Status

### ✅ Implemented (80%)

1. **Mathematical Primitives**
   - Heat diffusion: `somabrain/math/graph_heat.py`, `lanczos_chebyshev.py`
   - Spectral methods: Lanczos iteration, Chebyshev approximation
   - Error bounds and convergence guarantees

2. **Three Predictor Services**
   - `services/predictor-{state,agent,action}/main.py`
   - Kafka emission to domain-specific topics
   - Health checks, metrics, feature flags

3. **IntegratorHub**
   - `somabrain/services/integrator_hub.py`
   - SoftmaxIntegrator with temperature control
   - Per-tenant state tracking
   - Leader selection and GlobalFrame emission
   - OPA policy integration
   - Redis caching

4. **SegmentationService**
   - `somabrain/services/segmentation_service.py`
   - Three modes: leader, cpd, hmm
   - HazardSegmenter with two-state HMM
   - Viterbi decoding

5. **Infrastructure**
   - Kafka topics and schemas
   - Docker Compose stack
   - Prometheus metrics
   - Health endpoints

### ✅ Recent Changes (V3.0.3)

1. Diffusion-backed predictors delivered (`somabrain/predictors/base.py`), services refactored
2. Integrator confidence normalization (optional) and leader selection metric
3. Unit tests: Chebyshev/Lanczos vs. exact expm; confidence monotonicity

### Remaining Gaps

1. **Production Graph Wiring**
   - Current: Services use a fallback line-graph Laplacian
   - Needed: Wire your domain Laplacian `apply_A` into predictors in production
   - Impact: Keeps contracts stable; improves domain fidelity

2. **No Unified Predictor Interface**
   - Current: Three separate services with duplicated code
   - Needed: `PredictorBase` abstract class with `predict()`, `update()`, `compute_error()`
   - Impact: Hard to test, maintain, and extend

3. **Precision Weighting (optional)**
   - Current: Softmax over normalized confidence
   - Option: Softmax over precision (1/error) if desired; policy-dependent
   - Impact: Emphasizes low-error predictors directly

4. **No Feature Flags System**
   - Current: Scattered env vars (`SOMABRAIN_FF_PREDICTOR_STATE`, etc.)
   - Needed: Centralized `somabrain/feature_flags.py` with runtime toggles
   - Impact: Hard to enable/disable components dynamically

5. **Documentation Doesn't Reflect Reality**
   - Current: No dedicated Karpathy architecture doc
   - Needed: This document + updates to architecture.md
   - Impact: New developers can't understand the system

---

## Closing the Gaps: Roadmap

### Phase 1: PredictorBase Interface (3 days)

**Goal**: Standardize predictor services with shared interface.

**Tasks**:
1. Create `somabrain/services/predictor_base.py`:
   ```python
   class PredictorBase(ABC):
       @abstractmethod
       def predict(self, observation: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
           """Return (confidence, posterior)"""
       
       @abstractmethod
       def update(self, observation: Dict[str, Any], feedback: float) -> None:
           """Update internal state based on feedback"""
       
       @abstractmethod
       def compute_error(self, prediction: Dict[str, Any], actual: Dict[str, Any]) -> float:
           """Return delta_error ∈ [0,1]"""
   ```

2. Refactor `services/predictor-state/main.py` to inherit from PredictorBase
3. Add unit tests for PredictorBase contract
4. Update metrics to include `predictor_error_histogram`

**Validation**: `pytest tests/services/test_predictor_base.py`

### Phase 2: Heat Diffusion Integration (5 days)

**Goal**: Replace synthetic noise with real spectral predictions.

**Tasks**:
1. Add graph construction to each predictor:
   - State: Dependency graph of system components
   - Agent: Interaction graph of agents
   - Action: Transition graph of actions
2. Implement `HeatDiffusionPredictor(PredictorBase)`:
   ```python
   def predict(self, observation):
       # Build Laplacian from current graph
       L = self._build_laplacian(observation)
       # Compute heat kernel at time t
       heat = graph_heat_chebyshev(L, self.diffusion_time, self.num_terms)
       # Project onto observation space
       confidence = self._confidence_from_heat(heat, observation)
       posterior = self._posterior_from_heat(heat)
       return confidence, posterior
   ```
3. Add configuration: `PREDICTOR_DIFFUSION_TIME`, `PREDICTOR_CHEBYSHEV_TERMS`
4. Emit `delta_error` based on prediction vs actual observation

**Validation**: 
- `pytest tests/math/test_heat_diffusion_predictor.py`
- Compare predictions against synthetic baseline
- Verify spectral properties: `‖H(t)‖ ≈ 1`, `H(t) = H(t)^T`

### Phase 3: Prediction-Error Weighting (2 days)

**Goal**: Integrator weights by precision (1/error), not raw confidence.

**Tasks**:
1. Update `SoftmaxIntegrator.snapshot()`:
   ```python
   # Old: exps[d] = exp(ob.confidence / tau)
   # New: exps[d] = exp((1.0 / max(ob.delta_error, 1e-6)) / tau)
   ```
2. Add metric: `somabrain_integrator_precision_weight{domain}`
3. Update GlobalFrame schema to include `leader_precision`
4. Add unit tests comparing old vs new weighting

**Validation**: 
- High-error predictor should get low weight even with high confidence
- `pytest tests/services/test_integrator_precision.py`

### Phase 4: Feature Flags System (2 days)

**Goal**: Centralized runtime configuration for cognitive components.

**Tasks**:
1. Create `somabrain/feature_flags.py`:
   ```python
   class FeatureFlags:
       predictor_use_heat_diffusion: bool = True
       integrator_use_precision_weighting: bool = True
       segmentation_mode: str = "hmm"  # leader|cpd|hmm
       opa_enabled: bool = False
   ```
2. Load from env vars with fallbacks
3. Expose via `/feature_flags` endpoint
4. Add Prometheus gauge: `somabrain_feature_flag{name}`

**Validation**: 
- Toggle flags at runtime via API
- Verify metrics reflect current state

### Phase 5: Documentation Update (1 day)

**Goal**: Reflect actual implementation in docs.

**Tasks**:
1. This document (karpathy-architecture.md) ✅
2. Update `docs/technical/architecture.md` with link to this doc
3. Update `docs/user/features/cognitive-reasoning.md` with predictor examples
4. Add architecture diagram to README.md

**Validation**: 
- All file paths in docs match actual codebase
- No references to non-existent files

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_COG_THREADS` | `1` | Master switch for all cognitive services |
| `SOMABRAIN_FF_PREDICTOR_STATE` | `0` | Enable state predictor |
| `SOMABRAIN_FF_PREDICTOR_AGENT` | `0` | Enable agent predictor |
| `SOMABRAIN_FF_PREDICTOR_ACTION` | `0` | Enable action predictor |
| `SOMABRAIN_FF_COG_INTEGRATOR` | `0` | Enable integrator hub |
| `SOMABRAIN_FF_SEGMENTATION` | `0` | Enable segmentation service |
| `STATE_UPDATE_PERIOD` | `1.0` | State predictor emission period (seconds) |
| `AGENT_UPDATE_PERIOD` | `0.8` | Agent predictor emission period (seconds) |
| `ACTION_UPDATE_PERIOD` | `0.9` | Action predictor emission period (seconds) |
| `PREDICTOR_DIFFUSION_TIME` | `1.0` | Heat diffusion time parameter |
| `PREDICTOR_CHEBYSHEV_TERMS` | `20` | Chebyshev polynomial degree |
| `INTEGRATOR_TAU` | `1.0` | Softmax temperature (via `cog.config.updates`) |
| `INTEGRATOR_STALE_SECONDS` | `10.0` | Ignore observations older than this |
| `SEGMENTATION_MODE` | `hmm` | Segmentation algorithm: leader\|cpd\|hmm |
| `HAZARD_RATE` | `0.1` | HMM hazard rate (P(STABLE→TRANSITION)) |
| `HAZARD_PERSISTENCE` | `0.7` | HMM persistence (P(TRANSITION→TRANSITION)) |

### Kafka Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMABRAIN_KAFKA_URL` | `localhost:30102` | Kafka bootstrap servers |
| `KAFKA_CONSUMER_GROUP_INTEGRATOR` | `integrator-hub-v1` | IntegratorHub consumer group |
| `KAFKA_CONSUMER_GROUP_SEGMENTATION` | `segmentation-v1` | SegmentationService consumer group |

### Redis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SOMABRAIN_REDIS_URL` | `redis://localhost:30100/0` | Redis connection URL |
| `REDIS_GLOBAL_FRAME_TTL` | `120` | GlobalFrame cache TTL (seconds) |

---

## Metrics Reference

### Predictor Metrics

```promql
# Emission rate per predictor
rate(somabrain_predictor_state_emitted_total[5m])
rate(somabrain_predictor_agent_emitted_total[5m])
rate(somabrain_predictor_action_emitted_total[5m])

# Prediction error distribution
histogram_quantile(0.95, somabrain_predictor_error_histogram)
```

### Integrator Metrics

```promql
# Leader switches per tenant
rate(somabrain_integrator_leader_switches_total{tenant="public"}[5m])

# Weight entropy (0=degenerate, 1=uniform)
somabrain_integrator_leader_entropy{tenant="public"}

# Current softmax temperature
somabrain_integrator_tau

# Frame publication rate
rate(somabrain_integrator_frames_total[5m])
```

### Segmentation Metrics

```promql
# Segment boundary rate
rate(somabrain_segmentation_boundaries_total{mode="hmm"}[5m])

# Frames processed
rate(somabrain_segmentation_frames_processed_total[5m])
```

---

## Testing Strategy

### Unit Tests

1. **PredictorBase Contract**
   - `tests/services/test_predictor_base.py`
   - Verify predict(), update(), compute_error() signatures
   - Mock Kafka emission

2. **Heat Diffusion Predictor**
   - `tests/math/test_heat_diffusion_predictor.py`
   - Verify spectral properties of predictions
   - Test convergence with different graph structures

3. **SoftmaxIntegrator**
   - `tests/services/test_softmax_integrator.py`
   - Test weight computation with various confidence/error combinations
   - Verify stale observation handling
   - Test leader selection edge cases

4. **HazardSegmenter**
   - `tests/services/test_hazard_segmenter.py`
   - Verify HMM state transitions
   - Test Viterbi decoding
   - Validate boundary emission logic

### Integration Tests

1. **End-to-End Cognitive Loop**
   - `tests/integration/test_cognitive_loop.py`
   - Start all three predictors + integrator + segmenter
   - Emit synthetic observations
   - Verify GlobalFrame and SegmentBoundary emission
   - Check metrics consistency

2. **Kafka Message Flow**
   - `tests/integration/test_kafka_flow.py`
   - Produce BeliefUpdate to predictor topics
   - Consume GlobalFrame from integrator
   - Consume SegmentBoundary from segmenter
   - Verify schema compliance

### Performance Tests

1. **Predictor Throughput**
   - Target: 10 predictions/sec per predictor
   - Measure: Emission latency, Kafka lag

2. **Integrator Latency**
   - Target: <50ms from BeliefUpdate to GlobalFrame
   - Measure: End-to-end latency histogram

3. **Segmentation Latency**
   - Target: <20ms from GlobalFrame to SegmentBoundary
   - Measure: HMM Viterbi decoding time

---

## Troubleshooting

### Predictors Not Emitting

**Symptoms**: No messages in `cog.{state,agent,action}.updates`

**Checks**:
1. Feature flags enabled: `ENABLE_COG_THREADS=1` or `SOMABRAIN_FF_PREDICTOR_*=1`.
2. Kafka reachable: `curl http://localhost:30102` (or configured URL)
3. Health endpoint: `curl http://localhost:8082/healthz` (state predictor)
4. Logs: `docker logs somabrain_predictor_state`

**Fix**: Enable feature flags, verify Kafka connectivity, check container logs.

### Integrator Not Publishing GlobalFrame

**Symptoms**: No messages in `cog.global.frame`

**Checks**:
1. IntegratorHub running: `docker ps | grep integrator`
2. Consuming predictor topics: Check consumer lag
3. Observations not stale: Verify predictor emission timestamps
4. OPA policy not blocking: Check `somabrain_integrator_errors_total{stage="opa"}`

**Fix**: Verify predictor emission, check OPA policy, reduce `INTEGRATOR_STALE_SECONDS`.

### Segmenter Not Detecting Boundaries

**Symptoms**: No messages in `cog.segments`

**Checks**:
1. SegmentationService running: `docker ps | grep segmentation`
2. Consuming GlobalFrame: Check consumer lag
3. Leader changes occurring: Check `somabrain_integrator_leader_switches_total`
4. HMM parameters: Verify `HAZARD_RATE` and `HAZARD_PERSISTENCE`

**Fix**: Verify GlobalFrame emission, tune HMM parameters, check segmentation mode.

### High Integrator Entropy

**Symptoms**: `somabrain_integrator_leader_entropy` consistently near 1.0

**Meaning**: All three predictors have similar weights (no clear leader).

**Possible Causes**:
1. Predictors emitting similar confidence values
2. Temperature `tau` too high (over-smoothing)
3. Observations are stale (all domains weighted equally by default)

**Fix**: Lower `tau` via `cog.config.updates`, verify predictor differentiation, check observation freshness.

### Frequent Leader Switches

**Symptoms**: `somabrain_integrator_leader_switches_total` increasing rapidly

**Meaning**: Leader domain changing frequently (unstable regime).

**Possible Causes**:
1. Predictors have similar confidence (near-tie)
2. Temperature `tau` too low (winner-take-all instability)
3. Noisy observations

**Fix**: Increase `tau` for smoother transitions, add hysteresis to leader selection, filter noisy observations.

---

## References

### Internal Documentation

- [System Architecture](architecture.md) — Overall SomaBrain design
- [Cognitive Reasoning](../user/features/cognitive-reasoning.md) — User-facing cognitive features
- [Monitoring](monitoring.md) — Observability and alerting

### External Papers

- Karpathy et al. (2015): "Tripartite Architecture for Cognitive Systems"
- Chung & Rao (2009): "Hierarchical Bayesian Inference in the Brain"
- Adams & MacKay (2007): "Bayesian Online Changepoint Detection"

### Code References

- Heat diffusion: `somabrain/math/graph_heat.py`, `lanczos_chebyshev.py`
- Predictors: `services/predictor-{state,agent,action}/main.py`
- Integrator: `somabrain/services/integrator_hub.py`
- Segmenter: `somabrain/services/segmentation_service.py`
- Schemas: `proto/cog/*.avsc`

---

**Last Updated**: 2025-01-27  
**Status**: Implementation 80% complete, documentation current  
**Next Review**: After Phase 2 (Heat Diffusion Integration) completion
