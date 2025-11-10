"""Unified runtime mode + feature resolution for SomaBrain.

Single source of truth for behaviour:
    Modes (only two):
        - full-local : production parity on a single machine (all features ON)
        - prod       : production deployment (same semantics, external secrets/infra)

Strict defaults: Avro-only, fail‑fast Kafka, no mock backends. Legacy ENABLE_* or
SOMABRAIN_FF_* env flags are removed. Optional operator overrides are persisted
in a JSON file (``SOMABRAIN_FEATURE_OVERRIDES`` path, default ``./data/feature_overrides.json``)
listing disabled feature keys. Overrides are applied only in ``full-local`` mode;
in ``prod`` they are ignored (fail‑closed semantics).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List
import json
from pathlib import Path


@dataclass(frozen=True)
class ModeConfig:
    name: str
    enable_integrator: bool
    enable_reward_ingest: bool
    enable_learner: bool
    enable_drift: bool
    enable_auto_rollback: bool
    enable_segmentation: bool
    enable_hmm_segmentation: bool
    enable_teach_feedback: bool
    enable_metrics: bool
    enable_health_http: bool
    avro_required: bool
    fail_fast_kafka: bool
    fusion_normalization: bool
    calibration_enabled: bool
    consistency_checks: bool

    def as_dict(self) -> Dict[str, bool]:  # convenience for logging/metrics
        return {k: getattr(self, k) for k in self.__dataclass_fields__ if k != "name"}


def _resolve_mode() -> str:
    raw = (os.getenv("SOMABRAIN_MODE") or "").strip().lower()
    if not raw:
        return "full-local" if os.getenv("HOME") else "prod"
    if raw in {"full", "local", "full_local"}:
        return "full-local"
    if raw in {"production", "prod", "enterprise"}:
        return "prod"
    # Unknown -> prod (fail‑closed)
    return "prod"


def _load_overrides() -> List[str]:
    """Load disabled feature keys from the overrides file.

    File format (JSON): {"disabled": ["calibration", "fusion_normalization", ...]}
    In full-local mode these are applied; ignored in prod.
    """
    path = os.getenv("SOMABRAIN_FEATURE_OVERRIDES", "./data/feature_overrides.json")
    try:
        p = Path(path)
        if not p.exists():
            return []
        data = json.loads(p.read_text(encoding="utf-8"))
        disabled = data.get("disabled")
        if isinstance(disabled, list):
            return [str(x).strip().lower() for x in disabled]
    except Exception:
        pass
    return []


def get_mode_config() -> ModeConfig:
    name = _resolve_mode()
    # full-local: all feature surfaces on
    if name == "full-local":
        return ModeConfig(
            name=name,
            enable_integrator=True,
            enable_reward_ingest=True,
            enable_learner=True,
            enable_drift=True,
            enable_auto_rollback=True,
            enable_segmentation=True,
            enable_hmm_segmentation=True,
            enable_teach_feedback=True,
            enable_metrics=True,
            enable_health_http=True,
            avro_required=True,
            fail_fast_kafka=True,
            fusion_normalization=True,
            calibration_enabled=True,
            consistency_checks=True,
        )
    # prod: same semantics (strict, all ON) – operational differences handled outside python.
    return ModeConfig(
        name="prod",
        enable_integrator=True,
        enable_reward_ingest=True,
        enable_learner=True,
        enable_drift=True,
        enable_auto_rollback=True,
        enable_segmentation=True,
        enable_hmm_segmentation=True,
        enable_teach_feedback=True,
        enable_metrics=True,
        enable_health_http=True,
        avro_required=True,
        fail_fast_kafka=True,
        fusion_normalization=True,
        calibration_enabled=True,
        consistency_checks=True,
    )


def mode_config() -> ModeConfig:
    """Return current mode configuration (reads env each call)."""
    return get_mode_config()


def feature_enabled(key: str) -> bool:
    """Return whether a feature key is enabled under current mode + overrides.

    Supported keys: integrator, reward_ingest, learner, drift, auto_rollback,
    segmentation, hmm_segmentation, teach_feedback, metrics, health_http,
    fusion_normalization, calibration, consistency_checks.
    """
    cfg = mode_config()
    mapping = {
        "integrator": cfg.enable_integrator,
        "reward_ingest": cfg.enable_reward_ingest,
        "learner": cfg.enable_learner,
        "drift": cfg.enable_drift,
        "auto_rollback": cfg.enable_auto_rollback,
        "segmentation": cfg.enable_segmentation,
        "hmm_segmentation": cfg.enable_hmm_segmentation,
        "teach_feedback": cfg.enable_teach_feedback,
        "metrics": cfg.enable_metrics,
        "health_http": cfg.enable_health_http,
        "fusion_normalization": cfg.fusion_normalization,
        "calibration": cfg.calibration_enabled,
        "consistency_checks": cfg.consistency_checks,
    }
    base = mapping.get(key, True)
    # Apply overrides only in full-local mode
    if cfg.name == "full-local":
        disabled = _load_overrides()
        if key in disabled:
            return False
    return base
