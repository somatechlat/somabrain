from dataclasses import asdict
from typing import Any

def update_metrics(
    tenant_id: str,
    retrieval: Any,
    utility: Any,
    gains: Any,
    constraints: Any,
) -> None:
    """Update Prometheus/monitoring metrics."""
    try:
        from somabrain import metrics as _metrics

        _metrics.update_learning_retrieval_weights(
            tenant_id=tenant_id,
            alpha=retrieval.alpha,
            beta=retrieval.beta,
            gamma=retrieval.gamma,
            tau=retrieval.tau,
        )
        _metrics.update_learning_utility_weights(
            tenant_id=tenant_id,
            lambda_=utility.lambda_,
            mu=utility.mu,
            nu=utility.nu,
        )
        _metrics.update_learning_gains(
            tenant_id=tenant_id, **asdict(gains)
        )
        _metrics.update_learning_bounds(
            tenant_id=tenant_id, **asdict(constraints)
        )
    except Exception:
        pass
