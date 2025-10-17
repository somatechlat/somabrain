# SomaBrain Learning Loop (Draft)

This document captures the initial production learning loop that converts live
memory payloads into supervised fine-tuning corpora. The design takes cues from
nanogpt/nanochat by emphasizing small, deterministic pipelines that users can
inspect and run end-to-end.

## Objectives

- **Truthful datasets:** Only derive prompts/responses from real tenant data.
- **Deterministic signals:** Feature flags guard the pipeline, default OFF.
- **Composability:** Export artefacts suitable for nanochat-style training loops
  (JSONL with `prompt`/`response`).
- **Observability:** Metrics capture export counts, ANN backend choice, and
  supervisor adjustments so the loop is auditable.

## Components (Code References)

| Component | Description | Location |
| --- | --- | --- |
| Dataset builder | Extract `TrainingExample` objects from memory records. | `somabrain/learning/dataset.py` |
| Export script | CLI to read JSONL memory dumps and write training corpora. | `scripts/export_learning_corpus.py` |
| Governance signals | Tiered recall metadata (`governed_margin`, `cleanup_backend`). | `somabrain/api/memory_api.py` |
| ANN rebuild job | `/memory/admin/rebuild-ann` endpoint keeps cleanup indices aligned. | `somabrain/api/memory_api.py` |
| Kong gating | Request validators + audit logging for `/memory/*` routes. | `infra/gateway/memory-gateway.yaml` |
| Telemetry | Supervisor metrics + ANN rebuild counters. | `somabrain/runtime/config_runtime.py`, `somabrain/metrics.py` |

## Workflow

1. Enable the learning loop feature flag (planned): `cfg.learning_loop_enabled`.
2. Export memory records to JSONL (via API dump or journal migration).
3. Run `scripts/export_learning_corpus.py input.jsonl output.jsonl`.
4. Feed `output.jsonl` into nanochat/nanoGPT fine-tuning scripts.
5. Record uplift in `scripts/prove_enhancement.py` and push back via config API.

Future iterations will add tokenizer alignment and direct streaming into the
training pipeline. For now, this PoC establishes the dataset contract and the
operational hooks required for a trustworthy learning loop.
