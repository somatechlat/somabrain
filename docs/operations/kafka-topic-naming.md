## Kafka Topic Naming Policy

### Collision Warning Context
Some Kafka metrics exporters (and JMX→Prometheus transformers) sanitize topic names by replacing dots (`.`) with underscores (`_`). When a cluster contains mixed naming styles (both `cog.state.updates` and `cog_state_updates`), the sanitized metric names can collide, producing warnings like:

```
WARNING: Due to limitations in metric names, topics with a period ('.') or underscore ('_') could collide. To avoid issues it is best to use either, but not both.
```

### Policy (Enforced)
SomaBrain uses dot-delimited topic names exclusively. Underscores are not used in any Kafka topic identifiers. This ensures one unambiguous sanitized form for metrics.

Allowed pattern (examples):
- `cog.state.updates`
- `cog.global.frame`
- `cog.integrator.context.shadow`
- `soma.belief.state`

Disallowed examples (do not create):
- `cog_state_updates`
- `cog-global-frame`
- `cog_integrator_context_shadow`

### Rationale
1. Avoid exporter collisions when `.` → `_` sanitation occurs.
2. Provide hierarchical semantic grouping (prefix segments) improving operational filtering.
3. Maintain compatibility with existing documentation and automation (scripts/seed_topics.py).

### Verification
Add or maintain a test that asserts no required topic contains `_`.

### Migration Guidance (If Existing Underscore Topics Found)
1. Create new dot-form topic (e.g., `cog.state.updates`).
2. Dual-produce events to old + new for a short transition window.
3. Migrate consumers to the new topic.
4. Validate lag = 0 on old topic, then delete old topic.

### Operational Checklist
- [ ] Run `scripts/seed_topics.py` only (creates dot-form topics).
- [ ] Audit with `kafka-topics.sh --list` (no `_` present).
- [ ] Monitor exporter logs for absence of collision warnings.

### Future Enforcement
CI task can parse `scripts/seed_topics.py` and `somabrain/common/kafka.py` TOPICS mapping ensuring all names match regex: `^[a-z0-9]+(\.[a-z0-9]+)+$`.
