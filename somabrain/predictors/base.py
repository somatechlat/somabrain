from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import numpy as np

from somabrain.math.graph_heat import graph_heat_chebyshev, graph_heat_lanczos
import json


def _select_heat_method() -> str:

    m = (
        (settings.getenv("SOMA_HEAT_METHOD", "chebyshev") or "chebyshev")
        .strip()
        .lower()
    )
    return m if m in ("chebyshev", "lanczos") else "chebyshev"


def _now_ts() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


ApplyOp = Callable[[np.ndarray], np.ndarray]


@dataclass
class PredictorConfig:
    diffusion_t: float = 0.5
    alpha: float = 2.0  # confidence = exp(-alpha * mse)
    chebyshev_K: int = 30
    lanczos_m: int = 20


class PredictorBase:
    """Base class for diffusion-backed predictors.

    Contract:
      - Provide apply_A (Laplacian operator) and a domain-specific source vector x0
      - salience() computes y = exp(-t L) x0 via selected method
      - error() computes scalar mse vs observed vector
      - confidence(error) = exp(-alpha * error)
    """

    def __init__(
        self, apply_A: ApplyOp, dim: int, cfg: Optional[PredictorConfig] = None
    ):
        self.apply_A = apply_A
        self.dim = int(dim)
        self.cfg = cfg or PredictorConfig()
        self._method = _select_heat_method()

    def salience(self, x0: np.ndarray) -> np.ndarray:
        t = float(self.cfg.diffusion_t)
        if self._method == "lanczos":
            return graph_heat_lanczos(self.apply_A, x0, t, m=int(self.cfg.lanczos_m))

        # default chebyshev
        class _Cfg:
            truth_chebyshev_K = int(self.cfg.chebyshev_K)

        return graph_heat_chebyshev(self.apply_A, x0, t, _Cfg())

    @staticmethod
    def mse(a: np.ndarray, b: np.ndarray) -> float:
        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        if a.shape != b.shape:
            raise ValueError("Shape mismatch for MSE")
        d = a - b
        return float(np.mean(d * d))

    def error_and_confidence(
        self, salience: np.ndarray, observed: np.ndarray
    ) -> Tuple[float, float]:
        err = self.mse(salience, observed)
        conf = float(np.exp(-self.cfg.alpha * max(0.0, err)))
        return err, conf


class HeatDiffusionPredictor(PredictorBase):
    """A minimal concrete predictor using heat diffusion.

    It expects callers to supply a one-hot source vector and an observed vector.
    """

    def step(
        self, source_idx: int, observed: np.ndarray
    ) -> Tuple[np.ndarray, float, float]:
        x0 = np.zeros(self.dim, dtype=float)
        x0[max(0, min(self.dim - 1, int(source_idx)))] = 1.0
        y = self.salience(x0)
        err, conf = self.error_and_confidence(y, observed)
        return y, err, conf


def make_line_graph_laplacian(n: int) -> np.ndarray:
    """Simple n-node path graph Laplacian for demo/testing.

    L = D - A where A has 1 on (i,i+1) and (i+1,i)
    """
    n = int(n)
    L = np.zeros((n, n), dtype=float)
    for i in range(n):
        if i > 0:
            L[i, i - 1] = -1.0
        if i < n - 1:
            L[i, i + 1] = -1.0
    for i in range(n):
        deg = 0
        if i > 0:
            deg += 1
        if i < n - 1:
            deg += 1
        L[i, i] = float(deg)
    return L


def matvec_from_matrix(M: np.ndarray) -> ApplyOp:
    def _apply(v: np.ndarray) -> np.ndarray:
        return M @ v

    return _apply


def _to_ndarray(obj: object) -> Optional[np.ndarray]:
    try:
        arr = np.array(obj, dtype=float)
        if arr.ndim == 2 and arr.shape[0] == arr.shape[1]:
            return arr
    except Exception:
        return None
    return None


def _laplacian_from_adjacency(A: np.ndarray) -> np.ndarray:
    # L = D - A
    deg = np.sum(A, axis=1)
    L = np.diag(deg) - A
    return L


def load_operator_from_file(path: str) -> Tuple[ApplyOp, int]:
    """Load a graph operator from a JSON file.

    Supported formats:
    - A 2D array interpreted as adjacency (A); we build Laplacian L=D-A
    - An object {"adjacency": [[...]]}
    - An object {"laplacian": [[...]]}
    - An object {"type": "adjacency"|"laplacian", "matrix": [[...]]}

    Returns (apply_A, dim) where apply_A applies the Laplacian to a vector.
    """
    with open(path, "r") as f:
        data = json.load(f)
    L: Optional[np.ndarray] = None
    A: Optional[np.ndarray] = None
    if isinstance(data, dict):
        # Prefer explicit keys
        if "laplacian" in data:
            L = _to_ndarray(data.get("laplacian"))
        if L is None and "adjacency" in data:
            A = _to_ndarray(data.get("adjacency"))
        if L is None and ("matrix" in data):
            M = _to_ndarray(data.get("matrix"))
            ty = (
                str(data.get("type" or "")).strip().lower()
                if isinstance(data.get("type"), str)
                else ""
            )
            if isinstance(M, np.ndarray):
                if ty == "laplacian":
                    L = M
                else:
                    A = M
    if L is None and A is None:
        # Try bare 2D array
        A = _to_ndarray(data)
    if L is None and isinstance(A, np.ndarray):
        L = _laplacian_from_adjacency(A)
    if not isinstance(L, np.ndarray):
        raise ValueError(f"Could not load graph operator from file: {path}")
    dim = int(L.shape[0])
    return matvec_from_matrix(L), dim


def build_predictor_from_env(domain: str) -> Tuple["HeatDiffusionPredictor", int]:
    """Construct a HeatDiffusionPredictor using env configuration.

    Env vars consulted (domain-specific preferred):
    - SOMABRAIN_GRAPH_FILE_{DOMAIN}: path to JSON graph file
    - SOMABRAIN_GRAPH_FILE: default path if domain-specific not provided
    - SOMABRAIN_PREDICTOR_DIM: used only when no graph file provided
    - SOMABRAIN_DIFFUSION_T, SOMABRAIN_CONF_ALPHA, SOMABRAIN_CHEB_K, SOMABRAIN_LANCZOS_M
    """
    dom = (domain or "").strip().upper()
    # Graph source
    graph_path = settings.getenv(f"SOMABRAIN_GRAPH_FILE_{dom}") or settings.getenv(
        "SOMABRAIN_GRAPH_FILE"
    )
    if graph_path:
        try:
            apply_A, dim = load_operator_from_file(graph_path)
        except Exception:
            # Use line graph if load fails
            dim = int(settings.predictor_dim or "16")
            L = make_line_graph_laplacian(dim)
            apply_A = matvec_from_matrix(L)
    else:
        dim = int(settings.predictor_dim or "16")
        L = make_line_graph_laplacian(dim)
        apply_A = matvec_from_matrix(L)
    pred = HeatDiffusionPredictor(
        apply_A=apply_A,
        dim=dim,
        cfg=PredictorConfig(
            diffusion_t=float(settings.diffusion_t or "0.5"),
            alpha=float(settings.conf_alpha or "2.0"),
            chebyshev_K=int(settings.cheb_k or "30"),
            lanczos_m=int(settings.getenv("SOMABRAIN_LANCZOS_M", "20") or "20"),
        ),
    )
    return pred, dim
