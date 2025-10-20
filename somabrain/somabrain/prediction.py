from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional
import asyncio
import threading
import time
import numpy as np


@dataclass
class PredictionResult:
    predicted_vec: np.ndarray
    actual_vec: np.ndarray
    error: float  # bounded [0,1]


class BasePredictor(Protocol):
    def predict_and_compare(self, expected_vec: np.ndarray, actual_vec: np.ndarray) -> PredictionResult: ...


class StubPredictor:
    def __init__(self):
        pass

    @staticmethod
    def error_cosine(a: np.ndarray, b: np.ndarray) -> float:
        na = float(np.linalg.norm(a))
        nb = float(np.linalg.norm(b))
        if na <= 0 or nb <= 0:
            return 1.0
        sim = float(np.dot(a, b) / (na * nb))
        return float(max(0.0, 1.0 - sim))

    def predict_and_compare(self, expected_vec: np.ndarray, actual_vec: np.ndarray) -> PredictionResult:
        # For MVP, the predictor just echoes the expected vector
        predicted = expected_vec
        err = self.error_cosine(predicted, actual_vec)
        return PredictionResult(predicted_vec=predicted, actual_vec=actual_vec, error=err)


class SlowPredictor:
    """Test-only predictor that sleeps to simulate latency."""

    def __init__(self, delay_ms: int = 1000):
        self.delay_ms = int(delay_ms)

    def predict_and_compare(self, expected_vec: np.ndarray, actual_vec: np.ndarray) -> PredictionResult:
        time.sleep(self.delay_ms / 1000.0)
        predicted = expected_vec
        err = StubPredictor.error_cosine(predicted, actual_vec)
        return PredictionResult(predicted_vec=predicted, actual_vec=actual_vec, error=err)


class BudgetedPredictor:
    """Wraps a predictor and enforces a time budget; raises TimeoutError on exceed."""

    def __init__(self, inner: BasePredictor, timeout_ms: int = 250):
        self.inner = inner
        self.timeout_ms = int(timeout_ms)

    def predict_and_compare(self, expected_vec: np.ndarray, actual_vec: np.ndarray) -> PredictionResult:
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
        assert result is not None
        return result

    async def apredict_and_compare(self, expected_vec: np.ndarray, actual_vec: np.ndarray) -> PredictionResult:
        """Async wrapper around predict_and_compare with the same budget."""
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(loop.run_in_executor(None, self.predict_and_compare, expected_vec, actual_vec), timeout=self.timeout_ms / 1000.0)
        except asyncio.TimeoutError as e:
            raise TimeoutError("predictor timed out") from e


class MahalanobisPredictor:
    """Lightweight anomaly predictor: tracks online mean/variance of vectors and
    reports a bounded Mahalanobis-like distance as error (in [0,1]).

    This is model-free and CPU-friendly. It complements cosine residuals by
    providing a distributional surprise signal.
    """

    def __init__(self, alpha: float = 0.01):
        self.alpha = float(alpha)
        self._mean: Optional[np.ndarray] = None
        self._var: Optional[np.ndarray] = None  # diagonal variance

    def _update_stats(self, x: np.ndarray) -> None:
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
        if self._mean is None or self._var is None:
            return 0.0
        diff = x - self._mean
        d2 = float(np.sum((diff * diff) / self._var))
        dim = float(len(x)) or 1.0
        # map to [0,1] smoothly; saturates for large distances
        return float(d2 / (d2 + dim))

    def predict_and_compare(self, expected_vec: np.ndarray, actual_vec: np.ndarray) -> PredictionResult:
        # Use expected_vec to update distribution; compute surprise on actual
        x = expected_vec.astype("float32")
        self._update_stats(x)
        # Combine cosine residual to actual with bounded Mahalanobis surprise
        cos_err = StubPredictor.error_cosine(expected_vec, actual_vec)
        surprise = self._mahal_bounded(actual_vec.astype("float32"))
        # Small blend to avoid large behavior change; can tune later
        err = float(min(1.0, max(0.0, 0.8 * cos_err + 0.2 * surprise)))
        return PredictionResult(predicted_vec=expected_vec, actual_vec=actual_vec, error=err)


class LLMPredictor:
    """Budgeted LLM predictor placeholder.

    Makes an HTTP call to a configured endpoint (if provided) and derives an
    error proxy from the response. When unavailable, degrades to cosine error.
    """

    def __init__(self, endpoint: Optional[str] = None, token: Optional[str] = None, timeout_ms: int = 250):
        self.endpoint = endpoint
        self.token = token
        self.timeout_ms = int(timeout_ms)

    def predict_and_compare(self, expected_vec: np.ndarray, actual_vec: np.ndarray) -> PredictionResult:
        base_err = StubPredictor.error_cosine(expected_vec, actual_vec)
        if not self.endpoint:
            return PredictionResult(predicted_vec=expected_vec, actual_vec=actual_vec, error=base_err)
        try:
            import httpx  # type: ignore
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            with httpx.Client(timeout=self.timeout_ms / 1000.0) as client:
                r = client.post(self.endpoint, json={"signal": float(base_err)}, headers=headers)
                data = r.json() if r.status_code == 200 else {}
                adj = float(data.get("error", base_err)) if isinstance(data, dict) else base_err
                err = max(0.0, min(1.0, adj))
                return PredictionResult(predicted_vec=expected_vec, actual_vec=actual_vec, error=err)
        except Exception:
            return PredictionResult(predicted_vec=expected_vec, actual_vec=actual_vec, error=base_err)
