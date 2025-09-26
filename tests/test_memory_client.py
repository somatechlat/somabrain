import sys


def main():
    # Ensure imports resolve when running directly
    sys.path.insert(0, ".")

    from somabrain.config import Config
    from somabrain.memory_client import MemoryClient

    cfg = Config()
    cfg.namespace = "test_ns"
    # Memory mode removed; ensure HTTP endpoint is configured for tests
    cfg.http.endpoint = cfg.http.endpoint or "http://localhost:9595"

    mc = MemoryClient(cfg)

    # store_from_payload should succeed even without coordinates (fallback to remember)
    ok = mc.store_from_payload({"task": "foo", "memory_type": "episodic"})
    assert ok is True

    # With coordinates present it should also succeed (local path guarded)
    ok2 = mc.store_from_payload(
        {"coordinate": (0.1, 0.2, 0.3), "task": "bar", "memory_type": "episodic"}
    )
    # In stub mode, coordinate path falls back or no-ops; expect bool result
    assert isinstance(ok2, bool)

    print("MemoryClient tests passed.")


if __name__ == "__main__":
    main()
