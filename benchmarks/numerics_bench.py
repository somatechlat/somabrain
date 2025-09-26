"""Microbenchmarks for numerics: per-call vs batched normalize and rfft.

Run inside the project's .venv.
"""

import time

import numpy as np

from somabrain import batch as batch, numerics as num


def bench_normalize(D=2048, N=1000):
    x = np.random.randn(N, D).astype(np.float32)
    # per-call
    t0 = time.time()
    for i in range(N):
        _ = num.normalize_array(x[i], axis=-1, keepdims=False)
    t_per = time.time() - t0

    # batched: single call
    t0 = time.time()
    _ = num.normalize_array(x, axis=-1, keepdims=False)
    t_batch = time.time() - t0

    print(f"D={D} N={N}: per-call {t_per:.4f}s, batched {t_batch:.4f}s")


def bench_rfft(D=2048, N=1000):
    x = np.random.randn(N, D).astype(np.float32)
    t0 = time.time()
    for i in range(N):
        _ = num.rfft_norm(x[i], axis=-1)
    t_per = time.time() - t0

    t0 = time.time()
    _ = num.rfft_norm(x, axis=-1)
    t_batch = time.time() - t0

    print(f"rfft D={D} N={N}: per-call {t_per:.4f}s, batched {t_batch:.4f}s")


if __name__ == "__main__":
    bench_normalize(D=2048, N=500)
    bench_rfft(D=2048, N=500)
