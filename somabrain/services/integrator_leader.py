"""Integrator Leader Election Service

Implements leader election for integrator instances using Redis-based
distributed locking with min_dwell and entropy_cap constraints.

Key features:
- Redis-backed leader election with TTL
- Per-tenant leader selection
- Dwell time tracking and enforcement
- Entropy cap validation
- Automatic failover and re-election
- Health monitoring and metrics
"""

from __future__ import annotations

import os
from django.conf import settings
import time
import threading
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from somabrain.common.infra import assert_ready
from somabrain.modes import feature_enabled
import somabrain.metrics as app_metrics

# Leader election metrics
LEADER_ELECTION_TOTAL = app_metrics.get_counter(
    "somabrain_leader_election_total",
    "Total leader election attempts",
    labelnames=["tenant", "outcome"],
)

LEADER_ELECTION_LATENCY = app_metrics.get_histogram(
    "somabrain_leader_election_latency_seconds",
    "Time taken to complete leader election",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
)

LEADER_CURRENT = app_metrics.get_gauge(
    "somabrain_leader_current",
    "Current leader instance per tenant",
    labelnames=["tenant", "instance_id"],
)

LEADER_TENURE = app_metrics.get_gauge(
    "somabrain_leader_tenure_seconds",
    "Current leader tenure duration",
    labelnames=["tenant"],
)

LEADER_MIN_DWELL = app_metrics.get_gauge(
    "somabrain_leader_min_dwell_ms",
    "Current minimum dwell requirement",
    labelnames=["tenant"],
)

LEADER_ENTROPY_CAP = app_metrics.get_gauge(
    "somabrain_leader_entropy_cap", "Current entropy cap limit", labelnames=["tenant"]
)

LEADER_HEALTH_CHECK = app_metrics.get_gauge(
    "somabrain_leader_health_check",
    "Leader health check result",
    labelnames=["tenant", "check_type"],
)


@dataclass
class LeaderConfig:
    """Configuration for leader election per tenant."""

    min_dwell_ms: int = 50  # Minimum time leader must hold position
    entropy_cap: float = 0.3  # Maximum entropy before leader change
    lock_ttl_seconds: int = 30  # Redis lock TTL
    heartbeat_interval_seconds: int = 10  # Health check interval
    reelection_threshold_ms: int = 100  # Time before triggering re-election


@dataclass
class LeaderState:
    """Current leader state for a tenant."""

    instance_id: str
    start_time: float
    last_heartbeat: float
    min_dwell_ms: int
    entropy_cap: float
    config_version: int = 1


