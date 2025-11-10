from __future__ import annotations

import re
from somabrain.common.kafka import TOPICS


def test_kafka_topics_use_dot_only_delimiter():
    bad = [name for name in TOPICS.values() if "_" in name]
    assert (
        not bad
    ), f"Underscore-delimited topics found (policy requires only dots): {bad}"


def test_kafka_topics_match_pattern():
    pat = re.compile(r"^[a-z0-9]+(\.[a-z0-9]+)+$")
    bad = [t for t in TOPICS.values() if not pat.match(t)]
    assert not bad, f"Topics failing naming regex: {bad}"
