SomaBrain — Index Profiles and Compression

Overview
- These settings are passed to the `somafractalmemory` vector backend when running in local mode. Backends may ignore unknown keys; they are forward‑compatible hints.

Profiles
- `index_profile`: low_latency | balanced | high_recall
  - Selects default parameters for IVF/IMI probes, HNSW efsearch, and PQ code size.

Quantization
- `pq_m` (int): number of sub‑quantizers (e.g., 8/16/32)
- `pq_bits` (int): bits per sub‑vector (e.g., 6/8)
- `opq_enabled` (bool): rotate space before PQ to reduce distortion
- `anisotropic_enabled` (bool): prefer MIPS‑oriented loss over plain L2 (ScaNN‑style)

Coarse + Graph
- `imi_cells` (int): number of IMI coarse cells to partition the space
- `hnsw_M` (int): HNSW graph out‑degree (typ. 16–32)
- `hnsw_efc` (int): efConstruction (build quality)
- `hnsw_efs` (int): efSearch (query recall)

JL Projection (frontend)
- Use `SOMABRAIN_EMBED_DIM_TARGET_K` to project embeddings to a smaller k before indexing (Johnson–Lindenstrauss). This reduces RAM and speeds dot‑products while preserving neighborhoods.

HRR‑first Rerank (frontend)
- With `SOMABRAIN_USE_HRR_FIRST=true`, the system blends HRR similarity into ranking. On LTM payloads without scores, it uses HRR cosine to rerank as a best‑effort.

Notes
- In HTTP mode, these hints are not sent to remote backends; configure the remote service separately.
- Start with `balanced` and adjust `pq_m/pq_bits` using a rate–distortion sweep; increase `hnsw_efs` only for hard queries (adaptive efSearch).

