# Context API Reference: Payload Size Enforcement

## Overview
This document describes the payload size and length constraints enforced by the SomaBrain context API endpoints (`/context/evaluate` and `/context/feedback`). These constraints ensure that API responses remain within safe, predictable bounds for agent-side SLM consumption and system performance.

## Evaluate Endpoint (`/context/evaluate`)
- **Max memories returned:** 20
- **Max prompt length:** 4096 characters
- **Max residual vector length:** 2048 floats
- **Max working memory items:** 10
- **Max response size:** 128 KB (JSON-encoded)

## Feedback Endpoint (`/context/feedback`)
- **Max session_id/query/prompt/response_text length:** 1024 characters each
- **Max metadata size:** 8 KB (JSON-encoded)

## Enforcement
- Requests or responses exceeding these limits will return HTTP 400 with a descriptive error message.
- All limits are enforced in the FastAPI route handlers before returning a response.

## Example Error
```json
{
  "detail": "prompt length exceeds 4096 characters"
}
```

## Rationale
- These limits are designed to prevent abuse, ensure agent compatibility, and maintain low-latency operation at scale.
- Limits may be adjusted in future releases based on observed usage and performance data.

---
_Last updated: 2025-09-26_
