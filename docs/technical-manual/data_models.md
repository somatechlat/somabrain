# Data Models

This document provides an overview of the data models used in the SomaBrain API, based on the Pydantic schemas defined in `somabrain/schemas.py`.

## Core Data Models

### `MemoryPayload`

Represents the structure of memory content stored in the system.

| Field | Type | Description |
|---|---|---|
| `task` | string | Associated task or context identifier. |
| `content` | string | The main content of the memory. |
| `importance` | integer | Importance score (higher values are more important). |
| `memory_type` | string | Type of memory (e.g., "episodic", "semantic"). |
| `timestamp` | float | Unix epoch seconds. |
| `universe` | string | Universe/namespace identifier. |
| `who` | string | Who performed the action. |
| `did` | string | What action was performed. |
| `what` | string | What was affected by the action. |
| `where` | string | Where the action occurred. |
| `when` | string | When the action occurred. |
| `why` | string | Why the action was performed. |

### `RecallRequest`

Schema for memory recall API requests.

| Field | Type | Description |
|---|---|---|
| `query` | string | Search query string for memory retrieval. |
| `top_k` | integer | Number of top similar memories to return. |
| `universe` | string | Optional universe/namespace filter for memories. |

### `RememberRequest`

Schema for memory storage requests.

| Field | Type | Description |
|---|---|---|
| `coord` | string | Optional 3D coordinate string "x,y,z" for memory placement. |
| `payload` | `MemoryPayload` | Memory content and metadata to store. |

## Neuromodulation

### `NeuromodStateModel`

Represents the current levels of key neuromodulators in the cognitive system.

| Field | Type | Description |
|---|---|---|
| `dopamine` | float | Dopamine level (0.0 to 1.0). |
| `serotonin` | float | Serotonin level (0.0 to 1.0). |
| `noradrenaline` | float | Noradrenaline level (0.0 to 1.0). |
| `acetylcholine` | float | Acetylcholine level (0.0 to 1.0). |

For a complete list of all data models and their fields, please refer to the `somabrain/schemas.py` file.
