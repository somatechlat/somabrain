> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# Golden Datasets

This directory stores golden truth samples used by regression and integration tests. Datasets must reflect **real** service interactions—no mocks, no synthetic fill-ins. When updating, regenerate from production-like runs and recompute checksums.

## Files

| File | Description | SHA256 |
| --- | --- | --- |
| `memories.jsonl` | Canonical episodic memory samples captured from the live memory endpoint. | `8ca145c78cc8f414674a92ded255636b732a46d1542d1771aa518d7b4da70459` |

## Update Procedure

1. Run the live stack (docker-compose, Kind, or shared infra) with strict-real mode enabled and confirm the external memory endpoint is reachable.
2. Export dataset via approved script (see `scripts/data/capture_memory_golden.py`).
3. Overwrite the JSONL file and recompute SHA256: `shasum -a 256 memories.jsonl`.
4. Update the checksum table above and commit both changes together.

## Usage

Tests import these datasets via path helpers in `tests/support/golden_data.py`. Keep usage read-only and deterministic.
