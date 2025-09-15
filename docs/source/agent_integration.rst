Agent Integration Guide
=======================

Overview
--------

SomaBrain integrates with agents, chatbots, and automation scripts to provide persistent, context-aware memory.

How to use
----------

- Store agent outputs, actions, and context as memories using the `/remember` endpoint.
- Recall relevant memories for context or decision-making using `/recall`.
- Use filters to retrieve memories by type, importance, or timestamp.
- Delete outdated or irrelevant memories with `/delete`.

Runnable examples
-----------------

Python example using requests (assumes server at http://127.0.0.1:9696):

.. code-block:: python

   import requests

   BASE = "http://127.0.0.1:9696"
   HEADERS = {"Content-Type": "application/json", "X-Tenant-ID": "public"}

   remember_payload = {
       "coordinate": [1.0, 2.0, 3.0],
       "memory_type": "episodic",
   }
   r = requests.post(f"{BASE}/remember", json=remember_payload, headers=HEADERS)
   print('remember status', r.status_code, r.json())

   q = requests.post(f"{BASE}/recall", json={"query": "Agent completed task", "top_k": 3}, headers=HEADERS)
   print('recall', q.status_code, q.json())

HRR math notes (concise)
------------------------

1. Binding (circular convolution)

   - Let a, b ∈ R^D be real vectors. Compute their real FFTs: A = rfft(a), B = rfft(b).
   - Binding: c = irfft(A * B) (elementwise multiply in frequency domain, inverse rfft back to time domain).

2. Unbinding (regularized deconvolution)

   - To recover a from c and b: C = rfft(c), B = rfft(b).
   - Elementwise: A_est = C * conj(B) / ``(|B|**2 + eps)``
   - eps is dtype-aware: eps := max(cfg.fft_eps, dtype_floor), where dtype_floor is chosen per-dtype (see ``somabrain/numerics.py``).
   - a_est = irfft(A_est)
   - Renormalize a_est to unit L2 norm to preserve invariants.

3. Superposition and cleanup

   - Superpose by summing normalized anchors. After unbinding a noisy estimate, compute cosine similarity to anchor vectors and select top-k nearest anchors (cleanup).
   - Cleanup is required for robust recall when many items are superposed.

4. Numerical best practices

   - Always use dtype-aware eps/floor to avoid large amplification from small spectral bins.
   - Convert tiny amplitude floors to per-bin power as: ``power_floor_per_bin = tiny_amp**2 / D`` when applied in spectral denominators.
   - Normalize vectors to unit L2 norm after each HRR operation.
   - Prefer float64 for tight numeric tolerances; float32 is acceptable with a larger eps floor.

If desired, these examples can be copied into the README or API reference pages.
