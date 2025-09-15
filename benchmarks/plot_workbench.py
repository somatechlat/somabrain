"""Plot the deterministic numerics workbench results.

Reads `benchmarks/workbench_numerics_results.json` and writes PNGs to
`benchmarks/plots/`.
"""

import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
plt.figure(figsize=(6, 4))
for dtype, series in tiny.items():
    xs = list(series.keys())
    ys = [series[x] for x in xs]
    plt.plot(xs, ys, marker="o", label=dtype)
plt.xscale("log", base=2)
plt.yscale("log")
plt.xlabel("D (log2)")
plt.ylabel("tiny amplitude")
plt.title("Tiny-floor amplitude by dtype and D")
plt.grid(True, which="both", ls="--", alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig(OUT_DIR / "tiny_floor.png", dpi=150)
plt.close()

# Unitary roundtrip errors
rt = parse_metric_dict(data.get("unitary_roundtrip", {}))
plt.figure(figsize=(6, 4))
for dtype, series in rt.items():
    xs = list(series.keys())
    ys = [series[x] for x in xs]
    plt.plot(xs, ys, marker="o", label=dtype)
plt.xscale("log", base=2)
plt.yscale("log")
plt.xlabel("D")
plt.ylabel("RMS roundtrip error")
plt.title("Unitary FFT roundtrip error")
plt.grid(True, which="both", ls="--", alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig(OUT_DIR / "unitary_roundtrip.png", dpi=150)
plt.close()

# Role norms
roles = parse_metric_dict(data.get("role_norms", {}))
plt.figure(figsize=(6, 3))
labels = []
vals = []
for dtype, series in roles.items():
    for D, v in series.items():
        labels.append(f"{dtype}\nD={D}")
        vals.append(v)
x = np.arange(len(labels))
plt.bar(x, vals)
plt.xticks(x, labels, rotation=45, ha="right")
plt.ylabel("L2 norm")
plt.title("Generated role L2 norms")
plt.ylim(0.95, 1.05)
plt.tight_layout()
plt.savefig(OUT_DIR / "role_norms.png", dpi=150)
plt.close()

# Bind/unbind cosines
binds = parse_metric_dict(data.get("bind_unbind", {}))
plt.figure(figsize=(6, 3))
labels = []
vals = []
for dtype, series in binds.items():
    for D, v in series.items():
        labels.append(f"{dtype}\nD={D}")
        vals.append(v)
x = np.arange(len(labels))
plt.bar(x, vals)
plt.xticks(x, labels, rotation=45, ha="right")
plt.ylabel("cosine")
plt.title("Bind/Unbind cosines (should be ~1)")
plt.ylim(0.9, 1.01)
plt.tight_layout()
plt.savefig(OUT_DIR / "bind_unbind.png", dpi=150)
plt.close()

print(f"Wrote {len(list(OUT_DIR.glob('*.png')))} PNG(s) to {OUT_DIR}")
