from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EWMA:
    alpha: float = 0.05
    mean: float = 0.0
    m2: float = 0.0
    n: int = 0

    def update(self, x: float) -> dict:
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
        std = var ** 0.5
        z = (x - self.mean) / std
        return {"mean": self.mean, "var": var, "std": std, "z": z}

