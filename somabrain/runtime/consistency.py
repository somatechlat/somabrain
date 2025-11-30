"""Consistency checking utilities under runtime namespace."""

from __future__ import annotations

from typing import Dict
import numpy as np
import math


class ConsistencyChecker:
    """Compute Jensen-Shannon divergence and kappa consistency measure.

    kappa = 1 - JSD_norm, where JSD_norm = JSD / log(K), K = support size.
    """

def __init__(self, threshold: float = 0.8) -> None:
        self.threshold = float(threshold)

def js_divergence(self, p: np.ndarray, q: np.ndarray) -> float:
        P = self._as_prob(p)
        Q = self._as_prob(q)
        M = 0.5 * (P + Q)
        return 0.5 * (self._kl_div(P, M) + self._kl_div(Q, M))

def calculate_kappa(self, p: np.ndarray, q: np.ndarray) -> float:
        jsd = self.js_divergence(p, q)
        k = int(max(len(p.reshape(-1)), 2))
        denom = math.log(k)
        jsd_norm = jsd / denom if denom > 0 else 0.0
        kappa = 1.0 - jsd_norm
        return float(max(0.0, min(1.0, kappa)))

def is_consistent(self, p: np.ndarray, q: np.ndarray) -> bool:
        return self.calculate_kappa(p, q) >= self.threshold

def generate_consistency_report(
        self, distributions: Dict[str, np.ndarray]
    ) -> Dict[str, object]:
        keys = list(distributions.keys())
        pairwise: Dict[str, float] = {}
        kappas = []
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = keys[i], keys[j]
                kappa = self.calculate_kappa(distributions[a], distributions[b])
                pairwise[f"{a}|{b}"] = kappa
                kappas.append(kappa)
        overall = float(np.mean(kappas)) if kappas else 1.0
        return {"pairwise_kappa": pairwise, "overall_consistency": overall}

    # --- helpers ---
def _as_prob(self, x: np.ndarray) -> np.ndarray:
        v = np.asarray(x, dtype=float).reshape(-1)
        v = np.clip(v, 1e-12, None)
        s = float(v.sum())
        return v / s if s > 0 else np.full_like(v, 1.0 / max(v.size, 1))

def _kl_div(self, p: np.ndarray, q: np.ndarray) -> float:
        p = np.clip(p, 1e-12, None)
        q = np.clip(q, 1e-12, None)
        return float(np.sum(p * (np.log(p) - np.log(q))))
