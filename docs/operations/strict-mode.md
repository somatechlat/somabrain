# Strict Mode Posture (Avro-only, Fail-fast)

- Avro-only: All Kafka topics must serialize with Avro; JSON fallbacks removed.
- Fail-fast producers: When a feature is enabled, Kafka producer initialization must succeed, otherwise the service raises at startup.
- Invariants: CI scans enforce no legacy kafka-python, no JSON fallback code paths, and no soft-disable environment gates.
- Persistence scope: Calibration persists temperatures + sample counts; drift persists only telemetry (events). Statefulness beyond that must be explicit.
- Observability: Metrics for entropy, regret, alpha, tau, ECE/Brier, improvement ratio; OTel tracing aligned and enabled.
- Policy: OPA fail-closed; frames may be dropped on explicit policy denial.
