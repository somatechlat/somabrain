"""
Statistics Module for SomaBrain.

This module provides statistical utilities and data structures for monitoring and analyzing
system performance metrics. It includes implementations of exponentially weighted moving
averages and related statistical computations for real-time performance tracking.

Key Features:
- Exponentially Weighted Moving Average (EWMA) for smooth statistics
- Online variance and standard deviation calculation
- Z-score computation for anomaly detection
- Memory-efficient incremental updates

Classes:
    EWMA: Exponentially weighted moving average calculator with variance tracking.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EWMA:
    """
    Exponentially Weighted Moving Average calculator with variance tracking.

    This class implements an online algorithm for computing exponentially weighted
    moving averages, variance, and standard deviation. It provides efficient
    incremental updates suitable for real-time monitoring and anomaly detection.

    The EWMA gives more weight to recent observations while maintaining a running
    estimate of the mean and variance. Z-scores are computed for outlier detection.

    Attributes:
        alpha (float): Smoothing factor (0 < alpha <= 1). Lower values give more weight to history.
        mean (float): Current EWMA mean estimate.
        m2 (float): Running sum of squared differences for variance calculation.
        n (int): Number of observations processed.

    Example:
        >>> ewma = EWMA(alpha=0.1)
        >>> stats = ewma.update(10.5)
        >>> print(f"Mean: {stats['mean']:.2f}, Z-score: {stats['z']:.2f}")
    """

    alpha: float = 0.05
    mean: float = 0.0
    m2: float = 0.0
    n: int = 0

    def update(self, x: float) -> dict:
        """
        Update the EWMA with a new observation and return current statistics.

        Incrementally updates the exponentially weighted mean and variance estimates
        using the new observation. Returns a dictionary containing the current mean,
        variance, standard deviation, and z-score for the input value.

        Args:
            x (float): New observation to incorporate into the statistics.

        Returns:
            dict: Dictionary containing:
                - "mean": Current EWMA mean
                - "var": Current variance estimate (minimum 1e-6)
                - "std": Standard deviation (sqrt of variance)
                - "z": Z-score of the input value relative to current distribution

        Note:
            For the first observation (n=1), variance is set to 0.
            Variance is clamped to a minimum of 1e-6 to avoid division by zero.
        """
        x = float(x)
        self.n += 1
        # EWMA mean
        if self.n == 1:
            self.mean = x
            self.m2 = 0.0
        else:
            delta = x - self.mean
            self.mean += self.alpha * delta
            # EWMA variance approximation
            self.m2 = (1 - self.alpha) * (self.m2 + self.alpha * delta * delta)
        var = max(1e-6, self.m2)
        std = var**0.5
        z = (x - self.mean) / std
        return {"mean": self.mean, "var": var, "std": std, "z": z}
