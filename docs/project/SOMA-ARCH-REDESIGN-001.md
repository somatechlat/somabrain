# SOMA AGENT — ENTERPRISE ARCHITECTURE REDESIGN

## Document Control

| Field | Value |
|---|---|
| Document Title | Enterprise Architecture Redesign |
| Document Identifier | SOMA-ARCH-REDESIGN-001 |
| Version | 1.0.0 |
| Date | 2026-06-15 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2026-12-28 |
## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-09-28 | SomaTech Engineering | Document control normalised: prior status `Active` normalised to `Draft` (no approver named) \| Classification added as `Internal`. |


## 1. DESIGN PRINCIPLES

1. **Core is always on. Modules are pluggable with lifecycle.**
2. **Fail-closed everywhere.** Any error = deny/degrade, never allow.
3. **Async-first.** No synchronous I/O in hot paths.
4. **Cache-first reads.** Every read goes through cache before DB.
5. **Dependency injection.** No singletons, no hidden global state.
6. **Observable.** Every operation emits metrics, traces, and structured logs.

---

## 2. MODULE SYSTEM REDESIGN

### 2.1 Module Lifecycle

```
DISCOVER → VALIDATE DEPS → INITIALIZE → HEALTH CHECK → RUNNING → SHUTDOWN
                                                             ↓
                                                          DEGRADED
                                                             ↓
                                                          RECOVERING
```

### 2.2 Module Base Class

```python
# core/module.py
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import asyncio
import logging

logger = logging.getLogger(__name__)


class ModuleState(Enum):
    DISCOVERED = "discovered"
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ModuleHealth:
    healthy: bool
    state: ModuleState
    message: str = ""
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class Module(ABC):
    """Base class for all Soma modules with lifecycle management."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique module identifier (e.g., 'billing', 'auth.keycloak')."""
        ...

    @property
    def version(self) -> str:
        """Module version for compatibility checking."""
        return "1.0.0"

    @property
    def dependencies(self) -> List[str]:
        """Module IDs this module depends on. Empty = no dependencies."""
        return []

    @property
    def conflicts_with(self) -> List[str]:
        """Module IDs that cannot coexist with this module."""
        return []

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the module. Called once at startup.

        Raise ModuleInitError if initialization fails.
        The module will be marked FAILED and not started.
        """
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start the module. Called after initialize().

        All dependencies must be RUNNING before this is called.
        """
        ...

    async def stop(self) -> None:
        """Gracefully stop the module. Called at shutdown."""
        pass

    async def health_check(self) -> ModuleHealth:
        """Return current health status.

        Called periodically by the module registry.
        If unhealthy, module state changes to DEGRADED.
        """
        return ModuleHealth(healthy=True, state=ModuleState.RUNNING)

    async def on_dependency_state_change(
        self, dependency: str, new_state: ModuleState
    ) -> None:
        """Called when a dependency changes state.

        Use this to react to dependency failures (e.g., enter degraded mode).
        """
        pass


class ModuleInitError(Exception):
    """Raised when module initialization fails."""
    pass
```

### 2.3 Module Registry with Dependency Resolution

