## Policies (OPA)

Integrator policy lives under `ops/opa/policies/integrator.rego` with package `soma.policy.integrator`.

Expected input shape (subset):

```
{
  "input": {
    "tenant": "public",
    "candidate": {"leader": "agent", "weights": {"state": 0.2, "agent": 0.6, "action": 0.2}},
    "event": {"domain": "state", ...}
  }
}
```

Expected result:

```
{"result": {"allow": true, "leader": "action"}}
```

Enable via env:
- `SOMABRAIN_OPA_URL=http://somabrain_opa:8181`
- `SOMABRAIN_OPA_POLICY=soma.policy.integrator`

Tests: see `tests/cog/test_integrator_opa_policy.py` for HTTP stubbed coverage.
