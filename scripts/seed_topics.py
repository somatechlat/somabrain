from __future__ import annotations

from common.config.settings import settings
from typing import List

from kafka import KafkaAdminClient
from kafka.admin import NewTopic


def _bootstrap() -> str:
    url = settings.kafka_bootstrap_servers
    if not url:
        raise ValueError("SOMABRAIN_KAFKA_URL not set; refusing to fall back to localhost")
    # strip optional scheme if present (Settings may already contain scheme‑less value)
    return str(url).replace("kafka://", "")


def _topics() -> List[NewTopic]:
    # Retention: updates 3d, frames/segments 30d
    return [
        NewTopic(
            name="cog.state.updates",
            num_partitions=3,
            replication_factor=1,
            topic_configs={"retention.ms": str(3 * 24 * 60 * 60 * 1000)},
        ),
        NewTopic(
            name="cog.agent.updates",
            num_partitions=3,
            replication_factor=1,
            topic_configs={"retention.ms": str(3 * 24 * 60 * 60 * 1000)},
        ),
        NewTopic(
            name="cog.action.updates",
            num_partitions=3,
            replication_factor=1,
            topic_configs={"retention.ms": str(3 * 24 * 60 * 60 * 1000)},
        ),
        NewTopic(
            name="cog.global.frame",
            num_partitions=3,
            replication_factor=1,
            topic_configs={"retention.ms": str(30 * 24 * 60 * 60 * 1000)},
        ),
        NewTopic(
            name="cog.segments",
            num_partitions=3,
            replication_factor=1,
            topic_configs={"retention.ms": str(30 * 24 * 60 * 60 * 1000)},
        ),
        NewTopic(
            name="cog.reward.events",
            num_partitions=3,
            replication_factor=1,
            topic_configs={"retention.ms": str(30 * 24 * 60 * 60 * 1000)},
        ),
        NewTopic(
            name="cog.next.events",
            num_partitions=3,
            replication_factor=1,
            topic_configs={"retention.ms": str(30 * 24 * 60 * 60 * 1000)},
        ),
        NewTopic(
            name="cog.config.updates",
            num_partitions=3,
            replication_factor=1,
            topic_configs={"retention.ms": str(3 * 24 * 60 * 60 * 1000)},
        ),
        NewTopic(
            name="cog.teach.feedback",
            num_partitions=3,
            replication_factor=1,
            topic_configs={"retention.ms": str(30 * 24 * 60 * 60 * 1000)},
        ),
        NewTopic(
            name="cog.integrator.context.shadow",
            num_partitions=3,
            replication_factor=1,
            topic_configs={"retention.ms": str(7 * 24 * 60 * 60 * 1000)},
        ),
    ]


def main() -> None:
    admin = KafkaAdminClient(bootstrap_servers=_bootstrap(), client_id="seed-topics")
    topics = _topics()
    try:
        admin.create_topics(new_topics=topics, validate_only=False)
        print("Topics created (or already existed).")
    except Exception as e:
        print(f"Topic creation encountered an issue: {e}")
    finally:
        try:
            admin.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
