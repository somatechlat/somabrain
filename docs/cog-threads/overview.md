## Cog Threads: State · Agent · Action

This document describes the tripartite cognitive-thread architecture and how it’s wired in this repo:

- Producers (predictor-state/agent/action) emit BeliefUpdate events to Kafka
- Integrator Hub consumes updates, selects a leader, and publishes GlobalFrame
- Segmentation Service emits SegmentBoundary events based on dwell or leader change
- Orchestrator composes episodic snapshots on boundaries and enqueues to the outbox
- Outbox Applier persists episodic snapshots to Postgres

Feature flags gate each service so the baseline path can be restored instantly.

Key topics:
- cog.state.updates, cog.agent.updates, cog.action.updates (inputs)
- cog.global.frame (integrator output)
- cog.segments (segmentation output)

Services:
- `somabrain/services/integrator_hub.py`
- `somabrain/services/segmentation_service.py`
- `somabrain/services/orchestrator_service.py`
- `somabrain/workers/outbox_publisher.py` and `somabrain/workers/outbox_db_applier.py`

See also: contracts.md, policies.md, runbook.md
