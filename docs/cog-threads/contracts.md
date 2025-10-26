## Avro Contracts and Topics

Schemas reside under `proto/cog/` and are exercised by `tests/kafka/test_avro_contracts.py`.

- BeliefUpdate: `proto/cog/belief_update.avsc`
- GlobalFrame: `proto/cog/global_frame.avsc`
- SegmentBoundary: `proto/cog/segment_boundary.avsc`

Kafka topics (Strimzi manifests under `infra/kafka/topics/`):
- `cog.state.updates` – 3-day retention
- `cog.agent.updates` – 3-day retention
- `cog.action.updates` – 3-day retention
- `cog.global.frame` – 30-day retention
- `cog.segments` – 30-day retention

Local compose relies on Kafka auto-create; manifests are for clusters with Strimzi.
