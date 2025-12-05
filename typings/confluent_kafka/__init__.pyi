"""Minimal type stubs for the ``confluent_kafka`` package used in SomaBrain.

Only the symbols that the codebase imports are defined here.  The stub is
intended solely for static analysis (Pyright) – the real ``confluent_kafka``
library must still be installed at runtime.

References:
* Official docs: https://github.com/confluentinc/confluent-kafka-python
* ``confluent_kafka`` package on PyPI.
"""

from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple

# -------------------------------------------------------------------
# Exceptions
# -------------------------------------------------------------------
class KafkaException(Exception):
    """Base exception for ``confluent_kafka`` errors."""

class KafkaError(Exception):
    """Error class used by the producer/consumer APIs."""

# -------------------------------------------------------------------
# Producer API (used for sending messages)
# -------------------------------------------------------------------
class Producer:
    def __init__(self, **configs: Any) -> None: ...
    def produce(
        self,
        topic: str,
        value: Optional[bytes] = None,
        key: Optional[bytes] = None,
        partition: Optional[int] = None,
        on_delivery: Optional[Callable[[Any, Any], None]] = None,
        timestamp: Optional[int] = None,
        headers: Optional[Iterable[Tuple[str, bytes]]] = None,
        **kwargs: Any,
    ) -> None: ...
    def flush(self, timeout: float = ...) -> int: ...
    def poll(self, timeout: float = ...) -> Optional[Any]: ...
    def init_transactions(self) -> None: ...
    def begin_transaction(self) -> None: ...
    def commit_transaction(self) -> None: ...
    def abort_transaction(self) -> None: ...

# -------------------------------------------------------------------
# Consumer API (used for reading messages)
# -------------------------------------------------------------------
class Consumer:
    def __init__(self, **configs: Any) -> None: ...
    def subscribe(self, topics: List[str]) -> None: ...
    def poll(self, timeout: float = ...) -> Optional[Any]: ...
    def commit(self) -> None: ...
    def close(self) -> None: ...
    def assign(self, partitions: Any) -> None: ...
    def seek(self, offset: Any) -> None: ...
    def position(self, partitions: Any) -> List[Any]: ...
    def get_watermark_offsets(self, partition: Any) -> Tuple[int, int]: ...

# -------------------------------------------------------------------
# AdminClient (used for topic/cluster management)
# -------------------------------------------------------------------
class NewTopic:
    def __init__(
        self,
        topic: str,
        num_partitions: int = 1,
        replication_factor: int = 1,
        config: Optional[Mapping[str, Any]] = None,
    ) -> None: ...

class AdminClient:
    def __init__(self, **configs: Any) -> None: ...
    def create_topics(self, new_topics: List[NewTopic], **kwargs: Any) -> Any: ...
    def delete_topics(self, topics: List[str], **kwargs: Any) -> Any: ...
    def list_topics(self, timeout: float = ...) -> Any: ...

# -------------------------------------------------------------------
# Helper types used by the library
# -------------------------------------------------------------------
Message = Any
TopicPartition = Any
PartitionMetadata = Any

__all__ = [
    "KafkaException",
    "KafkaError",
    "Producer",
    "Consumer",
    "AdminClient",
    "NewTopic",
    "Message",
    "TopicPartition",
    "PartitionMetadata",
]
