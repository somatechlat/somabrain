"""
Prediction Module for SomaBrain.

This module provides various prediction and error calculation capabilities for the
SomaBrain system. It includes multiple predictor implementations ranging from simple
cosine similarity to sophisticated anomaly detection and LLM-based prediction.

Key Features:
- Multiple predictor implementations (budgeted, Mahalanobis, LLM)
- Error calculation using cosine similarity and statistical methods
- Time-bounded prediction with timeout handling
- Asynchronous prediction support
- Online learning for statistical predictors

Predictor Types:
- SlowPredictor: Test predictor with configurable latency
- BudgetedPredictor: Time-bounded wrapper for any predictor
- MahalanobisPredictor: Statistical anomaly detection using online mean/variance
- LLMPredictor: LLM-based prediction with HTTP endpoint integration

Error Metrics:
- Cosine error: 1 - cosine_similarity (bounded [0,1])
- Mahalanobis distance: Statistical distance normalized to [0,1]
- Combined error: Weighted blend of multiple error metrics

Classes:
    PredictionResult: Container for prediction results and error metrics.
    BasePredictor: Protocol defining the predictor interface.
    SlowPredictor: Test predictor with configurable delay.
    BudgetedPredictor: Time-bounded predictor wrapper.
    MahalanobisPredictor: Statistical anomaly detector.
    LLMPredictor: LLM-based predictor with HTTP integration.
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Optional, Protocol

import numpy as np

from somabrain.math import cosine_error as _canonical_cosine_error


@dataclass
class PredictionResult:
    """
    Container for prediction results and error metrics.

    Stores the predicted vector, actual vector, and computed error metric
    for a single prediction comparison.

    Attributes:
        predicted_vec (np.ndarray): The vector predicted by the predictor.
        actual_vec (np.ndarray): The actual observed vector.
        error (float): Error metric bounded in [0,1], where 0 indicates
            perfect prediction and 1 indicates maximum error.
    """

    predicted_vec: np.ndarray
    actual_vec: np.ndarray
    error: float  # bounded [0,1]


class BasePredictor(Protocol):
    """
    Protocol defining the interface for all predictors.

    Any predictor implementation must provide a predict_and_compare method
    that takes expected and actual vectors and returns a PredictionResult.
    """

    def predict_and_compare(
        self, expected_vec: np.ndarray, actual_vec: np.ndarray
    ) -> PredictionResult:
        """
        Predict and compare vectors to compute error.

        Args:
            expected_vec (np.ndarray): Expected/input vector for prediction.
            actual_vec (np.ndarray): Actual/observed vector for comparison.

        Returns:
            PredictionResult: Prediction result with error metric.
        """
        ...


def cosine_error(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine error between two vectors.

    Delegates to canonical implementation in somabrain.math.similarity.
    """
    return _canonical_cosine_error(a, b)


class SlowPredictor:
    """
    Test predictor that simulates latency for testing timeout behavior.

    Applies a configurable delay and then computes a cosine-error baseline
    to simulate slow prediction services. Useful for testing timeout
    handling and performance under load.

    Attributes:
        delay_ms (int): Delay in milliseconds before making prediction.
    """

    def __init__(self, delay_ms: int | None = None):
        """
        Initialize slow predictor with delay.

        Args:
            delay_ms (int): Delay in milliseconds. Default read from settings.
        """
        from django.conf import settings

        default_delay = getattr(settings, "SOMABRAIN_SLOW_PREDICTOR_DELAY_MS", 1000)
        self.delay_ms = int(default_delay if delay_ms is None else delay_ms)

    def predict_and_compare(
        self, expected_vec: np.ndarray, actual_vec: np.ndarray
    ) -> PredictionResult:
        """
        Make prediction after delay.

        Sleeps for the configured delay, then computes cosine error
        between the expected and actual vectors.

        Args:
            expected_vec (np.ndarray): Expected vector.
            actual_vec (np.ndarray): Actual vector.

        Returns:
            PredictionResult: Prediction result after delay.
        """
        time.sleep(self.delay_ms / 1000.0)
        predicted = expected_vec
        err = cosine_error(predicted, actual_vec)
        return PredictionResult(
            predicted_vec=predicted, actual_vec=actual_vec, error=err
        )