```python
# core/module_registry.py
import asyncio
import logging
import time
from typing import Dict, List, Set, Optional, Type
from collections import defaultdict, deque

from core.module import Module, ModuleState, ModuleHealth, ModuleInitError

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """Central registry for all modules with dependency resolution,
    lifecycle management, and health monitoring."""

    def __init__(self):
        self._modules: Dict[str, Module] = {}
        self._states: Dict[str, ModuleState] = {}
        self._health: Dict[str, ModuleHealth] = {}
        self._health_task: Optional[asyncio.Task] = None
        self._initialized = False

    def register(self, module: Module) -> None:
        """Register a module. Does not start it."""
        if module.name in self._modules:
            raise ValueError(f"Module '{module.name}' already registered")
        self._modules[module.name] = module
        self._states[module.name] = ModuleState.DISCOVERED
        logger.info("Module registered: %s v%s", module.name, module.version)

    def unregister(self, name: str) -> None:
        """Unregister a module. Must be STOPPED first."""
        if self._states.get(name) not in (
            ModuleState.STOPPED, ModuleState.DISCOVERED, ModuleState.FAILED
        ):
            raise ValueError(f"Cannot unregister module '{name}' in state {self._states.get(name)}")
        self._modules.pop(name, None)
        self._states.pop(name, None)
        self._health.pop(name, None)

    async def initialize_all(self) -> None:
        """Resolve dependencies and initialize all modules in order."""
        order = self._topological_sort()
        logger.info("Module initialization order: %s", order)

        for name in order:
            module = self._modules[name]

            # Validate dependencies are running
            for dep in module.dependencies:
                if self._states.get(dep) != ModuleState.RUNNING:
                    logger.error(
                        "Module '%s' depends on '%s' which is not running (state=%s)",
                        name, dep, self._states.get(dep),
                    )
                    self._states[name] = ModuleState.FAILED
                    break
            else:
                # Initialize
                self._states[name] = ModuleState.INITIALIZING
                try:
                    await module.initialize()
                    await module.start()
                    self._states[name] = ModuleState.RUNNING
                    logger.info("Module started: %s", name)
                except (ModuleInitError, Exception) as exc:
                    logger.error("Module '%s' failed to start: %s", name, exc)
                    self._states[name] = ModuleState.FAILED

        self._initialized = True

        # Start health monitoring
        self._health_task = asyncio.create_task(self._health_loop())

    async def shutdown_all(self) -> None:
        """Shutdown all modules in reverse dependency order."""
        if self._health_task:
            self._health_task.cancel()

        order = list(reversed(self._topological_sort()))
        for name in order:
            if self._states.get(name) == ModuleState.RUNNING:
                try:
                    await self._modules[name].stop()
                    self._states[name] = ModuleState.STOPPED
                    logger.info("Module stopped: %s", name)
                except Exception as exc:
                    logger.error("Module '%s' shutdown error: %s", name, exc)

    def get_module(self, name: str) -> Optional[Module]:
        """Get a module by name."""
        return self._modules.get(name)

    def is_running(self, name: str) -> bool:
        """Check if a module is in RUNNING state."""
        return self._states.get(name) == ModuleState.RUNNING

    def get_state(self, name: str) -> Optional[ModuleState]:
        """Get module state."""
        return self._states.get(name)

    def get_all_health(self) -> Dict[str, ModuleHealth]:
        """Get health status of all modules."""
        return dict(self._health)

    def get_running_modules(self) -> List[str]:
        """Get list of running module names."""
        return [n for n, s in self._states.items() if s == ModuleState.RUNNING]

    def _topological_sort(self) -> List[str]:
        """Sort modules by dependency order (Kahn's algorithm).

        Raises ValueError if circular dependency detected.
        """
        # Build adjacency list
        in_degree: Dict[str, int] = {n: 0 for n in self._modules}
        graph: Dict[str, List[str]] = defaultdict(list)

        for name, module in self._modules.items():
            for dep in module.dependencies:
                if dep in self._modules:
                    graph[dep].append(name)
                    in_degree[name] += 1

        # Kahn's algorithm
        queue = deque([n for n, d in in_degree.items() if d == 0])
        order = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self._modules):
            missing = set(self._modules.keys()) - set(order)
            raise ValueError(f"Circular dependency detected among: {missing}")

        return order

    async def _health_loop(self) -> None:
        """Periodic health check for all running modules."""
        while True:
            try:
                await asyncio.sleep(15)  # Check every 15 seconds
                for name, module in self._modules.items():
                    if self._states.get(name) == ModuleState.RUNNING:
                        try:
                            health = await module.health_check()
                            self._health[name] = health
                            if not health.healthy:
                                self._states[name] = ModuleState.DEGRADED
                                logger.warning("Module '%s' degraded: %s", name, health.message)
                                # Notify dependents
                                await self._notify_dependents(name, ModuleState.DEGRADED)
                        except Exception as exc:
                            self._health[name] = ModuleHealth(
                                healthy=False, state=ModuleState.DEGRADED,
                                message=str(exc),
                            )
                            logger.error("Health check failed for '%s': %s", name, exc)
            except asyncio.CancelledError:
                break

    async def _notify_dependents(self, module: str, new_state: ModuleState) -> None:
        """Notify all modules that depend on the given module."""
        for name, m in self._modules.items():
            if module in m.dependencies and self._states.get(name) == ModuleState.RUNNING:
                try:
                    await m.on_dependency_state_change(module, new_state)
                except Exception as exc:
                    logger.error("Error notifying '%s' of '%s' state change: %s", name, module, exc)


# Global registry instance
_registry: Optional[ModuleRegistry] = None


def get_module_registry() -> ModuleRegistry:
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry
```

