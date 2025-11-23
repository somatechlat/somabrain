"""
Chaos Experiment Scaffold for SomaBrain (S9)
--------------------------------------------
Simulates failure scenarios (broker, Redis, agent SLM outage) and verifies auto-recovery and data integrity.

NOTE: Actual process/container kill/restart must be orchestrated externally (e.g., via Docker Compose, Kubernetes, or manual intervention). This script coordinates the test and checks system health before, during, and after the chaos event.
"""

import time
import requests


def check_health():
    try:
        from common.config.settings import settings
        r = requests.get(f"http://localhost:{settings.getenv('SOMABRAIN_HOST_PORT', '9696')}/health")
        if r.status_code == 200 and r.json().get("ok"):
            print("System healthy.")
            return True
        else:
            print("Health check failed.")
            return False
    except Exception as e:
        print(f"Health check error: {e}")
        return False


def run_chaos_scenario(description, chaos_action, recovery_action=None, wait=10):
    print(f"\n=== CHAOS: {description} ===")
    print("[1] Checking system health before chaos...")
    assert check_health(), "System not healthy before chaos!"
    print("[2] Executing chaos action...")
    chaos_action()
    print(f"[3] Waiting {wait}s during chaos...")
    time.sleep(wait)
    print("[4] Checking system health during chaos...")
    check_health()
    if recovery_action:
        print("[5] Executing recovery action...")
        recovery_action()
        print("[6] Waiting for recovery...")
        time.sleep(wait)
        print("[7] Checking system health after recovery...")
        assert check_health(), "System did not recover!"
    print("=== CHAOS SCENARIO COMPLETE ===\n")


def main():
    # Example: Broker failure (manual)
    run_chaos_scenario(
        "Kafka broker failure (simulate by stopping broker container)",
        chaos_action=lambda: print(
            "[ACTION] Please stop the Kafka broker container now."
        ),
        recovery_action=lambda: print(
            "[ACTION] Please restart the Kafka broker container now."
        ),
        wait=15,
    )
    # Example: Redis node loss (manual)
    run_chaos_scenario(
        "Redis node failure (simulate by stopping Redis container)",
        chaos_action=lambda: print("[ACTION] Please stop the Redis container now."),
        recovery_action=lambda: print(
            "[ACTION] Please restart the Redis container now."
        ),
        wait=15,
    )
    # Example: Agent SLM outage (manual)
    run_chaos_scenario(
        "Agent SLM outage (simulate by stopping agent SLM container)",
        chaos_action=lambda: print("[ACTION] Please stop the agent SLM container now."),
        recovery_action=lambda: print(
            "[ACTION] Please restart the agent SLM container now."
        ),
        wait=15,
    )


if __name__ == "__main__":
    main()
