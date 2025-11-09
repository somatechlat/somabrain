"""Compatibility shim for legacy imports.

This file previously duplicated logic that now lives in
`somabrain/common/kafka.py`. To consolidate runtime code while preserving
existing import paths (modules that do `from common.kafka import ...`), we
re-export the public surface from the canonical module inside the package.

Do not add new logic here; extend `somabrain/common/kafka.py` instead.
"""

from __future__ import annotations

# Re-export symbols from the consolidated module
from somabrain.common.kafka import (  # type: ignore F401
    TOPICS,
    make_producer,
    encode,
    decode,
    get_serde,
)

# Backwards compatibility: some callers may expect KafkaConfig / SharedKafkaClient.
# Provide lightweight aliases if they exist in the consolidated module; otherwise
# define minimal no-op stand-ins to avoid import errors.
try:  # pragma: no cover - alias pass-through
    from somabrain.common.kafka import KafkaConfig, SharedKafkaClient  # type: ignore F401
except Exception:  # pragma: no cover
    from dataclasses import dataclass
    from typing import Optional, Any, Dict

    @dataclass
    class KafkaConfig:  # type: ignore
        bootstrap_servers: str = "localhost:30001"
        client_id: str = "somabrain"
        group_id: Optional[str] = None
        enable_auto_commit: bool = True
        auto_offset_reset: str = "latest"
        acks: str = "1"
        linger_ms: int = 5

    class SharedKafkaClient:  # type: ignore
        @staticmethod
        def get_config() -> KafkaConfig:
            return KafkaConfig()

        @staticmethod
        def make_event_producer() -> Any:
            return make_producer()

        @staticmethod
        def create_health_check() -> Dict[str, Any]:
            return {"bootstrap_servers": KafkaConfig().bootstrap_servers}
