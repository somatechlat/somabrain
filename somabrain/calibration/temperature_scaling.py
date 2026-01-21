"""
Temperature scaling for predictor calibration.

Implements Platt scaling and temperature scaling for confidence calibration.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np


@dataclass
class CalibrationResult:
    """Container for calibration results."""

    temperature: float
    ece: float
    brier_score: float
    reliability_diagram: List[Tuple[float, float, int]]


class TemperatureScaler:
    """Temperature scaling for confidence calibration."""

    def __init__(self, min_samples: int = 50):
        """Initialize the instance."""

        self.min_samples = min_samples
        self.temperature = 1.0
        self.is_fitted = False

    def fit(self, confidences: List[float], accuracies: List[float]) -> float:
        """
        Fit temperature using bounded NLL minimization (golden-section).

        Args:
            confidences: Predicted confidences (0-1)
            accuracies: Actual accuracies (0-1)

        Returns:
            Optimal temperature parameter
        """
        if len(confidences) < self.min_samples:
            return 1.0

        p = np.clip(np.asarray(confidences, dtype=float), 1e-8, 1 - 1e-8)
        y = np.asarray(accuracies, dtype=float)

        logits = np.log(p / (1 - p))

        def nll(temp: float) -> float:
            """Execute nll.

            Args:
                temp: The temp.
            """

            t = max(1e-6, float(temp))
            z = logits / t
            # Numerically stable sigmoid
            probs = 1.0 / (1.0 + np.exp(-z))
            probs = np.clip(probs, 1e-8, 1 - 1e-8)
            return -float(np.mean(y * np.log(probs) + (1 - y) * np.log(1 - probs)))

        # Golden-section search in [a, b]
        a, b = 0.1, 5.0
        phi = (5**0.5 - 1) / 2  # ~0.618
        c = b - phi * (b - a)
        d = a + phi * (b - a)
        fc = nll(c)
        fd = nll(d)
        tol = 1e-4
        for _ in range(80):
            if abs(b - a) < tol:
                break
            if fc < fd:
                b, d, fd = d, c, fc
                c = b - phi * (b - a)
                fc = nll(c)
            else:
                a, c, fc = c, d, fd
                d = a + phi * (b - a)
                fd = nll(d)
        # Choose best of bracket endpoints and interior points
        cand = [(a, nll(a)), (b, nll(b)), (c, fc), (d, fd), (1.0, nll(1.0))]
        best_temp, _ = min(cand, key=lambda kv: kv[1])

        self.temperature = float(max(0.05, min(10.0, best_temp)))
        self.is_fitted = True
        return self.temperature

    def scale(self, confidence: float) -> float:
        """Apply temperature scaling to confidence."""
        if not self.is_fitted or confidence <= 0 or confidence >= 1:
            return confidence

        logit = math.log(confidence / (1 - confidence + 1e-10))
        scaled_logit = logit / self.temperature
        return 1 / (1 + math.exp(-scaled_logit))


def compute_ece(
    confidences: List[float], accuracies: List[float], n_bins: int = 10
) -> float:
    """
    Compute Expected Calibration Error (ECE).

    Args:
        confidences: Predicted confidences
        accuracies: Actual accuracies
        n_bins: Number of bins for reliability diagram

    Returns:
        ECE value (0-1)
    """
    if len(confidences) < 10:
        return 0.0

    confidences = np.array(confidences)
    accuracies = np.array(accuracies)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    total_samples = len(confidences)

    for i in range(n_bins):
        lower, upper = bin_boundaries[i], bin_boundaries[i + 1]
        mask = (confidences >= lower) & (confidences < upper)

        if upper == 1.0:  # Include the last boundary
            mask = mask | (confidences == 1.0)

        bin_size = np.sum(mask)
        if bin_size == 0:
            continue

        bin_confidence = np.mean(confidences[mask])
        bin_accuracy = np.mean(accuracies[mask])
        bin_weight = bin_size / total_samples

        ece += bin_weight * abs(bin_confidence - bin_accuracy)

    return ece


def compute_brier_score(confidences: List[float], accuracies: List[float]) -> float:
    """
    Compute Brier score for calibration.

    Args:
        confidences: Predicted confidences
        accuracies: Actual accuracies

    Returns:
        Brier score (0-1, lower is better)
    """
    if len(confidences) == 0:
        return 0.0

    confidences = np.array(confidences)
    accuracies = np.array(accuracies)

    return np.mean((confidences - accuracies) ** 2)


def reliability_diagram(
    confidences: List[float], accuracies: List[float], n_bins: int = 10
) -> List[Tuple[float, float, int]]:
    """
    Generate data for reliability diagram.

    Returns:
        List of (bin_confidence, bin_accuracy, bin_count) tuples
    """
    if len(confidences) == 0:
        return []

    confidences = np.array(confidences)
    accuracies = np.array(accuracies)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    diagram = []

    for i in range(n_bins):
        lower, upper = bin_boundaries[i], bin_boundaries[i + 1]
        mask = (confidences >= lower) & (confidences < upper)

        if upper == 1.0:
            mask = mask | (confidences == 1.0)

        bin_size = np.sum(mask)
        if bin_size == 0:
            diagram.append((lower + (upper - lower) / 2, 0.0, 0))
        else:
            bin_confidence = np.mean(confidences[mask])
            bin_accuracy = np.mean(accuracies[mask])
            diagram.append((bin_confidence, bin_accuracy, int(bin_size)))

    return diagram
