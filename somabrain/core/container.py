"""Dependency injection container for runtime singletons.

This module provides a thread-safe container for managing application-wide
singletons without relying on module-level global state. Components are
registered with factory functions and instantiated lazily on first access.

Usage:
    # Registration (typically in bootstrap)
    container.register("memory_gateway", create_memory_gateway)

    # Access (anywhere in the application)
    gateway = container.get("memory_gateway")

    # Testing (reset between tests)
    container.reset()
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

T = TypeVar("T")


@dataclass
class Container:
    """Thread-safe dependency injection container.

    Provides lazy instantiation of singletons with explicit lifecycle management.
    All access is thread-safe via a reentrant lock.

    Attributes:
        _instances: Cache of instantiated singletons
        _factories: Registered factory functions for lazy instantiation
        _lock: Reentrant lock for thread safety
    """

    _instances: dict[str, Any] = field(default_factory=dict)
    _factories: dict[str, Callable[[], Any]] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def register(self, name: str, factory: Callable[[], T]) -> None:
        """Register a factory function for lazy instantiation.

        Args:
            name: Unique identifier for the dependency
            factory: Zero-argument callable that creates the instance

        Note:
            If a factory is already registered for this name, it will be
            overwritten. If an instance already exists, it will be cleared.
        """
        with self._lock:
            self._factories[name] = factory
            # Clear any existing instance to allow re-registration
            self._instances.pop(name, None)

    def get(self, name: str) -> Any:
        """Get or create instance by name.

        Args:
            name: Identifier of the registered dependency

        Returns:
            The singleton instance (created on first access)

        Raises:
            KeyError: If no factory is registered for the given name
        """
        with self._lock:
            if name not in self._instances:
                if name not in self._factories:
                    raise KeyError(f"No factory registered for '{name}'")
                self._instances[name] = self._factories[name]()
            return self._instances[name]

    def has(self, name: str) -> bool:
        """Check if a factory is registered for the given name."""
        with self._lock:
            return name in self._factories

    def is_instantiated(self, name: str) -> bool:
        """Check if an instance has been created for the given name."""
        with self._lock:
            return name in self._instances

    def reset(self) -> None:
        """Clear all instances (for testing).

        This clears the instance cache but preserves factory registrations,
        allowing fresh instances to be created on next access.
        """
        with self._lock:
            self._instances.clear()

    def reset_all(self) -> None:
        """Clear all instances and factory registrations.

        Use this for complete container reset, typically in test teardown.
        """
        with self._lock:
            self._instances.clear()
            self._factories.clear()


# Global container instance - the single source of truth for DI
container = Container()
