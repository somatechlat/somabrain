# Real-Time Propagation Feature

**Purpose**: Document how SomaBrain propagates cognitive state changes in real-time via Kafka.

**Audience**: Users building event-driven applications on top of SomaBrain.

---

## Overview

SomaBrain uses Kafka topics to propagate cognitive events in real-time:

- **Outbox Events** → Memory operations, admin actions
- **Cognitive Threads** → Predictor beliefs, integrator frames, segmentation boundaries
- **Teach Feedback** → User ratings converted to reward signals
- **Config Updates** → Dynamic parameter adjustments

---

## Kafka Topics

| Topic | Schema | Purpose | Producer | Consumer |
|-------|--------|---------|----------|----------|
| `soma.audit` | JSON | Audit trail for memory operations | SomaBrain API | Audit service |
| `cog.global.frame` | Avro | Integrated belief state | IntegratorHub | Downstream agents |
| `cog.segments` | Avro | Episodic boundaries | SegmentationService | Memory consolidation |
| `cog.reward.events` | Avro | Reward signals | RewardProducer | LearnerOnline |
| `cog.config.updates` | Avro | Parameter updates | LearnerOnline | All cognitive services |
| `cog.teach.feedback` | Avro | User feedback | External systems | TeachFeedbackProcessor |

---

## Outbox Pattern

**Purpose**: Ensure transactional consistency between Postgres writes and Kafka publishes.

**Flow**:
1. API writes memory operation to Postgres outbox table
2. Outbox worker polls for pending events
3. Worker publishes to Kafka with at-least-once semantics
4. Worker marks event as `sent` in outbox table

**Configuration**:
```bash
SOMABRAIN_OUTBOX_BATCH_SIZE=100
SOMABRAIN_OUTBOX_MAX_DELAY=5.0
```

**Monitoring**:
```bash
# Check outbox backlog
curl http://localhost:9696/admin/outbox?status=pending | jq '.events | length'

# Replay failed events
curl -X POST http://localhost:9696/admin/outbox/replay \
  -H "Content-Type: application/json" \
  -d '{"ids": [123, 456]}'
```

---

## Cognitive Thread Events

### Global Frame

**Schema**: `proto/cog/global_frame.avsc`

**Fields**:
- `frame_id` - Unique identifier
- `timestamp` - Event time
- `leader` - Winning predictor domain
- `weights` - Domain confidence weights
- `rationale` - Explanation text

**Example**:
```json
{
  "frame_id": "frame-20250127-001",
  "timestamp": 1706313600000,
  "leader": "state",
  "weights": {
    "state": 0.7,
    "agent": 0.2,
    "action": 0.1
  },
  "rationale": "State predictor has highest confidence"
}
```

### Segment Boundaries

**Schema**: `proto/cog/segment_boundary.avsc`

**Fields**:
- `segment_id` - Unique identifier
- `start_frame_id` - First frame in segment
- `end_frame_id` - Last frame in segment
- `boundary_type` - `cpd` (change point detection) or `hazard`

**Example**:
```json
{
  "segment_id": "seg-20250127-001",
  "start_frame_id": "frame-20250127-001",
  "end_frame_id": "frame-20250127-050",
  "boundary_type": "cpd"
}
```

### Reward Events

**Schema**: `proto/cog/reward_event.avsc`

**Fields**:
- `frame_id` - Associated frame
- `r_task` - Task completion reward
- `r_user` - User satisfaction reward
- `r_latency` - Latency penalty
- `r_safety` - Safety compliance reward
- `r_cost` - Cost efficiency reward
- `total` - Weighted sum

**Example**:
```json
{
  "frame_id": "frame-20250127-001",
  "r_task": 0.8,
  "r_user": 0.9,
  "r_latency": -0.1,
  "r_safety": 1.0,
  "r_cost": 0.7,
  "total": 0.86
}
```

---

## Teach Feedback Integration

**Purpose**: Convert user ratings into reward signals for online learning.

**Flow**:
1. External system posts to `/teach/feedback` (or publishes to `cog.teach.feedback`)
2. TeachFeedbackProcessor consumes feedback events
3. Processor maps `rating` to `r_user` component
4. Processor publishes `RewardEvent` to `cog.reward.events`
5. LearnerOnline consumes rewards and emits config updates

**Mapping**:
```python
rating_map = {
    5: 1.0,   # Excellent
    4: 0.5,   # Good
    3: 0.0,   # Neutral
    2: -0.5,  # Poor
    1: -1.0   # Terrible
}
r_user = rating_map.get(rating, 0.0)
```

**Example**:
```bash
# Submit teach feedback
curl -X POST http://localhost:9696/teach/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_id": "fb-001",
    "frame_id": "frame-20250127-001",
    "rating": 5,
    "comment": "Perfect response"
  }'
```

---

## Config Updates

**Purpose**: Dynamically adjust cognitive parameters based on reward signals.

**Schema**: `proto/cog/config_update.avsc`

**Fields**:
- `config_id` - Unique identifier
- `timestamp` - Update time
- `learning_rate` - Adjusted learning rate
- `exploration_temp` - Temperature for exploration

**Example**:
```json
{
  "config_id": "cfg-20250127-001",
  "timestamp": 1706313600000,
  "learning_rate": 0.01,
  "exploration_temp": 0.5
}
```

---

## Consuming Events

### Python (confluent-kafka)

```python
from confluent_kafka import Consumer

consumer = Consumer({
    'bootstrap.servers': 'localhost:30102',
    'group.id': 'my-consumer-group',
    'auto.offset.reset': 'earliest'
})

consumer.subscribe(['cog.global.frame'])

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        print(f"Error: {msg.error()}")
        continue
    
    frame = json.loads(msg.value().decode('utf-8'))
    print(f"Received frame: {frame['frame_id']}")
```

### Python (kafka-python)

```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'cog.global.frame',
    bootstrap_servers=['localhost:30102'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    frame = message.value
    print(f"Received frame: {frame['frame_id']}")
```

---

## Monitoring

**Metrics**:
- `somabrain_outbox_events_created_total` - Outbox events created
- `somabrain_outbox_failed_total` - Failed Kafka publishes
- `somabrain_teach_feedback_total` - Teach feedback received
- `somabrain_reward_events_published_total` - Reward events published

**Health Check**:
```bash
# Check Kafka connectivity
curl http://localhost:9696/health | jq '.kafka_ok'

# Check outbox backlog
curl http://localhost:9696/admin/outbox?status=pending
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Events not appearing in Kafka | Outbox worker not running | Check `somabrain_outbox_publisher` container logs |
| High outbox backlog | Kafka unavailable | Verify Kafka broker health, check network connectivity |
| Duplicate events | At-least-once semantics | Implement idempotency in consumers using `dedupe_key` |
| Missing teach feedback | Wrong topic name | Verify `cog.teach.feedback` topic exists and is spelled correctly |

---

## Related Documentation

- [Karpathy Architecture](../../technical/karpathy-architecture.md) - Cognitive threads design
- [Kafka Operations](../../technical/runbooks/kafka-operations.md) - Operational procedures
- [Outbox Backlog Playbook](../../operational/playbooks/outbox-backlog.md) - Incident response
