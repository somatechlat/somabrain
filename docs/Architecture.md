# SomaBrain Architecture — Biology x Hypervectors

Purpose
- Agent-grade cognition: attention, memory, prediction, reflection.
- Grounded in biology/chemistry; powered by hyperdimensional computing.
- Imitation principle: we deliberately imitate biological and biochemical mechanisms (not superficial mimicry) with simple, testable code abstractions.

System Map (Anatomy → Modules)
- ThalamusRouter: input gateway, normalization, attention routing, rate limits.
- PrefrontalWM: working-memory buffer; cosine/cleanup recall; novelty estimation.
  - HRR Context: superposed context vector + cleanup dictionary (anchors), per tenant, behind `use_hrr` flag.
- HippocampusEpisodic: episodic writes/recall via SomaFractalMemory (LTM).
- CortexSemantic: semantic summaries, rules, personality; consolidation target.
- AmygdalaSalience: salience = f(novelty, prediction error, goals, neuromods).
- CerebellumPredictor: pluggable predictors (stub → LLM/ML) with error bounds.
- ACCMonitor: conflict/error detection; emits corrective semantic “lessons”.
- DMNReflector: background reflection; clustering + summarization; reconsolidation.
- BasalGangliaPolicy: gating thresholds (store/act); go/no‑go decisions.
- Neuromodulators: Dopamine, Serotonin, Noradrenaline, ACh as gain controllers.
- CorpusCallosumBus: inter‑agent event bus (future: Kafka/RabbitMQ). 
- PituitaryHormone: global state broadcast (mood/time-of-day) → config modulation.
- QuantumLayer (future): HRR/VSA superposition, binding/unbinding, permutations.

Data Model
- MemoryRecord: {type: episodic|semantic, payload, importance, timestamp, links?}.
- WMItem: {vector256, payload, last_access} in PrefrontalWM.
- SalienceDecision: {novelty, pred_error, neuromod, score, gate:{store,act}}.
- PredictionResult: {predicted_vec|outcome, actual_vec|outcome, error∈[0,1]}.
- ReflectSummary: {cluster_id, summary_text, source_coords[], confidence}.

Control Flows
- /act: Thalamus → WM recall → Memory recall → Predictor → ACC → Salience → Policy → gated writes (Episodic + WM admit). 
- /recall: WM top‑k + LTM hybrid; merge/rank (future learned ranker).
- /remember: direct episodic write + WM admit (bypasses salience by intent).
- /reflect: DMN clusters episodics → Cortex writes summaries → link updates.

Superposition/HRR Spec (First‑Class Primitive)
- Dimensionality: default HRR 8192–16384 for capacity; 256‑D deterministic path for low‑footprint mode.
- Seeding: deterministic RNG seeds from Blake2b(text) for stable encodings.
- Operations (dense HRR):
  - superpose(a,b): normalize(a + b);
  - bind(a,b): circular convolution (FFT domain);
  - unbind(a,b): circular correlation (inverse of bind);
  - permute(a): fixed random permutation π; positional/time encoding via π^t;
  - cleanup(q, dict): nearest neighbor in clean‑up memory by cosine.
- Temporal encoding: context_t = superpose(context_{t-1}, permute(item_t)).
- Graph links: edge(A,B) = superpose(A, bind(LINK, B)); k‑hop via iterative bind/cleanup.
- Compression: Johnson–Lindenstrauss random projections for transport; product quantization in vector DBs.

Multi‑tenancy
- Tenant isolation at namespace and WM/HRR context levels; LRU eviction of least‑recent tenants.
- Rate limiting per tenant (token bucket) and short‑TTL recall cache to reduce backend load.

Salience & Neuromodulators
- Score: s = w_novelty·(1−cos(q,context)) + w_error·error + w_goal·goal_signal.
- Dopamine: scales prediction‑error weight; boosts consolidation after reward.
- NE: adjusts recall/admission thresholds under urgency/load (gain control).
- ACh: raises encoding focus → higher novelty threshold to admit.
- Serotonin: smooths fluctuations; stabilizes long‑horizon adjustments/personality.

Predict & Error
- Predictor API: predict(x) → predicted, compare(y) → error; vector/text modes.
- Error metric: cosine residual in HRR space; bounded [0,1].
- Self‑correction: ACC emits semantic “lesson” when error>τ; links corrective to source.

Memory Integration (SomaFractalMemory)
- Local mode: in‑proc factory with in‑memory vectors for dev/testing.
- HTTP mode: calls example FastAPI; token optional; same schemas.
- Store both: raw payload + HRR vector for hybrid search/recall.
- Graph: link episodic↔semantic; causal/related edges with Hebbian weight updates.

Migration & Multi‑Agent
- Export: JSONL bodies + Manifest (version, seeds, permutations, thresholds, neuromod profile, cleanup dict stats).
- Import: restore seeds/π; replay WM warm‑start from anchors; verify alignment.
- Alignment (cross‑agent): Procrustes mapping between HRR spaces when seeds differ; otherwise share keys/π.
- Bus: superposed messages broadcast; recipients unbind with shared keys.

Observability & SLOs
- Metrics: HTTP count/latency; WM hits/misses; salience decisions; predictor error histogram; reflection throughput; LTM store/recall latency; cleanup success rate; superposition saturation.
- Logs: structured JSON with task IDs, salience explain, neuromod state, memory coords.
- SLOs (initial):
  - /act p95 < 150ms (local predictors), < 600ms (LLM predictor);
  - reflection batch throughput ≥ 1k episodics/min on 8k HRR;
  - cleanup accuracy ≥ 0.95 for single‑item retrieval at 0.1 density.

Security & Privacy
- Tokens for SomaBrain and Memory APIs; rate limits at Thalamus.
- Optional field‑level encryption (via memory layer’s Fernet) for sensitive payloads.
- Redaction list for logs/metrics; privacy‑preserving analytics on vectors.

Deployment
- Stateless API; per‑process WM; scale with workers; sticky sessions optional.
- Dev profile: local memory; Prod profile: HTTP memory + external predictor; configurable via Dynaconf.

Open Questions
- Shared WM across workers/users? (Default: per‑instance.)
- Salience auto‑tuning per domain/task?
- Schema/versioning cadence for payloads and act outputs?
- Alignment strategy for heterogeneous agents at scale?