class IntegratorLeaderElection:
    """Redis-based leader election service for integrator instances."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        # Prefer explicit argument; fall back to central settings.
        """Initialize the instance."""

        self._redis_url = redis_url or settings.SOMABRAIN_REDIS_URL or ""
        self._redis_client = None
        self._leader_states: Dict[str, LeaderState] = {}
        self._configs: Dict[str, LeaderConfig] = {}
        self._lock_prefix = "integrator_leader"
        # Use centralized configuration for hostname
        self._instance_id = f"{settings.SOMABRAIN_HOST}-{int(time.time())}"
        self._running = False
        self._heartbeat_thread: Optional[threading.Thread] = None

        # Initialize Redis client
        self._init_redis()

        # Load tenant configurations
        self._load_configs()

    def _init_redis(self) -> None:
        """Initialize Redis client with fail-fast behavior."""
        if not self._redis_url:
            raise RuntimeError("Redis URL not configured for leader election")

        try:
            import redis

            self._redis_client = redis.from_url(
                self._redis_url,
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30,
            )
            # Test connection
            self._redis_client.ping()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Redis for leader election: {e}")

    def _load_configs(self) -> None:
        """Load leader election configurations from YAML file."""
        try:
            import yaml

            config_path = (
                settings.SOMABRAIN_LEARNING_TENANTS_FILE
                or settings.LEARNING_TENANTS_CONFIG
                or "config/learning.tenants.yaml"
            )

            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}

                for tenant, tenant_cfg in data.items():
                    if isinstance(tenant_cfg, dict):
                        config = LeaderConfig()

                        # Load min_dwell
                        min_dwell = tenant_cfg.get("min_dwell_ms")
                        if isinstance(min_dwell, int) and min_dwell > 0:
                            config.min_dwell_ms = min_dwell

                        # Load entropy_cap
                        entropy_cap = tenant_cfg.get("entropy_cap")
                        if (
                            isinstance(entropy_cap, (int, float))
                            and 0 < entropy_cap <= 1.0
                        ):
                            config.entropy_cap = float(entropy_cap)

                        # Load other settings
                        lock_ttl = tenant_cfg.get("leader_lock_ttl_seconds")
                        if isinstance(lock_ttl, int) and lock_ttl > 0:
                            config.lock_ttl_seconds = lock_ttl

                        self._configs[tenant] = config

                        # Update metrics
                        LEADER_MIN_DWELL.labels(tenant=tenant).set(config.min_dwell_ms)
                        LEADER_ENTROPY_CAP.labels(tenant=tenant).set(config.entropy_cap)

        except Exception as e:
            # Use defaults for all tenants if config loading fails
            print(f"Warning: Failed to load leader configs: {e}")

    def get_config(self, tenant: str) -> LeaderConfig:
        """Get leader election configuration for a tenant."""
        return self._configs.get(tenant, LeaderConfig())

    def _get_lock_key(self, tenant: str) -> str:
        """Get Redis lock key for a tenant."""
        return f"{self._lock_prefix}:{tenant}"

    def is_leader(self, tenant: str) -> bool:
        """Check if this instance is the leader for a tenant."""
        try:
            lock_key = self._get_lock_key(tenant)
            lock_value = self._redis_client.get(lock_key)

            if lock_value:
                leader_id = lock_value.decode("utf-8")
                is_current_leader = leader_id == self._instance_id

                # Update metrics
                LEADER_CURRENT.labels(tenant=tenant, instance_id=leader_id).set(1)

                if is_current_leader and tenant in self._leader_states:
                    state = self._leader_states[tenant]
                    tenure = time.time() - state.start_time
                    LEADER_TENURE.labels(tenant=tenant).set(tenure)

                return is_current_leader

            return False

        except Exception:
            LEADER_HEALTH_CHECK.labels(tenant=tenant, check_type="redis_error").set(0)
            return False

    def acquire_leadership(self, tenant: str) -> bool:
        """Attempt to acquire leadership for a tenant."""
        start_time = time.time()

        try:
            config = self.get_config(tenant)
            lock_key = self._get_lock_key(tenant)

            # Try to acquire lock using SET with NX and PX
            result = self._redis_client.set(
                lock_key, self._instance_id, nx=True, px=config.lock_ttl_seconds * 1000
            )

            success = bool(result)

            if success:
                # Record new leadership
                self._leader_states[tenant] = LeaderState(
                    instance_id=self._instance_id,
                    start_time=time.time(),
                    last_heartbeat=time.time(),
                    min_dwell_ms=config.min_dwell_ms,
                    entropy_cap=config.entropy_cap,
                )

                # Update metrics
                LEADER_ELECTION_TOTAL.labels(tenant=tenant, outcome="success").inc()
                LEADER_CURRENT.labels(tenant=tenant, instance_id=self._instance_id).set(
                    1
                )
                LEADER_TENURE.labels(tenant=tenant).set(0)

            else:
                LEADER_ELECTION_TOTAL.labels(tenant=tenant, outcome="failed").inc()

            # Record latency
            latency = time.time() - start_time
            LEADER_ELECTION_LATENCY.observe(latency)

            return success

        except Exception:
            LEADER_ELECTION_TOTAL.labels(tenant=tenant, outcome="error").inc()
            return False

    def renew_leadership(self, tenant: str) -> bool:
        """Renew leadership lock for a tenant."""
        try:
            if not self.is_leader(tenant):
                return False

            config = self.get_config(tenant)
            lock_key = self._get_lock_key(tenant)

            # Use Lua script for atomic renewal
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("pexpire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """

            result = self._redis_client.eval(
                lua_script,
                1,
                lock_key,
                self._instance_id,
                str(config.lock_ttl_seconds * 1000),
            )

            success = bool(result)

            if success and tenant in self._leader_states:
                self._leader_states[tenant].last_heartbeat = time.time()
                LEADER_HEALTH_CHECK.labels(tenant=tenant, check_type="heartbeat").set(1)

            return success

        except Exception:
            LEADER_HEALTH_CHECK.labels(tenant=tenant, check_type="heartbeat").set(0)
            return False

    def release_leadership(self, tenant: str) -> bool:
        """Release leadership for a tenant."""
        try:
            lock_key = self._get_lock_key(tenant)

            # Use Lua script for atomic release
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """

            result = self._redis_client.eval(lua_script, 1, lock_key, self._instance_id)

            success = bool(result)

            if success:
                if tenant in self._leader_states:
                    del self._leader_states[tenant]
                LEADER_CURRENT.labels(tenant=tenant, instance_id=self._instance_id).set(
                    0
                )
                LEADER_TENURE.labels(tenant=tenant).set(0)

            return success

        except Exception:
            return False

    def get_leader_info(self, tenant: str) -> Optional[Tuple[str, float]]:
        """Get current leader info for a tenant."""
        try:
            lock_key = self._get_lock_key(tenant)
            lock_value = self._redis_client.get(lock_key)

            if lock_value:
                leader_id = lock_value.decode("utf-8")
                ttl = self._redis_client.ttl(lock_key)
                return leader_id, ttl

            return None

        except Exception:
            return None

    def can_transition_leader(self, tenant: str, current_entropy: float) -> bool:
        """Check if leader transition is allowed based on dwell and entropy constraints."""
        config = self.get_config(tenant)

        # Check entropy cap
        if current_entropy > config.entropy_cap:
            return True

        # Check minimum dwell time
        if tenant in self._leader_states:
            state = self._leader_states[tenant]
            tenure = time.time() - state.start_time
            if tenure * 1000 < state.min_dwell_ms:
                return False

        return True

    def start_heartbeat(self) -> None:
        """Start background heartbeat thread for leader renewal."""
        if self._running:
            return

        self._running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True, name="integrator-leader-heartbeat"
        )
        self._heartbeat_thread.start()

    def stop_heartbeat(self) -> None:
        """Stop background heartbeat thread."""
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)

    def _heartbeat_loop(self) -> None:
        """Background thread for renewing leadership locks."""
        while self._running:
            for tenant in list(self._leader_states.keys()):
                if self._running:
                    self.renew_leadership(tenant)

            # Wait for next heartbeat interval
            heartbeat_interval = (
                min(
                    config.heartbeat_interval_seconds
                    for config in self._configs.values()
                )
                if self._configs
                else 10
            )

            time.sleep(heartbeat_interval)

    def shutdown(self) -> None:
        """Graceful shutdown - release all leadership locks."""
        self.stop_heartbeat()

        # Release all held leaderships
        for tenant in list(self._leader_states.keys()):
            self.release_leadership(tenant)


def main() -> None:  # pragma: no cover
    """Test entry point for leader election service."""

    if not feature_enabled("integrator"):
        print("integrator_leader: disabled via mode")
        return

    # Ensure Redis is ready
    assert_ready(require_redis=True)

    election_service = IntegratorLeaderElection()

    try:
        # Test leadership acquisition
        test_tenant = "test-tenant"

        if election_service.acquire_leadership(test_tenant):
            print(f"Acquired leadership for {test_tenant}")
            print(f"Instance: {election_service._instance_id}")

            # Start heartbeat
            election_service.start_heartbeat()

            # Simulate work
            time.sleep(5)

            # Check if still leader
            if election_service.is_leader(test_tenant):
                print("Still leader after 5s")
            else:
                print("Lost leadership")

        else:
            leader_info = election_service.get_leader_info(test_tenant)
            if leader_info:
                leader_id, ttl = leader_info
                print(f"Current leader: {leader_id} (TTL: {ttl}s)")
            else:
                print("No current leader")

    finally:
        election_service.shutdown()


if __name__ == "__main__":  # pragma: no cover
    main()
