from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


@dataclass
class HMMParams:
    """Parameters for a simple two-state HMM with Gaussian emissions.

    States are indexed as 0=STABLE, 1=TRANSITION.
    """

    # Transition probabilities A[i][j] = P(s_t=j | s_{t-1}=i)
    A: Tuple[Tuple[float, float], Tuple[float, float]]
    # Gaussian emission parameters per state (mean, std)
    mu: Tuple[float, float]
    sigma: Tuple[float, float]


def _log(x: float) -> float:
    return -1e12 if x <= 0.0 else math.log(x)


def _log_norm_pdf(x: float, mu: float, sigma: float) -> float:
    s = max(1e-6, float(sigma))
    z = (x - mu) / s
    return -0.5 * (z * z) - math.log(s) - 0.5 * math.log(2.0 * math.pi)


def online_viterbi_probs(
    obs_seq: Iterable[float],
    params: HMMParams,
    prior: Tuple[float, float] = (0.9, 0.1),
) -> List[Tuple[float, float]]:
    """Compute online Viterbi log-probabilities for a stream of observations.

    Returns a list of per-step normalized probabilities over states (stable, transition).
    """

    A = params.A
    mu0, mu1 = params.mu
    s0, s1 = params.sigma
    # start with log prior
    lp0 = _log(prior[0])
    lp1 = _log(prior[1])
    out: List[Tuple[float, float]] = []
    for x in obs_seq:
        # emission log-likelihood
        e0 = _log_norm_pdf(x, mu0, s0)
        e1 = _log_norm_pdf(x, mu1, s1)
        # transition + emission
        nlp0 = max(lp0 + _log(A[0][0]), lp1 + _log(A[1][0])) + e0
        nlp1 = max(lp0 + _log(A[0][1]), lp1 + _log(A[1][1])) + e1
        # normalize to probabilities to avoid drift
        m = max(nlp0, nlp1)
        p0 = math.exp(nlp0 - m)
        p1 = math.exp(nlp1 - m)
        Z = p0 + p1
        p0 /= Z
        p1 /= Z
        out.append((p0, p1))
        # carry forward in log-space
        lp0, lp1 = math.log(p0 + 1e-18), math.log(p1 + 1e-18)
    return out


def detect_boundaries(
    probs: Sequence[Tuple[float, float]],
    threshold: float = 0.6,
) -> List[int]:
    """Return indices where TRANSITION probability crosses threshold from below.

    threshold is applied to P(TRANSITION) (index 1).
    """

    out: List[int] = []
    prev = 0.0
    for i, (_, p1) in enumerate(probs):
        if prev < threshold and p1 >= threshold:
            out.append(i)
        prev = p1
    return out
