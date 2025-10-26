## Tuning

Defaults (adjust via env):

	- Warmup samples: `SOMABRAIN_CPD_MIN_SAMPLES` (default 20)
	- Z-score threshold: `SOMABRAIN_CPD_Z` (default 4.0)
	- Min gap between boundaries: `SOMABRAIN_CPD_MIN_GAP_MS` (default 1000)
	- Std-dev floor: `SOMABRAIN_CPD_MIN_STD` (default 0.02)
	- Segmentation Hazard/HMM (when `SOMABRAIN_SEGMENT_MODE=hazard`):
		- Transition probability λ: `SOMABRAIN_HAZARD_LAMBDA` (default 0.02)
		- Volatile sigma multiplier: `SOMABRAIN_HAZARD_VOL_MULT` (default 3.0)
		- Warmup samples: `SOMABRAIN_HAZARD_MIN_SAMPLES` (default 20)
		- Min gap between boundaries: `SOMABRAIN_CPD_MIN_GAP_MS` (default 1000)
- Redis TTLs: see integrator cache (10s typical)

	- For Hazard/HMM, start with small λ (0.01–0.05). Increase λ to make flips more frequent; raise `VOL_MULT` to require stronger deviations for VOLATILE.
- Alert on entropy spikes and missing updates
