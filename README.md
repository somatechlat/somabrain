SomaBrain — Brain‑Inspired Memory & Planning for Agents

[![CI](https://github.com/somatechlat/somaBrain/actions/workflows/ci.yml/badge.svg)](https://github.com/somatechlat/somaBrain/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://somatechlat.github.io/somaBrain/)
[![Tag](https://img.shields.io/github/v/tag/somatechlat/somaBrain?sort=semver)](https://github.com/somatechlat/somaBrain/tags)
[![Container](https://img.shields.io/badge/container-ghcr.io%2Fsomatechlat%2FsomaBrain-0A66C2?logo=docker)](https://github.com/somatechlat/somaBrain/pkgs/container/somaBrain)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Elegant, verifiable mathematics meets practical engineering. SomaBrain gives agents a stable, observable memory and planning layer powered by HRR numerics (unitary roles, exact and Wiener unbinding), typed graph links, multi‑tenant semantics, and a clean FastAPI surface.

Human × AI collaboration, by design. Declarative HTTP contracts and tiny SDKs make it easy for humans to guide the system, while Prometheus metrics make behavior visible and tunable. Small, composable “brain modules” (thalamus, amygdala, hippocampus, prefrontal) provide understandable control loops instead of opaque magic.

Why SomaBrain stands out
- Single memory gateway (ADR‑0002) to SomaFractalMemory (modes: stub | local | http)
- Hardened math: sqrt(D) tiny‑floor, deterministic unitary roles, float64 divisions, Wiener/MAP for superpositions
- Observable by default: Prometheus metrics for HTTP, recall stages, HRR paths, microcircuits, predictors, consolidation

Docs & Tutorials
- Quickstart API: `docs/source/api_quickstart.md` • Full API: `docs/source/api.md`
- Configure & deploy: `docs/ops/configuration.md`, `docs/OPERATION.md`
```markdown
# SomaBrain — Observable Memory & Planning for AI Agents

[![CI](https://github.com/somatechlat/somabrain/actions/workflows/ci.yml/badge.svg)](https://github.com/somatechlat/somabrain/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://somatechlat.github.io/somabrain/)
[![Tag](https://img.shields.io/github/v/tag/somatechlat/somabrain?sort=semver)](https://github.com/somatechlat/somabrain/tags)
[![Container](https://img.shields.io/badge/container-ghcr.io%2Fsomatechlat%2Fsomabrain-0A66C2?logo=docker)](https://github.com/somatechlat/somabrain/pkgs/container/somabrain)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Make agents *remember, connect, and explain* their work. SomaBrain gives you:
- **Stable, inspectable memory** (HRR-based numerics; exact & Wiener unbinding)
- **Typed links/graphs** between notes, tasks, entities
- **Multi-tenant isolation**
- **FastAPI** HTTP gateway with **OpenAPI docs** and **Prometheus** metrics

> You can see what was saved, how it was found, and why it’s suggested.

---

## 🚀 TL;DR — Run in ~10 seconds (Docker)

**Option A — Pull prebuilt image (if available):**
```bash
docker run --rm -p 8000:8000 ghcr.io/somatechlat/somabrain:latest
```

**Option B — Build locally (works anywhere Docker runs):**
```bash
git clone https://github.com/somatechlat/somabrain.git
cd somabrain
docker build -t somabrain:local .
docker run --rm -p 8000:8000 somabrain:local
```

Now open:
- API docs (Swagger): **http://localhost:8000/docs**
- Prometheus metrics: **http://localhost:8000/metrics**

---

## 🔎 60-second Smoke Test

**1) Store a memory (multi-tenant via header):**
```bash
curl -s -X POST http://localhost:8000/remember   -H 'Content-Type: application/json'   -H 'X-Tenant-ID: demo'   -d '{"text":"Pay ACME invoice on Friday","tags":["todo","ops"]}'
```

**2) Recall it by cue:**
```bash
curl -s -X POST http://localhost:8000/recall   -H 'Content-Type: application/json'   -H 'X-Tenant-ID: demo'   -d '{"query":"invoice ACME"}'
```

**3) (Optional) Link facts:**  
Connect items with a typed relation (example shape):
```bash
curl -s -X POST http://localhost:8000/link   -H 'Content-Type: application/json'   -H 'X-Tenant-ID: demo'   -d '{
        "source_id":"note:acme-invoice",
        "target_id":"entity:acme",
        "type":"about"
      }'
```

> Don’t want curl? Open **/docs** and try the endpoints interactively.

---

## 🧠 What makes SomaBrain different

- **HRR numerics done right**: unitary role vectors, deterministic seeding, float64 ops, exact & Wiener unbinding for robust recall.
- **Typed graph links**: turn scattered notes into a navigable knowledge mesh.
- **Observable by default**: Prometheus metrics to watch recall stages and latency.
- **Multi-tenant**: isolate projects or users via headers and (optional) auth.

---

## 🧩 API Overview

```
POST /remember     # Store text/facts/tasks with optional tags/metadata
POST /recall       # Retrieve by keyword/semantic cue; ranked results
POST /link         # Create typed relations between stored items
GET  /metrics      # Prometheus exposition format
GET  /docs         # OpenAPI/Swagger UI
```

Minimal request shapes (subject to evolution):
```json
// /remember
{
  "text": "Research HRR unitary roles",
  "tags": ["research","hrr"],
  "metadata": {"source":"paper-notes"}
}

// /recall
{
  "query": "unitary roles hrr",
  "k": 10
}

// /link
{
  "source_id": "note:123",
  "target_id": "entity:hrr",
  "type": "about"
}
```

---

## 👩‍💻 Quick Client Examples

**Python**
```python
import requests

BASE = "http://localhost:8000"
HEAD = {"X-Tenant-ID": "demo"}

requests.post(f"{BASE}/remember", json={"text":"Buy graphite for lab"}, headers=HEAD)
r = requests.post(f"{BASE}/recall", json={"query":"graphite lab"}, headers=HEAD)
print(r.json())
```

**JavaScript**
```js
const BASE = "http://localhost:8000";
const HEAD = {"X-Tenant-ID": "demo","Content-Type":"application/json"};

await fetch(`${BASE}/remember`, {
  method: "POST",
  headers: HEAD,
  body: JSON.stringify({ text: "Link ACME invoice to vendor ACME", tags:["acct"] })
});

const res = await fetch(`${BASE}/recall`, {
  method: "POST",
  headers: HEAD,
  body: JSON.stringify({ query: "invoice ACME" })
});
console.log(await res.json());
```

---

## 📦 Docker Compose (optional Prometheus + Grafana)

Create `docker-compose.yml`:
```yaml
services:
  somabrain:
    image: ghcr.io/somatechlat/somabrain:latest
    ports: ["8000:8000"]

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
```

Create `prometheus.yml`:
```yaml
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: "somabrain"
    static_configs:
      - targets: ["somabrain:8000"]
    metrics_path: /metrics
```

Run:
```bash
docker compose up -d
```
Open Grafana at `http://localhost:3000` and add Prometheus at `http://prometheus:9090`.

---

## ⚙️ Configuration (common)

Environment variables (all optional; sensible defaults):
- `PORT` — HTTP port (default `8000`)
- `LOG_LEVEL` — `info` | `debug` | `warning`
- `SOMABRAIN_MODE` — memory backend mode: `stub` | `local` | `http`
- `DISABLE_AUTH` — `true` for local demos (enable auth for prod)
- `TENANT_HEADER` — name for tenant header (default `X-Tenant-ID`)

Example:
```bash
docker run --rm -p 8000:8000   -e LOG_LEVEL=info -e SOMABRAIN_MODE=local   ghcr.io/somatechlat/somabrain:latest
```

---

## ✅ Production Checklist

- Use a **persistent volume** for any on-disk state
- Put SomaBrain **behind TLS** (reverse proxy) and **enable auth**
- Set a fixed `TENANT_HEADER` & integrate with your identity provider
- **Scrape /metrics** and alert on latency/error spikes
- Constrain resources with container **limits/requests**
- Run **load tests** before going live

---

## 🗺️ Roadmap (high level)

- Structured schemas for entities & relations
- More recall strategies (rerankers, hybrids)
- Built-in dashboards for memory transparency
- Language-agnostic client SDKs

---

## 🤝 Contributing

PRs welcome! Please discuss big changes in an issue first. Add tests where possible, and keep docs/examples in sync.

---

## 📄 License

MIT — see `LICENSE`.

---

### Maintainer Notes (remove in forks)
- If the **GHCR image** isn’t published yet, keep **Option B** as the primary quickstart and publish tags when ready.
- Keep `/remember`, `/recall`, `/link` examples aligned with current schemas.
- Update this README when env vars or routes change.

```
Performance (CPU, D=8192, float32)
- Quality (mean cosine):
  - Unitary+Exact k=1: ≈ 1.000 (PASS gate ≥ 0.70)
  - Gaussian+Wiener − Tikhonov Δcos (raw): k=1 ≈ 0.030 (borderline), k=4 ≈ 0.087, k=16 ≈ 0.052 (PASS ≥ 0.03)
- Unbind latency p99 (ms):
  - Unitary+Exact: ≈ 0.80 ms (PASS ≤ 1.0 ms)
  - Gaussian+Wiener: ≈ 0.72 ms
  - Gaussian+Tikhonov: ≈ 0.80 ms
- Reproduce locally:
  - `PYTHONPATH=. MPLBACKEND=Agg python benchmarks/cognition_core_bench.py`
  - Outputs: `benchmarks/cognition_quality.csv`, `benchmarks/cognition_latency.csv` (and PNGs if matplotlib is available)

Charts
- Recovery vs k: `benchmarks/cognition_cosine.png`
- Unbind latency p99: `benchmarks/cognition_unbind_p99.png`
