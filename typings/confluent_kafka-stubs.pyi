"""
Type stubs for confluent_kafka to resolve Pyright import errors.
"""
from typing import Any, Callable

class Message:
    """Kafka message type stub."""
    key: bytes | None
    value: bytes | None
    topic: str
    partition: int
    offset: int
  
class Producer:
    """Kafka producer type stub."""
    def __init__(self, config: dict[str, Any]): ...
    def poll(self, timeout: float) -> None: ...
    def produce(self, topic: str, key: bytes, value: bytes, 
               on_delivery: Callable | None = None, 
               partition: int = -1) -> None: ...
    def flush(self, timeout: float | None = None) -> int: ...

class Consumer:
    """Kafka consumer type stub."""
    def __init__(self, config: dict[str, Any]): ...
    def poll(self, timeout: float) -> Message | None: ...
    def commit(self, offsets: list[Any] | None = None) -> None: ...
    def close(self) -> None: ...

def KafkaException(Exception): ...
