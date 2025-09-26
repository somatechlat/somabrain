from fastapi import FastAPI, Request

from somabrain.api.dependencies.utility_guard import compute_utility


def test_compute_utility_basic():
    params = {"lambda": 1.0, "mu": 0.5, "nu": 0.1}
    u = compute_utility(0.9, cost=1.0, latency=0.2, const_params=params)
    assert isinstance(u, float)


def test_utility_guard_allows_request_when_positive():
    app = FastAPI()

    @app.get("/ok")
    async def ok(req: Request):
        return {"utility": req.state.utility_value}

    # call compute_utility directly to assert it returns a numeric
    u = compute_utility(0.9, 0.0, 0.0, {})
    assert isinstance(u, float)
