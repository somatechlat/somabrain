from __future__ import annotations

import os
from typing import List

from kafka import KafkaAdminClient
from kafka.admin import NewTopic


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "localhost:30001"
    # strip optional scheme
    return url.replace("kafka://", "")


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
