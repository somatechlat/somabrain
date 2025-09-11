Architecture
============

This page describes the high-level architecture of SomaBrain.

- FastAPI HTTP gateway exposing the memory API and metrics.
- HRR-based numeric core for high-dimensional vector storage and unbinding.
- Pluggable memory backends (local, stub, remote HTTP, or database-backed).
- Observable telemetry via Prometheus metrics and structured logs.

See `NUMERICS_MATH_SPEC.md` and `COGNITION_MATH_WHITEPAPER.md` for design details.
