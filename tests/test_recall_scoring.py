import time

from somabrain.app import _build_wm_support_index, _score_memory_candidate


def test_score_prefers_math_domain_payloads():
    query_lower = "master calculus integrals"
    query_tokens = ["master", "calculus", "integrals"]
    now_ts = time.time()

    math_payload = {
        "task": "Master calculus integrals with worked examples",
        "domains": ["math", "learning"],
        "quality_score": 0.9,
        "timestamp": now_ts - 30.0,
    }
    generic_payload = {
        "task": "Review generic study tips",
        "domains": ["study"],
        "quality_score": 0.4,
        "timestamp": now_ts - 3600.0,
    }

    wm_support = _build_wm_support_index([])
    hrr_cache: dict[str, object] = {}

    math_score = _score_memory_candidate(
        math_payload,
        query_lower=query_lower,
        query_tokens=query_tokens,
        wm_support=wm_support,
        now_ts=now_ts,
        quantum_layer=None,
        query_hrr=None,
        hrr_cache=hrr_cache,
    )
    generic_score = _score_memory_candidate(
        generic_payload,
        query_lower=query_lower,
        query_tokens=query_tokens,
        wm_support=wm_support,
        now_ts=now_ts,
        quantum_layer=None,
        query_hrr=None,
        hrr_cache=hrr_cache,
    )

    assert math_score > generic_score


def test_wm_support_signal_boosts_candidates():
    query_lower = "solve vector equations"
    query_tokens = ["solve", "vector", "equations"]
    now_ts = time.time()

    wm_hits = [
        (
            0.7,
            {
                "coordinate": (1.0, 2.0, 3.0),
            },
        )
    ]
    wm_support = _build_wm_support_index(wm_hits)
    hrr_cache: dict[str, object] = {}

    boosted_payload = {
        "task": "Solve vector equations for physics",
        "coordinate": (1.0, 2.0, 3.0),
        "timestamp": now_ts - 120.0,
    }
    baseline_payload = {
        "task": "Solve vector equations for physics",
        "coordinate": (3.0, 4.0, 5.0),
        "timestamp": now_ts - 120.0,
    }

    boosted_score = _score_memory_candidate(
        boosted_payload,
        query_lower=query_lower,
        query_tokens=query_tokens,
        wm_support=wm_support,
        now_ts=now_ts,
        quantum_layer=None,
        query_hrr=None,
        hrr_cache=hrr_cache,
    )
    baseline_score = _score_memory_candidate(
        baseline_payload,
        query_lower=query_lower,
        query_tokens=query_tokens,
        wm_support=wm_support,
        now_ts=now_ts,
        quantum_layer=None,
        query_hrr=None,
        hrr_cache=hrr_cache,
    )

    assert boosted_score > baseline_score
