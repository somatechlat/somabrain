"""Plot the deterministic numerics workbench results.

Reads `benchmarks/workbench_numerics_results.json` and writes PNGs to
`benchmarks/plots/`.
"""

import json
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio

pio.templates.default = "plotly_dark"

ROOT = Path(__file__).resolve().parent
JSON_PATH = ROOT / "workbench_numerics_results.json"
OUT_DIR = ROOT / "plots"
OUT_DIR.mkdir(exist_ok=True)

with open(JSON_PATH, "r") as f:
    data = json.load(f)


# Utility to parse keys like "float32:128"
def parse_metric_dict(d):
    by_dtype = {}
    for k, v in d.items():
        dtype, D = k.split(":")
        D = int(D)
        by_dtype.setdefault(dtype, {})[D] = float(v)
    # sort
    for dtype in by_dtype:
        by_dtype[dtype] = dict(sorted(by_dtype[dtype].items()))
    return by_dtype


# Tiny floor
tiny = parse_metric_dict(data.get("tiny_floor", {}))
fig = go.Figure()
for dtype, series in tiny.items():
    xs = list(series.keys())
    ys = [series[x] for x in xs]
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name=dtype))
fig.update_layout(
    title="Tiny-floor amplitude by dtype and D",
    xaxis_title="D (log2)",
    yaxis_title="tiny amplitude",
    xaxis_type="log",
    yaxis_type="log",
)
fig.write_html(OUT_DIR / "tiny_floor.html")

# Unitary roundtrip errors
rt = parse_metric_dict(data.get("unitary_roundtrip", {}))
fig = go.Figure()
for dtype, series in rt.items():
    xs = list(series.keys())
    ys = [series[x] for x in xs]
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name=dtype))
fig.update_layout(
    title="Unitary FFT roundtrip error",
    xaxis_title="D",
    yaxis_title="RMS roundtrip error",
    xaxis_type="log",
    yaxis_type="log",
)
fig.write_html(OUT_DIR / "unitary_roundtrip.html")

# Role norms
roles = parse_metric_dict(data.get("role_norms", {}))
labels = []
vals = []
for dtype, series in roles.items():
    for D, v in series.items():
        labels.append(f"{dtype}<br>D={D}")
        vals.append(v)
fig = go.Figure([go.Bar(x=labels, y=vals)])
fig.update_layout(
    title="Generated role L2 norms", yaxis_title="L2 norm", yaxis_range=[0.95, 1.05]
)
fig.write_html(OUT_DIR / "role_norms.html")


# Bind/unbind cosines
binds = parse_metric_dict(data.get("bind_unbind", {}))
labels = []
vals = []
for dtype, series in binds.items():
    for D, v in series.items():
        labels.append(f"{dtype}<br>D={D}")
        vals.append(v)
fig = go.Figure([go.Bar(x=labels, y=vals)])
fig.update_layout(
    title="Bind/Unbind cosines (should be ~1)",
    yaxis_title="cosine",
    yaxis_range=[0.9, 1.01],
)
fig.write_html(OUT_DIR / "bind_unbind.html")

print(f"Wrote {len(list(OUT_DIR.glob('*.html')))} HTML file(s) to {OUT_DIR}")
