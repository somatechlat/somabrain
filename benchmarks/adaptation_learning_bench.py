"""Adaptation Learning Benchmark
=================================

End-to-end benchmark that exercises SomaBrain's online learning via the
evaluate/feedback endpoints and plots the evolution of learning weights.

Features:
- Optional memory seeding for retrieval context (synthetic facts)
- Up to thousands of feedback iterations (default 3000)
- Captures retrieval weights (alpha, beta, gamma, tau)
- Captures utility weights (lambda_, mu, nu)
- Captures learning_rate and history length
- Saves JSON artifact with full time series and a matplotlib PNG plot

This uses the public REST API:
  - POST /context/evaluate
  - POST /context/feedback
  - GET  /context/adaptation/state
  - POST /remember (optional seeding)

Environment overrides:
  SOMA_API_URL       Base URL, default http://127.0.0.1:9696
  SOMABRAIN_TENANT   Tenant header value, default "learnbench"
  SOMABRAIN_TOKEN    Optional Bearer token for Authorization

CLI usage examples:
  python benchmarks/adaptation_learning_bench.py --iterations 3000 --plot
  python benchmarks/adaptation_learning_bench.py --seed 500 --iterations 1500 --sample-every 10 --plot

Artifacts written under artifacts/learning/:
  - learning_timeseries_<ts>.json
  - learning_plot_<ts>.png
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import time
import uuid
from typing import Dict, List, Optional, Tuple, Callable, Any

import requests
import random
import csv
from typing import Iterable

# Deterministic embedder to match server-side retrieval behavior
try:
    from somabrain.embeddings import TinyDeterministicEmbedder  # type: ignore
except Exception:
    TinyDeterministicEmbedder = None  # type: ignore
    # Local minimal fallback to ensure memstore seeding works without imports
    import hashlib  # type: ignore
    import numpy as _np  # type: ignore

    class _LocalDeterministicEmbedder:
        def __init__(self, dim: int = 256, seed_salt: int = 1337):
            self.dim = int(dim)
            self.seed_salt = int(seed_salt)

        def _seed(self, text: str) -> int:
            h = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
            return int.from_bytes(h, "big") ^ self.seed_salt

        def embed(self, text: str):
            rng = _np.random.default_rng(self._seed(text))
            v = rng.normal(0.0, 1.0, size=self.dim).astype("float32")
            n = float(_np.linalg.norm(v))
            if n > 0:
                v /= n
            return v


DEFAULT_BASE = os.getenv("SOMA_API_URL", "http://127.0.0.1:9696").rstrip("/")
DEFAULT_TENANT = os.getenv("SOMABRAIN_TENANT", "learnbench")
DEFAULT_TOKEN = os.getenv("SOMABRAIN_TOKEN", "").strip()

ART_DIR = pathlib.Path("artifacts/learning")
ART_DIR.mkdir(parents=True, exist_ok=True)

# Default memory HTTP endpoint follows centralized settings/env
DEFAULT_MEMSTORE_URL = os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "").strip() or os.getenv("MEMORY_SERVICE_URL", "").strip() or ""


def _headers(session_id: Optional[str] = None) -> Dict[str, str]:
    h: Dict[str, str] = {
        "X-Model-Confidence": "8.5",
    }
    if session_id:
        h["X-Session-ID"] = session_id
    if DEFAULT_TOKEN:
        h["Authorization"] = f"Bearer {DEFAULT_TOKEN}"
    return h


def _get(path: str, timeout: float = 10.0, headers: Optional[Dict[str, str]] = None) -> requests.Response:
    resp = requests.get(f"{DEFAULT_BASE}/{path.lstrip('/')}", timeout=timeout, headers=headers)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        # Print server-provided error details to aid debugging
        try:
            print("GET error body:", resp.text)
        except Exception:
            pass
        raise e
    return resp


def _post(path: str, payload: dict, timeout: float = 15.0, headers: Optional[Dict[str, str]] = None) -> requests.Response:
    resp = requests.post(
        f"{DEFAULT_BASE}/{path.lstrip('/')}",
        json=payload,
        headers=headers,
        timeout=timeout,
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        # Print request context and server error to quickly identify contract mismatches
        print(f"POST {path} failed: status={resp.status_code}")
        try:
            print("payload:", json.dumps(payload)[:500])
        except Exception:
            pass
        try:
            print("response:", resp.text)
        except Exception:
            pass
        raise e
    return resp


def seed_memories(n: int, *, tenant: str, namespace: str = "wm") -> None:
    """Seed N synthetic facts via /remember.

    Uses a simple "Author{i} wrote Book{i}" format, which maps into the runtime's
    scoring text fields. This is optional but can improve retrieval context during
    evaluate() calls.
    """
    if n <= 0:
        return
    h = _headers()
    for i in range(1, n + 1):
        fact = f"Author{i} wrote Book{i}"
        body = {
            "payload": {
                "task": fact,
                "content": fact,
                "memory_type": "semantic",
                "importance": 1,
                "tenant": tenant,
                "namespace": namespace,
            }
        }
        try:
            _post("remember", body, headers=h, timeout=10.0)
        except Exception as exc:
            # Fail soft on occasional write issues to avoid blocking the whole run.
            # The adaptation loop does not require full seeding to proceed.
            print(f"seed[{i}] failed: {exc}")
        if i % 200 == 0:
            print(f"Seeded {i}/{n}")


def seed_target_memory(*, tenant: str, content: str, task: Optional[str] = None, namespace: str = "wm") -> None:
    """Seed a single target memory to later track its retrieval rank."""
    h = _headers()
    body = {
        "payload": {
            "task": task or content,
            "content": content,
            "memory_type": "semantic",
            "importance": 1,
            "tenant": tenant,
            "namespace": namespace,
        }
    }
    _post("remember", body, headers=h, timeout=10.0)


def _embed_texts(texts: Iterable[str]) -> List[List[float]]:
    """Embed a list of texts using the tiny deterministic embedder (dim=256)."""
    if TinyDeterministicEmbedder is None:
        # Use local fallback if server embedder isn't importable in this process
        emb = _LocalDeterministicEmbedder(dim=256)  # type: ignore[name-defined]
    else:
        emb = TinyDeterministicEmbedder(dim=256)
    return [list(map(float, emb.embed(t))) for t in texts]


def memstore_store(coord: str, payload: dict, base_url: Optional[str] = None, timeout: float = 10.0, memory_type: str = "semantic") -> dict:
    """Store a single memory into the memstore via POST /memories.

    Payload is an arbitrary JSON object. We include tenant and content fields for retrieval.
    """
    url = f"{(base_url or DEFAULT_MEMSTORE_URL).rstrip('/')}/memories"
    body = {"coord": coord, "payload": payload, "memory_type": memory_type}
    headers = {}
    token = os.getenv("SOMABRAIN_MEMORY_HTTP_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.post(url, json=body, headers=headers, timeout=timeout)
    # Provide a cleaner message for common auth failures
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        if resp.status_code in (401, 403):
            raise RuntimeError(f"memstore unauthorized ({resp.status_code}): check SOMABRAIN_MEMORY_HTTP_TOKEN")
        raise
    return resp.json()


def memstore_auth_check(base_url: Optional[str] = None, timeout: float = 5.0) -> Tuple[bool, Optional[str]]:
    """Lightweight auth probe against /memories/search to verify token acceptance.

    Returns (ok, error_detail).
    """
    url = f"{(base_url or DEFAULT_MEMSTORE_URL).rstrip('/')}/memories/search"
    headers = {"Content-Type": "application/json"}
    token = os.getenv("SOMABRAIN_MEMORY_HTTP_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.post(url, json={"query": "auth_probe", "top_k": 1}, headers=headers, timeout=timeout)
        if resp.status_code in (401, 403):
            try:
                detail = resp.json().get("detail", str(resp.text))
            except Exception:
                detail = resp.text
            return False, f"{resp.status_code} {detail}"
        # Accept 200 or even 404/422 as OK for token; only 401/403 indicates auth block
        return True, None
    except Exception as exc:
        return False, str(exc)


def seed_memstore(n: int, *, tenant: str, memstore_url: Optional[str] = None) -> int:
    """Seed N synthetic facts directly into the memstore used by evaluate() via /memories.

    Returns the number of successful writes.
    """
    if n <= 0:
        return 0
    success = 0
    for i in range(1, n + 1):
        text = f"Author{i} wrote Book{i}"
        coord = f"mem-{tenant}-{i}"
        payload = {"content": text, "tenant": tenant, "kind": "synthetic", "text": text, "title": f"A{i}"}
        try:
            memstore_store(coord, payload, base_url=memstore_url)
            success += 1
        except Exception as exc:
            print(f"seed_memstore[{i}] failed: {exc}")
        if i % 200 == 0:
            print(f"Memstore seeding progress: {i}/{n} (ok={success})")
    return success


def seed_target_memstore(*, tenant: str, content: str, memstore_url: Optional[str] = None) -> None:
    """Seed a single target memory directly into the memstore used by evaluate()."""
    coord = f"target-{tenant}-{uuid.uuid4().hex[:8]}"
    payload = {"content": content, "tenant": tenant, "kind": "target", "text": content, "title": "target"}
    memstore_store(coord, payload, base_url=memstore_url)


def fetch_adaptation_state(tenant_id: Optional[str] = None) -> dict:
    q = "context/adaptation/state"
    if tenant_id:
        q += f"?tenant_id={tenant_id}"
    return _get(q, headers=_headers()).json()


def run_adaptation(
    iterations: int,
    *,
    top_k: int = 3,
    sample_every: int = 1,
    sleep_ms: int = 0,
    query: str = "measure my adaptation progress",
    tenant_base: Optional[str] = None,
    feedback_fn: Optional[Callable[[int], Tuple[float, float]]] = None,
    track_target: bool = False,
    target_text: Optional[str] = None,
    target_query: Optional[str] = None,
    seed_target: bool = False,
    seed_memstore_count: int = 0,
    memstore_url: Optional[str] = None,
    seed_target_memstore_flag: bool = False,
    do_reset: bool = False,
    base_lr_override: Optional[float] = None,
    constraints_override: Optional[Dict[str, float]] = None,
    retrieval_defaults_override: Optional[Dict[str, float]] = None,
    utility_defaults_override: Optional[Dict[str, float]] = None,
) -> dict:
    session_id = f"bench-{uuid.uuid4().hex[:16]}"
    base_tenant = tenant_base or DEFAULT_TENANT
    tenant_id = f"{base_tenant}-{uuid.uuid4().hex[:8]}"
    h = _headers(session_id=session_id)
    # Optional: reset adaptation if explicitly requested
    if do_reset:
        try:
            reset_payload: Dict[str, Any] = {
                "tenant_id": tenant_id,
                "reset_history": True,
            }
            if base_lr_override is not None:
                reset_payload["base_lr"] = float(base_lr_override)
            if retrieval_defaults_override is not None:
                reset_payload["retrieval_defaults"] = retrieval_defaults_override
            if utility_defaults_override is not None:
                reset_payload["utility_defaults"] = utility_defaults_override
            if constraints_override is not None:
                reset_payload["constraints"] = constraints_override
            _post("context/adaptation/reset", reset_payload, headers=_headers())
        except Exception as exc:
            print(f"Warning: reset failed or not available: {exc}")
    # Optionally seed memstore corpus for evaluate() retrieval
    memstore_auth_ok: Optional[bool] = None
    memstore_seeded_count: int = 0
    if seed_memstore_count > 0 or (track_target and seed_target_memstore_flag):
        ok, detail = memstore_auth_check(memstore_url)
        memstore_auth_ok = ok
        if not ok:
            print(f"Memstore auth check failed: {detail}")
        if ok and seed_memstore_count > 0:
            try:
                memstore_seeded_count = seed_memstore(seed_memstore_count, tenant=tenant_id, memstore_url=memstore_url)
                print(f"Memstore seeded ok={memstore_seeded_count}/{seed_memstore_count} for tenant={tenant_id}")
            except Exception as exc:
                print(f"Warning: memstore seeding failed: {exc}")

    # Optionally seed a target memory for rank tracking (memstore and/or internal memory)
    if track_target and seed_target and target_text:
        try:
            # Seed into app memory for completeness
            seed_target_memory(tenant=tenant_id, content=target_text)
        except Exception as exc:
            print(f"Warning: failed to seed target memory into app memory: {exc}")
        try:
            if seed_target_memstore_flag and (memstore_auth_ok or memstore_auth_ok is None):
                seed_target_memstore(tenant=tenant_id, content=target_text, memstore_url=memstore_url)
        except Exception as exc:
            print(f"Warning: failed to seed target memory into memstore: {exc}")

    # If tracking and a target-specific query is provided, prefer it
    if track_target and target_query:
        query = target_query
    elif track_target and target_text:
        # Use the target text as query if no explicit target-query is provided
        query = target_text

    eval_payload = {
        "session_id": session_id,
        "query": query,
        "top_k": top_k,
        "tenant_id": tenant_id,
    }
    eval_resp = _post("context/evaluate", eval_payload, headers=h).json()
    last_prompt = eval_resp.get("prompt")

    # Time series containers
    steps: List[int] = []
    alpha: List[float] = []
    beta: List[float] = []
    gamma: List[float] = []
    tau: List[float] = []
    lambda_: List[float] = []
    mu: List[float] = []
    nu: List[float] = []
    lr: List[float] = []
    hist: List[int] = []
    # Context for auxiliary series (gains/constraints)
    aux_series: Dict[str, Dict[str, List[float]]] = {}
    # Optional target rank series aligned with sampling steps
    target_rank: List[Optional[int]] = []
    # Retrieval count per sample (how many memories were returned)
    retrieval_counts: List[int] = []

    def record_state(i: int) -> None:
        s = fetch_adaptation_state(tenant_id=tenant_id)
        steps.append(i)
        alpha.append(s["retrieval"]["alpha"])  # type: ignore[index]
        beta.append(s["retrieval"]["beta"])    # type: ignore[index]
        gamma.append(s["retrieval"]["gamma"])  # type: ignore[index]
        tau.append(s["retrieval"]["tau"])      # type: ignore[index]
        lambda_.append(s["utility"]["lambda_"]) # type: ignore[index]
        mu.append(s["utility"]["mu"])           # type: ignore[index]
        nu.append(s["utility"]["nu"])           # type: ignore[index]
        lr.append(s.get("learning_rate", 0.0))
        hist.append(int(s.get("history_len", 0)))
        # Store gains and constraints time series lazily
        if "gains" not in aux_series:
            aux_series["gains"] = {k: [] for k in ["alpha", "gamma", "lambda_", "mu", "nu"]}
        if "constraints" not in aux_series:
            # Track only key constraints to reduce clutter
            aux_series["constraints"] = {k: [] for k in [
                "alpha_min", "alpha_max", "gamma_min", "gamma_max",
                "lambda_min", "lambda_max", "mu_min", "mu_max", "nu_min", "nu_max"
            ]}
        for k in aux_series["gains"].keys():
            aux_series["gains"][k].append(float(s.get("gains", {}).get(k, 0.0)))
        for k in aux_series["constraints"].keys():
            aux_series["constraints"][k].append(float(s.get("constraints", {}).get(k, 0.0)))

    # Record initial state
    record_state(0)
    # When tracking, capture initial target rank from first evaluate
    if track_target and target_text:
        try:
            r0: Optional[int] = None
            mems = eval_resp.get("memories") or []
            retrieval_counts.append(int(len(mems)))
            for idx, m in enumerate(mems, start=1):
                meta = m.get("metadata") or {}
                mc = str(meta.get("content") or "")
                mt = str(meta.get("task") or "")
                if target_text == mc or target_text == mt:
                    r0 = idx
                    break
            target_rank.append(r0)
        except Exception:
            target_rank.append(None)
            retrieval_counts.append(0)

    # Default feedback function -> constant positive reinforcement
    if feedback_fn is None:
        def feedback_fn(step: int) -> Tuple[float, float]:  # type: ignore[no-redef]
            return (0.9, 0.9)

    for i in range(1, iterations + 1):
        # Use the last known prompt; refresh it only periodically to avoid
        # exceeding the server working-memory cap of 10 items per session.
        prompt = last_prompt
        util, rew = feedback_fn(i)
        # Clip defensively to [0,1]
        util = max(0.0, min(1.0, float(util)))
        rew = max(0.0, min(1.0, float(rew)))
        feedback_payload = {
            "session_id": session_id,
            "query": query,
            "prompt": prompt,
            "response_text": "ack",
            "utility": util,
            "reward": rew,
            "tenant_id": tenant_id,
        }
        _post("context/feedback", feedback_payload, headers=h)
        if sleep_ms > 0:
            time.sleep(max(0.0, sleep_ms) / 1000.0)
        # Optionally resample state to reduce overhead
        do_sample = (i % max(1, sample_every) == 0) or (i == iterations)
        if do_sample:
            record_state(i)
        # Refresh evaluate to keep prompts contextual only on sample steps,
        # but do not append to working memory to avoid exceeding 10 entries.
        if do_sample:
            eval_refresh = {
                "session_id": "",  # empty -> builder will not write to WM
                "query": query,
                "top_k": top_k,
                "tenant_id": tenant_id,
            }
            eval_resp = _post("context/evaluate", eval_refresh, headers=h).json()
            last_prompt = eval_resp.get("prompt")
            # Track target rank at each sample step
            if track_target and target_text:
                rank_val: Optional[int] = None
                try:
                    mems = eval_resp.get("memories") or []
                    retrieval_counts.append(int(len(mems)))
                    for idx, m in enumerate(mems, start=1):
                        meta = m.get("metadata") or {}
                        mc = str(meta.get("content") or "")
                        mt = str(meta.get("task") or "")
                        if target_text == mc or target_text == mt:
                            rank_val = idx
                            break
                except Exception:
                    rank_val = None
                target_rank.append(rank_val)
            else:
                # Still track retrieval count when not tracking a specific target
                try:
                    mems = eval_resp.get("memories") or []
                    retrieval_counts.append(int(len(mems)))
                except Exception:
                    retrieval_counts.append(0)

    # Package result
    result = {
        "steps": steps,
        "retrieval": {"alpha": alpha, "beta": beta, "gamma": gamma, "tau": tau},
        "utility": {"lambda_": lambda_, "mu": mu, "nu": nu},
        "learning_rate": lr,
        "history": hist,
        "meta": {
            "tenant": tenant_id,
            "top_k": top_k,
            "iterations": iterations,
            "base_url": DEFAULT_BASE,
            "sample_every": sample_every,
            "query": query,
            "tenant_base": base_tenant,
        },
    }
    # Attach gains/constraints series if collected
    if "gains" in aux_series:
        result["gains"] = aux_series["gains"]
    if "constraints" in aux_series:
        result["constraints"] = aux_series["constraints"]
    if track_target:
        result["target"] = {
            "text": target_text,
            "query": query,
            "rank": target_rank,
        }
    # Attach retrieval counts
    if retrieval_counts:
        result["retrieval_count"] = retrieval_counts
    # Attach memstore auth/seeding meta if we attempted any interaction
    if seed_memstore_count > 0 or (track_target and seed_target_memstore_flag):
        if isinstance(result.get("meta"), dict):
            result["meta"]["memstore_auth_ok"] = bool(memstore_auth_ok) if memstore_auth_ok is not None else None
            result["meta"]["memstore_seeded_ok"] = int(memstore_seeded_count)
    return result


def save_artifacts(data: dict, *, plot: bool = True) -> pathlib.Path:
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    json_path = ART_DIR / f"learning_timeseries_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    if not plot:
        return json_path

    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print("matplotlib not available; skipping plot:", exc)
        return json_path

    steps = data.get("steps", [])
    ret = data.get("retrieval", {})
    utl = data.get("utility", {})
    lr = data.get("learning_rate", [])
    hist = data.get("history", [])
    hist_delta = [h - hist[0] for h in hist] if hist else []
    gains = data.get("gains", {})
    constraints = data.get("constraints", {})
    target = data.get("target", {})
    ranks = target.get("rank", []) if isinstance(target, dict) else []

    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)

    # Retrieval weights
    ax = axes[0][0]
    ax.plot(steps, ret.get("alpha", []), label="alpha", lw=2)
    ax.plot(steps, ret.get("beta", []), label="beta", lw=2)
    ax.plot(steps, ret.get("gamma", []), label="gamma", lw=2)
    ax.plot(steps, ret.get("tau", []), label="tau", lw=2)
    # Overlay alpha constraints if available
    if constraints:
        a_min = constraints.get("alpha_min")
        a_max = constraints.get("alpha_max")
        if a_min and len(a_min) == len(steps):
            ax.hlines(a_min[0], steps[0], steps[-1], colors="#888", linestyles=":", label="alpha_min")
        if a_max and len(a_max) == len(steps):
            ax.hlines(a_max[0], steps[0], steps[-1], colors="#666", linestyles="--", label="alpha_max")
    ax.set_title("Retrieval Weights")
    ax.set_xlabel("Step")
    ax.set_ylabel("Value")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")

    # Utility weights
    ax = axes[0][1]
    ax.plot(steps, utl.get("lambda_", []), label="lambda", lw=2)
    ax.plot(steps, utl.get("mu", []), label="mu", lw=2)
    ax.plot(steps, utl.get("nu", []), label="nu", lw=2)
    # Overlay lambda constraints if available
    if constraints:
        l_min = constraints.get("lambda_min")
        l_max = constraints.get("lambda_max")
        if l_min and len(l_min) == len(steps):
            ax.hlines(l_min[0], steps[0], steps[-1], colors="#888", linestyles=":", label="lambda_min")
        if l_max and len(l_max) == len(steps):
            ax.hlines(l_max[0], steps[0], steps[-1], colors="#666", linestyles="--", label="lambda_max")
    ax.set_title("Utility Weights")
    ax.set_xlabel("Step")
    ax.set_ylabel("Value")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")

    # Learning rate
    ax = axes[1][0]
    ax.plot(steps, lr, color="purple", lw=2, label="lr")
    # Overlay selected gains on a twin y-axis for visibility
    if gains:
        ax2 = ax.twinx()
        if gains.get("alpha"):
            ax2.plot(steps, gains["alpha"], color="#cc99ff", lw=1.5, ls=":", label="gain_alpha")
        if gains.get("lambda_"):
            ax2.plot(steps, gains["lambda_"], color="#99ccff", lw=1.5, ls="--", label="gain_lambda")
        ax2.set_ylabel("gains")
        # Merge legends
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc="best")
    ax.set_title("Effective Learning Rate + Gains")
    ax.set_xlabel("Step")
    ax.set_ylabel("lr")
    ax.grid(True, alpha=0.3)

    # Feedback history (delta) with optional target rank
    ax = axes[1][1]
    ax.plot(steps, hist_delta, color="teal", lw=2, label="history Δ")
    if ranks:
        ax2 = ax.twinx()
        ax2.plot(steps, ranks, color="#d62728", lw=1.5, ls="-.", label="target rank (lower=better)")
        ax2.set_ylabel("rank")
        # Merge legends
        l1, lb1 = ax.get_legend_handles_labels()
        l2, lb2 = ax2.get_legend_handles_labels()
        ax.legend(l1 + l2, lb1 + lb2, loc="best")
    ax.set_title("Feedback History Δ + Target Rank")
    ax.set_xlabel("Step")
    ax.set_ylabel("count")
    ax.grid(True, alpha=0.3)

    png_path = ART_DIR / f"learning_plot_{ts}.png"
    fig.suptitle("SomaBrain Adaptation Learning Benchmark", fontsize=14)
    fig.savefig(png_path, dpi=160)
    plt.close(fig)
    print(f"Wrote plot {png_path}")
    return png_path


def _load_schedule(path: str) -> List[Tuple[float, float]]:
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Schedule file not found: {path}")
    # Try JSON first
    try:
        with open(p, "r", encoding="utf-8") as f:
            data: Any = json.load(f)
        if isinstance(data, list):
            sched: List[Tuple[float, float]] = []
            for item in data:
                if isinstance(item, (int, float)):
                    v = float(item)
                    sched.append((v, v))
                elif isinstance(item, dict):
                    u = float(item.get("utility", item.get("u", 0.0)))
                    r = float(item.get("reward", item.get("r", u)))
                    sched.append((u, r))
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    u = float(item[0])
                    r = float(item[1])
                    sched.append((u, r))
            if sched:
                return sched
    except Exception:
        pass
    # Try CSV: columns utility,reward or u,r
    sched_csv: List[Tuple[float, float]] = []
    with open(p, "r", encoding="utf-8") as f:
        try:
            reader = csv.DictReader(f)
            for row in reader:
                if not row:
                    continue
                u = row.get("utility") or row.get("u")
                r = row.get("reward") or row.get("r") or u
                if u is None:
                    continue
                sched_csv.append((float(u), float(r)))
        except Exception:
            f.seek(0)
            reader2 = csv.reader(f)
            for pair in reader2:
                if len(pair) >= 2:
                    try:
                        sched_csv.append((float(pair[0]), float(pair[1])))
                    except Exception:
                        continue
    if not sched_csv:
        raise ValueError("Unsupported schedule format; provide JSON(list) or CSV with utility,reward")
    return sched_csv


def main():
    ap = argparse.ArgumentParser(description="SomaBrain adaptation learning benchmark")
    ap.add_argument("--iterations", type=int, default=3000, help="Number of feedback iterations")
    ap.add_argument("--seed", type=int, default=0, help="Optional synthetic memories to seed via /remember")
    ap.add_argument("--top-k", type=int, default=3, help="Top-K for evaluate() context")
    ap.add_argument("--sample-every", type=int, default=10, help="Record adaptation state every N steps")
    ap.add_argument("--sleep-ms", type=int, default=0, help="Sleep between iterations (ms)")
    ap.add_argument("--plot", action="store_true", help="Render matplotlib plot")
    ap.add_argument("--query", type=str, default="measure my adaptation progress", help="Evaluation query text")
    ap.add_argument("--tenant", type=str, default=None, help="Override base tenant (suffix will be auto-appended)")
    # Memstore seeding and config
    ap.add_argument("--seed-memstore", type=int, default=0, help="Seed N synthetic memories directly into memstore for evaluate retrieval")
    ap.add_argument(
        "--memstore-url",
        type=str,
        default=os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT", DEFAULT_MEMSTORE_URL),
        help="Override memory HTTP endpoint",
    )

    # Feedback configuration
    ap.add_argument(
        "--feedback-mode",
        type=str,
        default="constant",
        choices=["constant", "alternating", "random", "schedule"],
        help="How to generate feedback values per step",
    )
    ap.add_argument("--utility", type=float, default=0.9, help="Utility value for constant/positive phase")
    ap.add_argument("--reward", type=float, default=0.9, help="Reward value for constant/positive phase")
    ap.add_argument("--neg-utility", type=float, default=0.1, help="Utility value for negative phase in alternating mode")
    ap.add_argument("--neg-reward", type=float, default=0.1, help="Reward value for negative phase in alternating mode")
    ap.add_argument("--utility-min", type=float, default=0.1, help="Min utility for random mode")
    ap.add_argument("--utility-max", type=float, default=0.9, help="Max utility for random mode")
    ap.add_argument("--reward-min", type=float, default=0.1, help="Min reward for random mode")
    ap.add_argument("--reward-max", type=float, default=0.9, help="Max reward for random mode")
    ap.add_argument("--rng-seed", type=int, default=None, help="Random seed for random mode")
    ap.add_argument("--schedule-file", type=str, default=None, help="JSON/CSV file providing per-step utility/reward")
    # Target rank tracking
    ap.add_argument("--track-target", action="store_true", help="Track rank of a seeded target memory at each sample step")
    ap.add_argument("--target-text", type=str, default="Author777 wrote Book777", help="Target memory content to seed and track")
    ap.add_argument("--target-query", type=str, default=None, help="Use a specific query when tracking; defaults to target-text if provided")
    ap.add_argument("--seed-target", action="store_true", help="Seed the target memory into the run's tenant before starting")
    ap.add_argument("--seed-target-memstore", action="store_true", help="Also seed the target memory directly into memstore")
    # Optional adaptation reset and overrides
    ap.add_argument("--reset-adaptation", action="store_true", help="Reset adaptation state for the run (uses overrides if provided)")
    ap.add_argument("--base-lr", type=float, default=None, help="Override base learning rate on reset")
    ap.add_argument("--constraints-json", type=str, default=None, help="Path to JSON file with constraints to apply on reset")
    ap.add_argument("--retrieval-defaults-json", type=str, default=None, help="Path to JSON file with retrieval defaults to apply on reset")
    ap.add_argument("--utility-defaults-json", type=str, default=None, help="Path to JSON file with utility defaults to apply on reset")
    args = ap.parse_args()

    if args.seed > 0:
        print(f"Seeding {args.seed} synthetic facts to tenant={DEFAULT_TENANT} ...")
        seed_memories(args.seed, tenant=DEFAULT_TENANT)

    # Build feedback provider
    fb_mode = args.feedback_mode
    fb_meta: Dict[str, Any] = {"mode": fb_mode}
    if fb_mode == "constant":
        const_u = float(args.utility)
        const_r = float(args.reward)
        fb_meta.update({"utility": const_u, "reward": const_r})

        def provider(step: int) -> Tuple[float, float]:
            return const_u, const_r

    elif fb_mode == "alternating":
        pos = (float(args.utility), float(args.reward))
        neg = (float(args.neg_utility), float(args.neg_reward))
        fb_meta.update({"pos": pos, "neg": neg})

        def provider(step: int) -> Tuple[float, float]:
            return pos if (step % 2 == 1) else neg

    elif fb_mode == "random":
        umin, umax = float(args.utility_min), float(args.utility_max)
        rmin, rmax = float(args.reward_min), float(args.reward_max)
        if args.rng_seed is not None:
            random.seed(int(args.rng_seed))
        fb_meta.update({"utility_min": umin, "utility_max": umax, "reward_min": rmin, "reward_max": rmax, "rng_seed": args.rng_seed})

        def provider(step: int) -> Tuple[float, float]:
            return random.uniform(umin, umax), random.uniform(rmin, rmax)

    elif fb_mode == "schedule":
        if not args.schedule_file:
            raise ValueError("--schedule-file is required for schedule mode")
        sched = _load_schedule(args.schedule_file)
        fb_meta.update({"schedule_file": args.schedule_file, "length": len(sched)})

        def provider(step: int) -> Tuple[float, float]:
            # 1-indexed step -> 0-indexed list, cycle through schedule
            idx = (step - 1) % len(sched)
            return sched[idx]

    else:
        raise ValueError(f"Unsupported feedback mode: {fb_mode}")

    print(
        f"Running adaptation: iterations={args.iterations} top_k={args.top_k} sample_every={args.sample_every} mode={fb_mode}"
    )
    # Load optional JSON overrides
    def _load_json(path: Optional[str]) -> Optional[Dict[str, Any]]:
        if not path:
            return None
        p = pathlib.Path(path)
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    constraints_override = _load_json(args.constraints_json)
    retrieval_defaults_override = _load_json(args.retrieval_defaults_json)
    utility_defaults_override = _load_json(args.utility_defaults_json)

    data = run_adaptation(
        args.iterations,
        top_k=args.top_k,
        sample_every=args.sample_every,
        sleep_ms=args.sleep_ms,
        query=args.query,
        tenant_base=(args.tenant or DEFAULT_TENANT),
        feedback_fn=provider,
        track_target=bool(args.track_target),
        target_text=(args.target_text if args.track_target else None),
        target_query=(args.target_query if args.target_query else (args.target_text if args.track_target else None)),
        seed_target=bool(args.seed_target and args.track_target),
        seed_memstore_count=int(args.seed_memstore),
        memstore_url=(args.memstore_url or DEFAULT_MEMSTORE_URL),
        seed_target_memstore_flag=bool(args.seed_target_memstore and args.track_target),
        do_reset=bool(args.reset_adaptation),
        base_lr_override=(float(args.base_lr) if args.base_lr is not None else None),
        constraints_override=constraints_override,
        retrieval_defaults_override=retrieval_defaults_override,
        utility_defaults_override=utility_defaults_override,
    )
    # Attach feedback meta
    if isinstance(data.get("meta"), dict):
        data["meta"]["feedback"] = fb_meta
    path = save_artifacts(data, plot=args.plot)
    print(f"Artifacts written under {ART_DIR} ({path})")


if __name__ == "__main__":
    main()
