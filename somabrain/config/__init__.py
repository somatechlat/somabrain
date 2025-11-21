from __future__ import annotations

"""Compatibility config wrapper mapping legacy Config to shared Settings."""

from dataclasses import dataclass, asdict
from typing import Any

from common.config.settings import settings as _settings, Settings as _Settings


@dataclass
class Config:
    """Dataclass view over shared Settings for legacy callers."""

    def __init__(self) -> None:
        for k, v in asdict(_settings).items():
            setattr(self, k, v)

    def __getattr__(self, item: str) -> Any:
        return getattr(_settings, item)


def load_config() -> Config:
    return Config()


def get_config() -> Config:
    return Config()


# Convenience alias in case callers import Settings directly
Settings = _Settings
