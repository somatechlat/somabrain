## Tuning

Defaults (adjust via env):

- Predictor debounce: `MIN_DWELL_MS` (per predictor service)
- Integrator softmax temperature `τ`: set in code (SoftmaxIntegrator), expose via env if needed
- Segmentation max dwell: `SOMABRAIN_SEGMENT_MAX_DWELL_MS`
- Redis TTLs: see integrator cache (10s typical)

Guidelines:
- Start with higher dwell to reduce chatter; lower gradually while watching `leader_entropy`
- Cap predictor output rate with `*_UPDATE_PERIOD` envs per service
- Alert on entropy spikes and missing updates
