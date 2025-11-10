import os
from somabrain.modes import mode_config


def test_full_local_mode_matrix():
    os.environ["SOMABRAIN_MODE"] = "full-local"
    cfg = mode_config()
    assert cfg.enable_integrator
    assert cfg.enable_reward_ingest
    assert cfg.enable_learner
    assert cfg.enable_drift
    assert cfg.avro_required
    assert cfg.fail_fast_kafka
    assert cfg.calibration_enabled
    assert cfg.fusion_normalization


def test_ci_mode_minimal_surfaces():
    os.environ["SOMABRAIN_MODE"] = "ci"
    cfg = mode_config()
    assert cfg.enable_integrator and cfg.enable_drift
    assert not cfg.enable_segmentation
    assert not cfg.enable_teach_feedback
    assert not cfg.enable_hmm_segmentation
    assert not cfg.enable_auto_rollback  # deterministic tests
    assert cfg.avro_required and cfg.fail_fast_kafka
