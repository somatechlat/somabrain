"""Unified runtime mode configuration for SomaBrain.

This module produces a single source of truth mapping `SOMABRAIN_MODE` to a
feature matrix consumed by services. It replaces scattered ENABLE_* and
SOMABRAIN_FF_* environment flags.

Modes:
  full-local : production parity on a single machine
  prod       : production deployment (same semantics, external infra)
  ci         : strict semantics, minimal optional surfaces

All modes are strict (Avro-only, fail-fast). Differences are limited to
endpoint exposure and optional experimental features.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict


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
        # Default: full-local when running interactively (heuristic: presence of HOME)
        return "full-local" if os.getenv("HOME") else "prod"
    if raw in {"full", "local", "full_local"}:
        return "full-local"
    if raw in {"production", "prod"}:
        return "prod"
    if raw in {"ci", "test", "testing"}:
        return "ci"
    # Fallback to prod for unknown values (fail-closed semantics)
    return "prod"


def get_mode_config() -> ModeConfig:
    name = _resolve_mode()
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
    if name == "ci":
        # Minimal surfaces (no segmentation / teach feedback), still strict
        return ModeConfig(
            name=name,
            enable_integrator=True,
            enable_reward_ingest=True,
            enable_learner=True,
            enable_drift=True,
            enable_auto_rollback=False,  # deterministic tests
            enable_segmentation=False,
            enable_hmm_segmentation=False,
            enable_teach_feedback=False,
            enable_metrics=True,
            enable_health_http=False,
            avro_required=True,
            fail_fast_kafka=True,
            fusion_normalization=True,
            calibration_enabled=True,
            consistency_checks=True,
        )
    # prod (default)
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


def mode_config() -> ModeConfig:
    """Return current mode configuration (reads env each call)."""
    return get_mode_config()


__all__ = [
    "ModeConfig",
    "mode_config",
    "get_mode_config",
]
