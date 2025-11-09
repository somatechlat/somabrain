# Playbook: Segmentation Flood / Drought

## Flood
- Symptoms: Alert `SegmentationFlood`; >8 boundaries /5m; F1 may drop; false boundary rate may rise.
- Checks:
  - Evaluate HMM/CPD mode configuration (lambda, z_threshold).
  - Confirm input belief update rates not spiking.
  - Inspect `somabrain_seg_p_volatile` histogram for sustained high volatility.
- Actions:
  - Temporarily increase `SOMABRAIN_CPD_MIN_SAMPLES` or raise `SOMABRAIN_CPD_Z`.
  - For HMM: reduce `SOMABRAIN_HAZARD_LAMBDA`.
- Rollback: disable advanced segmentation (`ENABLE_HMM_SEGMENTATION=0`).

## Drought
- Symptoms: Alert `SegmentationDrought`; zero boundaries 30m.
- Checks:
  - Verify segmentation service process health and Kafka consumption.
  - Check leader domain variation (entropy gauge) to ensure upstream changes occur.
- Actions:
  - Lower dwell threshold (`SOMABRAIN_SEGMENT_MAX_DWELL_MS`).
  - Re-enable CPD/HMM mode if disabled.
- Rollback: fallback to leader-mode segmentation.

References: `segmentation_service.py`, evaluator metrics `somabrain_segmentation_*`.