class BudgetedPredictor:
    """
    Time-bounded predictor wrapper with timeout enforcement.

    Wraps any predictor and enforces a time budget using threading.
    Raises TimeoutError if the prediction exceeds the timeout.

    Attributes:
        inner (BasePredictor): The wrapped predictor.
        timeout_ms (int): Timeout in milliseconds.
    """

    def __init__(self, inner: BasePredictor, timeout_ms: int | None = None):
        """
        Initialize budgeted predictor.

        Args:
            inner (BasePredictor): Predictor to wrap with timeout.
            timeout_ms (int): Timeout in milliseconds. Default: 250
        """
        from django.conf import settings

        self.inner = inner
        default_timeout = getattr(settings, "SOMABRAIN_PREDICTOR_TIMEOUT_MS", 1000)
        self.timeout_ms = int(default_timeout if timeout_ms is None else timeout_ms)

    def predict_and_compare(
        self, expected_vec: np.ndarray, actual_vec: np.ndarray
    ) -> PredictionResult:
        """
        Make prediction with timeout enforcement.

        Runs the inner predictor in a separate thread and waits for completion
        within the timeout. Raises TimeoutError if exceeded.

        Args:
            expected_vec (np.ndarray): Expected vector.
            actual_vec (np.ndarray): Actual vector.

        Returns:
            PredictionResult: Result from inner predictor.

        Raises:
            TimeoutError: If prediction exceeds timeout.
            Exception: Any exception raised by inner predictor.
        """
        result: Optional[PredictionResult] = None
        exc: Optional[BaseException] = None

        def _run():
            nonlocal result, exc
            try:
                result = self.inner.predict_and_compare(expected_vec, actual_vec)
            except BaseException as e:
                exc = e

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(self.timeout_ms / 1000.0)
        if t.is_alive():
            raise TimeoutError("predictor timed out")
        if exc is not None:
            raise exc
        if result is None:
            raise RuntimeError("predictor returned None result unexpectedly")
        return result

    async def apredict_and_compare(
        self, expected_vec: np.ndarray, actual_vec: np.ndarray
    ) -> PredictionResult:
        """
        Async wrapper for predict_and_compare with same timeout.

        Provides asynchronous interface while maintaining the same timeout behavior.

        Args:
            expected_vec (np.ndarray): Expected vector.
            actual_vec (np.ndarray): Actual vector.

        Returns:
            PredictionResult: Result from inner predictor.

        Raises:
            TimeoutError: If prediction exceeds timeout.
        """
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(
                    None, self.predict_and_compare, expected_vec, actual_vec
                ),
                timeout=self.timeout_ms / 1000.0,
            )
        except asyncio.TimeoutError as e:
            raise TimeoutError("predictor timed out") from e


