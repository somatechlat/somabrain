from somabrain.autonomous.config import AdaptiveConfigManager, AutonomousConfig


class DummyExperimentManager:
    def __init__(self):
        # experiments: id -> dict with name and sample groups
        self.experiments = {}

    def add_experiment(self, eid, name, control_samples, variant_samples):
        self.experiments[eid] = {
            "name": name,
            "groups": {"control": control_samples, "variant": variant_samples},
        }

    def analyze_experiment(self, eid, metric="latency", alpha=0.05):
        exp = self.experiments.get(eid)
        if not exp:
            return None
        a = exp["groups"]["control"]
        b = exp["groups"]["variant"]
        # simple mean comparison
        import math

        mean_a = sum(a) / len(a)
        mean_b = sum(b) / len(b)
        # effect size simple (Cohen's d)
        pooled_sd = math.sqrt(
            (sum((x - mean_a) ** 2 for x in a) + sum((x - mean_b) ** 2 for x in b))
            / (len(a) + len(b) - 2)
        )
        if pooled_sd == 0:
            d = 0.0
        else:
            d = (mean_b - mean_a) / pooled_sd
        # treat significant if difference > 0.1
        significant = abs(mean_b - mean_a) > 0.1
        return {
            "mean_a": mean_a,
            "mean_b": mean_b,
            "effect_size_cohen_d": d,
            "significant": significant,
        }


def test_promotion_then_rollback():
    cfg = AutonomousConfig()
    manager = AdaptiveConfigManager(cfg)
    # stage a canary
    cfg.set_custom_parameter("canary::timeout_ms", 50)

    em = DummyExperimentManager()
    # experiment shows variant improved -> promotion
    em.add_experiment(
        "can1",
        "canary_timeout_ms",
        control_samples=[100, 102, 98],
        variant_samples=[50, 52, 49],
    )

    promoted = manager.promote_canaries(em, alpha=0.05, min_effect=0.01)
    assert promoted == 1
    # now experiment flips and variant is worse -> trigger rollback
    em.add_experiment(
        "can1",
        "canary_timeout_ms",
        control_samples=[100, 102, 98],
        variant_samples=[200, 210, 205],
    )
    rollbacks = manager.monitor_promotions_and_rollback(em, alpha=0.05, min_effect=0.01)
    # rollback should occur (old was None so param removed)
    assert rollbacks == 1