### 2.4 Module Loader with Profile Support

```python
# core/module_loader.py
import os
import logging
from typing import Dict, Type, Set, List
from pathlib import Path

from core.module import Module
from core.module_registry import get_module_registry, ModuleRegistry

logger = logging.getLogger(__name__)

# All known module classes
_MODULE_CLASSES: Dict[str, Type[Module]] = {}


def register_module_class(cls: Type[Module]) -> Type[Module]:
    """Decorator to register a module class."""
    _MODULE_CLASSES[cls.name if hasattr(cls, 'name') else cls.__name__] = cls
    return cls


def discover_modules(package_path: str = "modules") -> None:
    """Discover module classes from a package directory."""
    import importlib
    path = Path(package_path)
    if not path.exists():
        return
    for py_file in path.rglob("*.py"):
        if py_file.name.startswith("_"):
            continue
        module_path = str(py_file.relative_to(Path("."))).replace("/", ".").replace(".py", "")
        try:
            importlib.import_module(module_path)
        except Exception as exc:
            logger.warning("Failed to import module %s: %s", module_path, exc)


# Profile presets
PROFILES: Dict[str, Set[str]] = {
    "standalone": set(),  # core only
    "enterprise": {
        "auth.keycloak",
        "authz.opa",
        "authz.spicedb",
        "secrets.vault",
        "events.kafka",
        "audit",
        "billing",
    },
    "full": set(_MODULE_CLASSES.keys()),  # everything
}


async def load_modules(
    profile: str = "standalone",
    extra_modules: str = "",
) -> ModuleRegistry:
    """Load and initialize modules based on profile and extras.

    Args:
        profile: Profile name (standalone, enterprise, full)
        extra_modules: Comma-separated additional module names
    """
    registry = get_module_registry()

    # Determine which modules to enable
    enabled = PROFILES.get(profile, set()).copy()
    if extra_modules:
        for mod in extra_modules.split(","):
            enabled.add(mod.strip())

    # Register and initialize
    for name in enabled:
        cls = _MODULE_CLASSES.get(name)
        if cls:
            registry.register(cls())
        else:
            logger.warning("Module '%s' not found in registry", name)

    await registry.initialize_all()
    return registry
```

---

## 3. DATABASE LAYER REDESIGN

### 3.1 Connection Pool Architecture

```
                    ┌─────────────────────────┐
                    │     Django ASGI App      │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │   Database Router        │
                    │   (read/write split)     │
                    └───┬───────────────┬─────┘
                        │               │
              ┌─────────▼──────┐  ┌─────▼─────────┐
              │  Write Pool    │  │  Read Pool     │
              │  (Primary)     │  │  (Replicas)    │
              │  PgBouncer     │  │  PgBouncer     │
              │  max=20        │  │  max=50        │
              └────────┬──────┘  └──────┬─────────┘
                       │                │
              ┌────────▼────────────────▼─────────┐
              │         PostgreSQL Cluster         │
              │  Primary (writes) + Replica(s)     │
              └────────────────────────────────────┘
```

### 3.2 Database Router

```python
# core/db_router.py
class ReadWriteRouter:
    """Route reads to replicas, writes to primary.

    Usage in settings.py:
        DATABASE_ROUTERS = ['core.db_router.ReadWriteRouter']
    """

    def db_for_read(self, model, **hints):
        """Send reads to replica."""
        return "replica"

    def db_for_write(self, model, **hints):
        """Send writes to primary."""
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations between all databases."""
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Only allow migrations on primary."""
        return db == "default"
```

### 3.3 Async Connection Pool (settings)