class MahalanobisPredictor:
    """
    Statistical anomaly predictor using online Mahalanobis distance.

    Tracks online mean and variance of input vectors and computes a bounded
    Mahalanobis-like distance as an error metric. This provides a distributional
    surprise signal that complements cosine similarity.

    The predictor is model-free and CPU-friendly, making it suitable for
    real-time anomaly detection.

    Attributes:
        alpha (float): Learning rate for online statistics update.
        _mean (Optional[np.ndarray]): Online mean vector.
        _var (Optional[np.ndarray]): Online variance vector (diagonal).
    """

    def __init__(self, alpha: float = 0.01):
        """
        Initialize Mahalanobis predictor.

        Args:
            alpha (float): Learning rate for EWMA updates. Default: 0.01
        """
        self.alpha = float(alpha)
        self._mean: Optional[np.ndarray] = None
        self._var: Optional[np.ndarray] = None  # diagonal variance

    def _update_stats(self, x: np.ndarray) -> None:
        """
        Update online mean and variance statistics.

        Uses exponentially weighted moving averages to update the distribution
        parameters based on the input vector.

        Args:
            x (np.ndarray): Input vector for statistics update.
        """
        if self._mean is None or self._var is None:
            self._mean = x.astype("float32")
            self._var = np.ones_like(self._mean, dtype="float32") * 1e-1
            return
        a = self.alpha
        mu = self._mean
        var = self._var
        # EWMA updates
        mu_new = (1 - a) * mu + a * x
        diff = x - mu_new
        var_new = (1 - a) * var + a * (diff * diff)
        self._mean = mu_new.astype("float32")
        self._var = np.maximum(var_new.astype("float32"), 1e-6)

    def _mahal_bounded(self, x: np.ndarray) -> float:
        """
        Compute bounded Mahalanobis distance.

        Calculates the Mahalanobis distance and normalizes it to [0,1]
        using a smooth saturation function.

        Args:
            x (np.ndarray): Vector to compute distance for.

        Returns:
            float: Bounded Mahalanobis distance in [0,1].
        """
        if self._mean is None or self._var is None:
            return 0.0
        diff = x - self._mean
        d2 = float(np.sum((diff * diff) / self._var))
        dim = float(len(x)) or 1.0
        # map to [0,1] smoothly; saturates for large distances
        return float(d2 / (d2 + dim))

    def predict_and_compare(
        self, expected_vec: np.ndarray, actual_vec: np.ndarray
    ) -> PredictionResult:
        """
        Predict and compute combined error metric.

        Updates statistics with expected vector, then computes error on actual
        vector using a blend of cosine similarity and Mahalanobis distance.

        Args:
            expected_vec (np.ndarray): Expected vector (used for statistics update).
            actual_vec (np.ndarray): Actual vector for error calculation.

        Returns:
            PredictionResult: Result with expected vector as prediction and
                combined error metric.
        """
        # Use expected_vec to update distribution; compute surprise on actual
        x = expected_vec.astype("float32")
        self._update_stats(x)
        # Combine cosine residual to actual with bounded Mahalanobis surprise
        cos_err = cosine_error(expected_vec, actual_vec)
        surprise = self._mahal_bounded(actual_vec.astype("float32"))
        # Small blend to avoid large behavior change; can tune later
        err = float(min(1.0, max(0.0, 0.8 * cos_err + 0.2 * surprise)))
        return PredictionResult(
            predicted_vec=expected_vec, actual_vec=actual_vec, error=err
        )


class LLMPredictor:
    """
    LLM-based predictor with HTTP endpoint integration.

    Makes HTTP calls to a configured LLM endpoint to get prediction adjustments.
    Falls back to cosine error when endpoint is unavailable or fails.

    Attributes:
        endpoint (Optional[str]): HTTP endpoint URL for LLM service.
        token (Optional[str]): Bearer token for authentication.
        timeout_ms (int): Request timeout in milliseconds.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        token: Optional[str] = None,
        timeout_ms: int = 250,
    ):
        """
        Initialize LLM predictor.

        Args:
            endpoint (Optional[str]): LLM service endpoint URL.
            token (Optional[str]): Authentication token.
            timeout_ms (int): Request timeout in milliseconds. Default: 250
        """
        self.endpoint = endpoint
        self.token = token
        self.timeout_ms = int(timeout_ms)

    def predict_and_compare(
        self, expected_vec: np.ndarray, actual_vec: np.ndarray
    ) -> PredictionResult:
        """
        Make LLM-based prediction with alternative.

        Computes base cosine error, then attempts to get adjustment from LLM
        endpoint. Falls back to base error if endpoint unavailable.

        Args:
            expected_vec (np.ndarray): Expected vector.
            actual_vec (np.ndarray): Actual vector.

        Returns:
            PredictionResult: Result with LLM-adjusted error or alternative.
        """
        base_err = cosine_error(expected_vec, actual_vec)
        if not self.endpoint:
            return PredictionResult(
                predicted_vec=expected_vec, actual_vec=actual_vec, error=base_err
            )
        try:
            import httpx

            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            with httpx.Client(timeout=self.timeout_ms / 1000.0) as client:
                r = client.post(
                    self.endpoint, json={"signal": float(base_err)}, headers=headers
                )
                data = r.json() if r.status_code == 200 else {}
                adj = (
                    float(data.get("error", base_err))
                    if isinstance(data, dict)
                    else base_err
                )
                err = max(0.0, min(1.0, adj))
                return PredictionResult(
                    predicted_vec=expected_vec, actual_vec=actual_vec, error=err
                )
        except Exception:
            return PredictionResult(
                predicted_vec=expected_vec, actual_vec=actual_vec, error=base_err
            )
