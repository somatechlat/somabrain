from __future__ import annotations

import json
from typing import Any, Dict, Optional

from somabrain.services.teach_feedback_processor import _r_user_from_rating, _enc, _dec


def test_r_user_from_rating_mapping():
    # Happy path mapping
    assert _r_user_from_rating(1) == -1.0
    assert _r_user_from_rating(2) == -0.5
    assert _r_user_from_rating(3) == 0.0
    assert _r_user_from_rating(4) == 0.5
    assert _r_user_from_rating(5) == 1.0

    # Out-of-range defaults to 0.0
    assert _r_user_from_rating(0) == 0.0
    assert _r_user_from_rating(6) == 0.0

    # Non-int input handled gracefully
    assert _r_user_from_rating("not-an-int") == 0.0


def test_enc_dec_json_fallback_roundtrip():
    # With serde=None, enc/dec should fall back to JSON bytes
    rec: Dict[str, Any] = {"frame_id": "abc", "r_user": 0.5, "total": 0.5}
    payload: bytes = _enc(rec, serde=None)  # type: ignore[arg-type]
    assert isinstance(payload, (bytes, bytearray))
    out: Optional[Dict[str, Any]] = _dec(payload, serde=None)  # type: ignore[arg-type]
    assert isinstance(out, dict)
    assert out["frame_id"] == "abc"
    assert out["total"] == 0.5