```python
# settings.py — Database configuration for scale
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("SA01_DB_NAME"),
        "USER": env("SA01_DB_USER"),
        "PASSWORD": env("SA01_DB_PASSWORD"),
        "HOST": env("SA01_DB_HOST", "localhost"),
        "PORT": env("SA01_DB_PORT", "5432"),
        "CONN_MAX_AGE": 0,  # Managed by PgBouncer
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "MAX_CONNS": 20,  # Django 5.x connection pool
            "connect_timeout": 5,
            "options": "-c statement_timeout=30000",  # 30s query timeout
        },
    },
    "replica": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("SA01_DB_NAME"),
        "USER": env("SA01_DB_RO_USER", env("SA01_DB_USER")),
        "PASSWORD": env("SA01_DB_RO_PASSWORD", env("SA01_DB_PASSWORD")),
        "HOST": env("SA01_DB_REPLICA_HOST", env("SA01_DB_HOST", "localhost")),
        "PORT": env("SA01_DB_PORT", "5432"),
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "MAX_CONNS": 50,
            "connect_timeout": 5,
            "options": "-c statement_timeout=10000",  # 10s for reads
        },
    },
}
```

### 3.4 Cache Layer for Hot Paths

```python
# core/cache.py
from django.core.cache import cache
from functools import wraps
import hashlib
import json
from typing import Any, Optional, Callable

# Cache TTLs
CAPSULE_TTL = 300       # 5 minutes (changes rarely)
IQ_SETTINGS_TTL = 300   # 5 minutes (derived from capsule)
PERMISSIONS_TTL = 60    # 1 minute (can change)
AGENT_LIST_TTL = 30     # 30 seconds (frequently updated)
HEALTH_TTL = 10         # 10 seconds

def cached(ttl: int, prefix: str = ""):
    """Decorator that caches function results in Redis.

    Usage:
        @cached(ttl=300, prefix="capsule")
        async def get_capsule(capsule_id: str) -> Capsule:
            return await Capsule.objects.aget(id=capsule_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Build cache key from function name + args
            key_parts = [prefix or func.__name__] + [str(a) for a in args]
            if kwargs:
                key_parts.append(json.dumps(kwargs, sort_keys=True))
            cache_key = "soma:" + hashlib.md5(":".join(key_parts).encode()).hexdigest()

            # Try cache
            result = await cache.aget(cache_key)
            if result is not None:
                return result

            # Cache miss — call function
            result = await func(*args, **kwargs)

            # Store in cache
            if result is not None:
                await cache.aset(cache_key, result, ttl)

            return result
        return wrapper
    return decorator


def invalidate(prefix: str, *args) -> None:
    """Invalidate cached entries matching prefix + args."""
    key_parts = [prefix] + [str(a) for a in args]
    cache_key = "soma:" + hashlib.md5(":".join(key_parts).encode()).hexdigest()
    cache.delete(cache_key)
```

---

## 4. DEPENDENCY INJECTION

```python
# core/container.py
from typing import Any, Dict, Type, TypeVar, Optional, Callable
import asyncio

T = TypeVar("T")


class Container:
    """Dependency injection container.

    Replaces singleton pattern with explicit registration.

    Usage:
        container = Container()
        container.register(MemoryPort, SomaBrainMemoryAdapter)
        memory = container.resolve(MemoryPort)
    """

    def __init__(self):
        self._bindings: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._lock = asyncio.Lock()

    def register(self, interface: Type[T], implementation: T) -> None:
        """Register a concrete instance for an interface."""
        self._bindings[interface] = implementation

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a factory that creates instances on demand."""
        self._factories[interface] = factory

    def register_singleton(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a singleton factory (created once, then cached)."""
        self._factories[interface] = factory

    async def resolve(self, interface: Type[T]) -> T:
        """Resolve an interface to its implementation.

        Priority:
        1. Explicit binding (register)
        2. Singleton (created once)
        3. Factory (created each time)
        """
        # 1. Explicit binding
        if interface in self._bindings:
            return self._bindings[interface]

        # 2. Singleton
        if interface in self._singletons:
            return self._singletons[interface]

        # 3. Factory (check if it's a singleton factory)
        if interface in self._factories:
            instance = self._factories[interface]()
            # If the factory was registered via register_singleton, cache it
            if interface not in self._bindings:
                self._singletons[interface] = instance
            return instance

        raise ValueError(f"No binding for {interface}")

    def has(self, interface: Type[T]) -> bool:
        """Check if an interface has a binding."""
        return (
            interface in self._bindings
            or interface in self._factories
            or interface in self._singletons
        )

    async def shutdown(self) -> None:
        """Clear all bindings and singletons."""
        self._bindings.clear()
        self._factories.clear()
        self._singletons.clear()


# Global container
_container: Optional[Container] = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container
```

---

## 5. BACKGROUND TASK QUEUE

