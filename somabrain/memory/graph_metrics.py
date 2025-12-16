"""Prometheus metrics for graph operations.

Extracted from memory/graph_client.py per monolithic-decomposition spec.
Provides metrics for SB→SFM graph operations per H2.
"""

from prometheus_client import Counter, Histogram

# Prometheus metrics for SB→SFM graph operations (H2)
SB_GRAPH_LINK_TOTAL = Counter(
    "sb_graph_link_total",
    "Total graph link creation calls from SB to SFM",
    ["tenant", "link_type", "status"],
)

SB_GRAPH_LINK_LATENCY = Histogram(
    "sb_graph_link_latency_seconds",
    "Graph link creation latency from SB to SFM",
    ["tenant", "link_type"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

SB_GRAPH_NEIGHBORS_TOTAL = Counter(
    "sb_graph_neighbors_total",
    "Total graph neighbors query calls from SB to SFM",
    ["tenant", "status"],
)

SB_GRAPH_NEIGHBORS_LATENCY = Histogram(
    "sb_graph_neighbors_latency_seconds",
    "Graph neighbors query latency from SB to SFM",
    ["tenant"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

SB_GRAPH_PATH_TOTAL = Counter(
    "sb_graph_path_total",
    "Total graph path query calls from SB to SFM",
    ["tenant", "status", "found"],
)

SB_GRAPH_PATH_LATENCY = Histogram(
    "sb_graph_path_latency_seconds",
    "Graph path query latency from SB to SFM",
    ["tenant"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)
