#!/usr/bin/env bash
set -euo pipefail

HOST=${1:-http://localhost:9696}
TENANT=${2:-demo}

hdr=( -H "Content-Type: application/json" -H "X-Tenant-ID: $TENANT" )

echo "Seeding corpus..."
curl -s -X POST "$HOST/remember" "${hdr[@]}" -d '{"payload":{"task":"solar energy optimization with panels","memory_type":"episodic"}}' >/dev/null
curl -s -X POST "$HOST/remember" "${hdr[@]}" -d '{"payload":{"task":"battery storage for solar microgrids","memory_type":"episodic"}}' >/dev/null
curl -s -X POST "$HOST/remember" "${hdr[@]}" -d '{"payload":{"task":"photovoltaic inverter diagnostics","memory_type":"episodic"}}' >/dev/null
curl -s -X POST "$HOST/remember" "${hdr[@]}" -d '{"payload":{"task":"intro to renewable energy planning","memory_type":"episodic"}}' >/dev/null

echo "Baseline vector-only retrieval..."
base=$(curl -s -X POST "$HOST/rag/retrieve" "${hdr[@]}" -d '{"query":"solar energy planning","top_k":5,"retrievers":["vector"],"persist":false}')
echo "$base" | jq '{baseline: .candidates | map(.payload.task)}'

echo "Persisting session (vector+wm)..."
persist=$(curl -s -X POST "$HOST/rag/retrieve" "${hdr[@]}" -d '{"query":"solar energy planning","top_k":5,"retrievers":["vector","wm"],"persist":true}')
echo "$persist" | jq '{session_coord: .session_coord, candidates: .candidates | map(.payload.task)}'

echo "Graph-only retrieval after persist..."
graph=$(curl -s -X POST "$HOST/rag/retrieve" "${hdr[@]}" -d '{"query":"solar energy planning","top_k":5,"retrievers":["graph"],"persist":false}')
echo "$graph" | jq '{graph_only: .candidates | map(.payload.task)}'

echo "Planning baseline..."
plan_base=$(curl -s -X POST "$HOST/plan/suggest" "${hdr[@]}" -d '{"task_key":"solar project planning","max_steps":5,"rel_types":["depends_on","causes","part_of","motivates","related"]}')
echo "$plan_base" | jq '{baseline_plan: .plan}'

echo "Planning after persist (using retrieved_with)..."
plan_rich=$(curl -s -X POST "$HOST/plan/suggest" "${hdr[@]}" -d '{"task_key":"solar project planning","max_steps":5,"rel_types":["retrieved_with","depends_on","related"]}')
echo "$plan_rich" | jq '{post_persist_plan: .plan}'

echo "Metrics snapshot (RAG)..."
curl -s "$HOST/metrics" | egrep 'somabrain_rag_requests_total|somabrain_rag_retrieve_latency_seconds|somabrain_rag_candidates_total|somabrain_rag_persist_total' || true
