## Prune and Update Candidates (Truth Audit)

This list tracks documentation items that were corrected in this pass or should be removed/updated to match the running code.

Addressed now
- API runbook endpoint corrected: `POST /plan` → `POST /plan/suggest` (FastAPI route and schemas).
- Deployment guide health example updated to use `HealthResponse` fields (`ok`, `components`, `ready`, `memory_ok`, `embedder_ok`).
- Kubernetes file paths fixed from `k8s/...` to `infra/k8s/...` in the deployment guide and quick commands.
- Operator navigation now links to Environment Variables and Services & Ports matrices.
- Quick Start clarifies API host port differences between `dev_up.sh` (dynamic, default attempt 9696) and `dev_up_9999.sh` (fixed 9999).

To verify or follow up
- Search docs for legacy health fields like `status: healthy` and update to `ok: true` where applicable.
- Normalize API port references in examples: prefer 9999 for the 9999 stack, or add a note to check `.env`/`ports.json` for dynamic runs.
- Ensure any client examples use current request schemas:
  - `/recall` expects `top_k` (not `k`).
  - `/remember` uses `{ "payload": { ... } }` as canonical; legacy shapes should be explicitly called out.
- Confirm all references to Kafka exporter images reflect current setup; Compose uses a Docker Hub OSS image `danielqsj/kafka-exporter` by default.

How to proceed
- Run a grep to catch remaining mismatches:
  - Endpoints: `grep -R "\b/plan\b" docs/`
  - Health: `grep -R "\bstatus\b" docs/technical-manual | grep -i health`
  - Ports: `grep -R "localhost:9999\|localhost:9696" docs/`
- Update any lingering examples in-place, keeping them aligned with `somabrain/schemas.py` and `somabrain/app.py`.
