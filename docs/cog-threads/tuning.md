## Tuning

Defaults (adjust via env):

- Predictor debounce: `MIN_DWELL_MS` (per predictor service)
- Integrator softmax temperature `τ`: set in code (SoftmaxIntegrator), expose via env if needed
- Segmentation max dwell: `SOMABRAIN_SEGMENT_MAX_DWELL_MS`
- Segmentation CPD (when `SOMABRAIN_SEGMENT_MODE=cpd`):
	- Warmup samples: `SOMABRAIN_CPD_MIN_SAMPLES` (default 20)
	- Z-score threshold: `SOMABRAIN_CPD_Z` (default 4.0)
	- Min gap between boundaries: `SOMABRAIN_CPD_MIN_GAP_MS` (default 1000)
	- Std-dev floor: `SOMABRAIN_CPD_MIN_STD` (default 0.02)
- Redis TTLs: see integrator cache (10s typical)

Guidelines:
- Start with higher dwell to reduce chatter; lower gradually while watching `leader_entropy`
- For CPD, start with higher Z (4–6), then tighten as SNR improves; ensure `MIN_SAMPLES` ≥ 10
- Cap predictor output rate with `*_UPDATE_PERIOD` envs per service
- Alert on entropy spikes and missing updates