```python
# core/tasks.py
import asyncio
import logging
from typing import Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    retry_count: int = 0


class TaskQueue:
    """In-process async task queue with retry and dead letter.

    For production, replace with Celery/Dramatiq backed by Redis.
    This implementation works for standalone mode.
    """

    def __init__(self, max_concurrent: int = 10, max_retries: int = 3):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._results: dict[str, TaskResult] = {}
        self._max_concurrent = max_concurrent
        self._max_retries = max_retries
        self._workers: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        """Start worker tasks."""
        self._running = True
        for i in range(self._max_concurrent):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(task)
        logger.info("TaskQueue started with %d workers", self._max_concurrent)

    async def stop(self) -> None:
        """Stop all workers."""
        self._running = False
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def submit(
        self,
        func: Callable,
        *args: Any,
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Submit a task for background execution.

        Returns task_id for status checking.
        """
        task_id = task_id or str(uuid4())
        self._results[task_id] = TaskResult(
            task_id=task_id, status=TaskStatus.PENDING
        )
        await self._queue.put((task_id, func, args, kwargs, 0))
        return task_id

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get task result by ID."""
        return self._results.get(task_id)

    async def _worker(self, name: str) -> None:
        """Worker coroutine that processes tasks from the queue."""
        while self._running:
            try:
                task_id, func, args, kwargs, retries = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
                self._results[task_id].status = TaskStatus.RUNNING

                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

                    self._results[task_id].status = TaskStatus.COMPLETED
                    self._results[task_id].result = result
                    self._results[task_id].completed_at = datetime.utcnow()

                except Exception as exc:
                    if retries < self._max_retries:
                        # Retry
                        self._results[task_id].retry_count = retries + 1
                        self._results[task_id].status = TaskStatus.RETRYING
                        await self._queue.put(
                            (task_id, func, args, kwargs, retries + 1)
                        )
                        logger.warning(
                            "Task %s failed (retry %d/%d): %s",
                            task_id, retries + 1, self._max_retries, exc,
                        )
                    else:
                        # Dead letter
                        self._results[task_id].status = TaskStatus.FAILED
                        self._results[task_id].error = str(exc)
                        self._results[task_id].completed_at = datetime.utcnow()
                        logger.error("Task %s failed permanently: %s", task_id, exc)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break


# Global task queue
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue
```

---

## 6. API VERSIONING

```python
# core/api_version.py
from functools import wraps
from typing import Callable, Optional
from ninja import Router


class APIVersion:
    """API version management.

    Usage:
        v2 = APIVersion(2)
        v3 = APIVersion(3)

        @v2.router.get("/agents")
        async def list_agents_v2(request): ...

        @v3.router.get("/agents")
        async def list_agents_v3(request): ...
    """

    def __init__(self, version: int, deprecated: bool = False):
        self.version = version
        self.deprecated = deprecated
        self.router = Router(tags=[f"v{version}"])

    def mount(self, parent: Router, prefix: str = "") -> None:
        """Mount this version's router on a parent router."""
        full_prefix = f"/v{self.version}"
        if prefix:
            full_prefix += f"/{prefix}"
        parent.add_router(full_prefix, self.router)

        if self.deprecated:
            # Add deprecation header middleware
            pass


# Usage in admin/api.py:
# v2 = APIVersion(2)
# v3 = APIVersion(3, deprecated=False)
# v2.mount(master_router)
# v3.mount(master_router)
```

---

## 7. MIGRATION PATH

### Phase 1: Module System (Week 1-2)
1. Create `core/module.py`, `core/module_registry.py`, `core/module_loader.py`
2. Convert existing services to modules (billing, auth, etc.)
3. Wire module loader into Django startup

### Phase 2: Database (Week 3-4)
1. Add read replica configuration
2. Add DatabaseRouter
3. Add cache decorators to hot paths
4. Add connection pooling settings

### Phase 3: DI Container (Week 5-6)
1. Create `core/container.py`
2. Register all services in container
3. Replace singleton patterns with container.resolve()

### Phase 4: Task Queue (Week 7-8)
1. Create `core/tasks.py`
2. Move background operations to task queue
3. Add task status API endpoint

### Phase 5: API Versioning (Week 9)
1. Create `core/api_version.py`
2. Version existing endpoints as v2
3. Prepare v3 for new features

---

End of Document
