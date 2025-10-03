Agent Integration Guide
=======================

Overview
--------
This guide explains how to integrate SOMABRAIN with agents and automation
scripts.

Key operations
--------------

- Persist agent outputs: ``POST /remember`` with a JSON payload.
- Retrieve context: ``POST /recall`` with a query and optional ``top_k``.

Quick Python example
--------------------

.. code-block:: python

   import requests

   payload = {"coordinate": [1.0, 2.0, 3.0], "memory_type": "episodic"}
   r = requests.post('http://127.0.0.1:9696/remember', json=payload)
   print('remember', r.status_code, r.json())

   q = requests.post('http://127.0.0.1:9696/recall', json={'query': 'task', 'top_k': 3})
   print('recall', q.status_code, q.json())

Notes
-----

- For full API details, consult the API reference and module docs.

- Recall relevant memories for context or decision-making using the ``/recall`` endpoint.

- Use filters to retrieve memories by type, importance, or timestamp.

- Delete outdated or irrelevant memories with the appropriate API.

- Timestamps are returned as Unix epoch seconds (float). When sending data to
   ``/remember`` you can provide either epoch seconds or an ISO-8601 string; the
   service normalizes everything to epoch seconds before storage.

Runnable examples
-----------------

Python example using requests (assumes server at http://127.0.0.1:9696):

.. code-block:: python

   import requests

   payload = {
       "coordinate": [1.0, 2.0, 3.0],
       "memory_type": "episodic",
   }

   r = requests.post('http://127.0.0.1:9696/remember', json=payload)
   print('remember status', r.status_code, r.json())

   q = requests.post('http://127.0.0.1:9696/recall', json={'query': 'Agent completed task', 'top_k': 3})
   print('recall', q.status_code, q.json())

Notes on HRR math (concise)
---------------------------

1. Binding (circular convolution)

   - Let a, b in R^D be real vectors. Compute their real FFTs: A = rfft(a), B = rfft(b).
   - Binding: c = irfft(A * B) (elementwise multiply in frequency domain, inverse rfft back to time domain).

2. Unbinding (regularized deconvolution)

   - To recover a from c and b: C = rfft(c), B = rfft(b).
      - Elementwise: A_est = C * conj(B) / (:math:`|B|^2` + eps)
   - eps is dtype-aware: eps := max(cfg.fft_eps, dtype_floor), where dtype_floor = 1e-6 for float32 and 1e-12 for float64.
   - a_est = irfft(A_est)
   - Renormalize a_est to unit norm to preserve invariants.

3. Superposition and cleanup

   - Superpose by summing normalized anchors. After unbinding a noisy estimate, compute cosine similarity to anchor vectors and select top-k nearest anchors (cleanup).
   - Cleanup is required for robust recall when many items are superposed.

4. Numerical best-practices

   - Always use dtype-aware eps to avoid large amplification from small spectral bins.
   - Normalize vectors to unit norm after each HRR operation.
   - Prefer float64 for tight numeric tolerances; float32 is acceptable with a larger eps floor.

If desired, these examples can be copied into the README or API reference pages.
