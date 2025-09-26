"""
Demonstration of SomaBrain's autonomous operations capabilities.
"""

import logging
import time

from somabrain.autonomous import AutonomousConfig, initialize_autonomous_operations


def setup_logging():
    """Set up logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def create_demo_config():
    """Create a demo configuration for autonomous operations."""
    config = AutonomousConfig()
    config.enabled = True
    config.monitoring.health_check_interval = 10  # Check every 10 seconds
    config.monitoring.alert_threshold_cpu = 80.0
    config.monitoring.alert_threshold_memory = 85.0
    config.safety.audit_logging_enabled = True
    config.learning.continuous_learning_enabled = True
    return config


def simulate_system_load():
    """Simulate system load to demonstrate monitoring."""
    import psutil

    # Simulate some CPU load
    print("Simulating system activity...")
    for i in range(10):
        # Do some work to generate CPU load
        start = time.time()
        while time.time() - start < 0.1:
            pass
        time.sleep(0.1)

        # Report metrics occasionally
        if i % 3 == 0:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            print(
                f"System metrics - CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%"
            )


def main():
    """Main demo function."""
    setup_logging()
    print("SomaBrain Autonomous Operations Demo")
    print("=" * 40)

    # Create demo configuration
    config = create_demo_config()
    print(f"Autonomous operations enabled: {config.enabled}")
    print(f"Health check interval: {config.monitoring.health_check_interval} seconds")

    # Initialize autonomous operations
    coordinator = initialize_autonomous_operations()
    coordinator.update_config(config)

    # Start autonomous operations
    print("\nStarting autonomous operations...")
    coordinator.start()

    try:
        # Run for a while to demonstrate autonomous operations
        print("\nRunning autonomous monitoring for 30 seconds...")
        print("Check the logs for autonomous operations activity.")

        for i in range(30):
            # Every 10 seconds, simulate some system activity
            if i % 10 == 0:
                simulate_system_load()

            # Every 5 seconds, check status
            if i % 5 == 0:
                status = coordinator.get_status()
                print(f"\nStatus update ({i}s):")
                print(f"  Monitoring: {status.monitoring_active}")
                print(f"  Learning: {status.learning_active}")
                print(f"  Healing: {status.healing_active}")
                print(f"  Metrics collected: {len(status.metrics)}")

            time.sleep(1)

        # Show final status
        print("\nFinal autonomous operations status:")
        status = coordinator.get_status()
        for key, value in status.metrics.items():
            print(f"  {key}: {value}")

    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    finally:
        # Stop autonomous operations
        print("\nStopping autonomous operations...")
        coordinator.stop()
        print("Demo completed successfully!")


if __name__ == "__main__":
    main()
