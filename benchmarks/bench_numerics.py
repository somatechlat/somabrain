"""Robust numerics comparison harness.

This script implements the recommended CLI and compares current vs proposed
implementations for unbind and normalize operations. It supports module-level
callables as well as instance methods on `QuantumLayer`.

Example:
  python benchmarks/bench_numerics.py \
    --unbind-current somabrain.quantum.unbind_exact \
    --unbind-proposed somabrain.quantum.unbind_exact_unitary \
    --normalize-current somabrain.numerics.normalize_array \
    --normalize-proposed somabrain.numerics.normalize_array \
    --dtype f32 f64 --D 256 1024 --trials 200 --roles unitary nonunitary --postnorm
"""

from __future__ import annotations

import argparse
import importlib
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from somabrain.quantum import HRRConfig, QuantumLayer

OUT_PATH = Path("benchmarks/bench_numerics_results.json")


def resolve_callable(path: Optional[str]):
    """Resolve a dotted import path to either a module-level callable or a
    marker indicating a method on QuantumLayer.

    Returns:
      - a callable object if found on module; or
      - tuple ("method", method_name) if method exists on QuantumLayer; or
      - None if path is falsy.
    """
    if not path:
        return None
    mod_name, _, attr = path.rpartition(".")
    if not mod_name:
        raise ImportError(f"invalid callable path: {path}")
    mod = importlib.import_module(mod_name)
    if hasattr(mod, attr):
        return getattr(mod, attr)
    # try QuantumLayer method
    if hasattr(QuantumLayer, attr):
        return ("method", attr)
    raise AttributeError(f"callable not found: {path}")


def rand_unit_vector(rng: np.random.Generator, D: int, dtype: Any) -> np.ndarray:
    v = rng.normal(0.0, 1.0, size=D).astype(dtype)
    n = float(np.linalg.norm(v))
    if n == 0:
        return np.ones((D,), dtype=dtype) / np.sqrt(D)
    return (v / n).astype(dtype)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na <= 0 or nb <= 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def call_unbind(
    spec,
    qinst: QuantumLayer,
    cvec: np.ndarray,
    bvec: np.ndarray,
    role_token: Optional[str] = None,
):
    """Call either a module function or a QuantumLayer method for unbinding.

    - If spec is ('method', name), call qinst.name(cvec, bvec) or qinst.name(cvec, role_token)
      if the method signature expects a role token.
    - If spec is a callable, try calling spec(c,b) then spec(qinst,c,b) as alternative.
    """
    if spec is None:
        raise RuntimeError("no unbind function supplied")
    if isinstance(spec, tuple) and spec[0] == "method":
        method_name = spec[1]
        meth = getattr(qinst, method_name)
        try:
            return meth(cvec, bvec)
        except TypeError:
            if role_token is not None:
                return meth(cvec, role_token)
            raise
    # module-level callable
    try:
        return spec(cvec, bvec)
    except TypeError:
        return spec(qinst, cvec, bvec)


def call_normalize(spec, x: np.ndarray, D: int, dtype: Any):
    if spec is None:
        raise RuntimeError("no normalize function supplied")
    try:
        return spec(x, D, dtype)
    except TypeError:
        return spec(x, axis=-1, keepdims=False, dtype=dtype)


def run_unbind_trial(
    q: QuantumLayer,
    rng: np.random.Generator,
    D: int,
    dtype: Any,
    unbind_cur,
    unbind_prop,
    role_mode: str,
    postnorm: bool,
    norm_fn: Optional[Callable],
) -> Dict[str, float]:
    a = q.random_vector()
    b = q.random_vector()
    if role_mode == "unitary":
        role_token = "bench:role"
        q.make_unitary_role(role_token)
        c = q.bind_unitary(a, role_token)
    else:
        c = q.bind(a, b)

    rec_cur = call_unbind(
        unbind_cur, q, c, b, role_token if role_mode == "unitary" else None
    )
    rec_prop = call_unbind(
        unbind_prop, q, c, b, role_token if role_mode == "unitary" else None
    )

    if postnorm and norm_fn is not None:
        rec_cur = call_normalize(norm_fn, rec_cur, D, dtype)
        rec_prop = call_normalize(norm_fn, rec_prop, D, dtype)

    mse_cur = float(np.mean((a - rec_cur) ** 2))
    mse_prop = float(np.mean((a - rec_prop) ** 2))
    cos_cur = cosine(a, rec_cur)
    cos_prop = cosine(a, rec_prop)
    return {
        "mse_cur": mse_cur,
        "mse_prop": mse_prop,
        "cos_cur": cos_cur,
        "cos_prop": cos_prop,
    }


def run_normalize_trial(
    rng: np.random.Generator, D: int, dtype: Any, norm_cur, norm_prop
) -> Dict[str, Any]:
    x = rng.normal(0.0, 1.0, size=D).astype(dtype)
    out_cur = call_normalize(norm_cur, x, D, dtype)
    out_prop = call_normalize(norm_prop, x, D, dtype)
    ncur = float(np.linalg.norm(out_cur))
    nprop = float(np.linalg.norm(out_prop))
    diff = float(np.mean((out_cur - out_prop) ** 2))
    return {"ncur": ncur, "nprop": nprop, "diff_mse": diff}


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--unbind-current", required=False)
    p.add_argument("--unbind-proposed", required=False)
    p.add_argument("--normalize-current", required=False)
    p.add_argument("--normalize-proposed", required=False)
    p.add_argument("--dtype", nargs="+", default=["f32"], help="f32 f64")
    p.add_argument("--D", nargs="+", type=int, default=[2048])
    p.add_argument("--trials", type=int, default=200)
    p.add_argument("--roles", nargs="+", default=["unitary"], help="unitary nonunitary")
    p.add_argument("--postnorm", action="store_true")
    args = p.parse_args(argv)

    unbind_cur = resolve_callable(args.unbind_current)
    unbind_prop = resolve_callable(args.unbind_proposed)
    norm_cur = resolve_callable(args.normalize_current)
    norm_prop = resolve_callable(args.normalize_proposed)

    dmap = {"f32": np.float32, "f64": np.float64}
    rng = np.random.default_rng(12345)
    results = {"meta": {"timestamp": time.time(), "args": vars(args)}, "runs": []}

    for dtype_tag in args.dtype:
        dtype = dmap.get(dtype_tag, np.float32)
        for D in args.D:
            cfg = HRRConfig(
                dim=int(D),
                seed=42,
                dtype=("float32" if dtype == np.float32 else "float64"),
            )
            q = QuantumLayer(cfg)
            for role_mode in args.roles:
                run_summary = {
                    "dtype": str(dtype),
                    "D": D,
                    "role": role_mode,
                    "trials": args.trials,
                    "results": [],
                }
                for t in range(args.trials):
                    res = {}
                    if unbind_cur and unbind_prop:
                        res = run_unbind_trial(
                            q,
                            rng,
                            D,
                            dtype,
                            unbind_cur,
                            unbind_prop,
                            role_mode,
                            args.postnorm,
                            norm_prop,
                        )
                    if norm_cur and norm_prop:
                        nres = run_normalize_trial(rng, D, dtype, norm_cur, norm_prop)
                        res["norm"] = nres
                    run_summary["results"].append(res)
                results["runs"].append(run_summary)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote bench summary to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
