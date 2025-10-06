from prometheus_client import Gauge

class ContextBuilder:
    def __init__(self, tenant_id, initial_tau=1.0):
        self.tenant_id = tenant_id
        self._current_tau = initial_tau
        self._history = []

    def build_context(self):
        # Build context using the current tau
        context = self._build_context_with_tau(self._current_tau)
        
        # Tau adaptation for diversity
        self._track_diversity()
        clamped_tau = max(0.4, min(1.2, self._current_tau))
        tau_gauge.set(clamped_tau)
        
        return context

    def _build_context_with_tau(self, tau):
        # Build context using the current tau
        context = []
        for _ in range(100):
            context.append(self._sample_coordinate(tau))
        return context

    def _sample_coordinate(self, tau):
        # Sample a coordinate using the current tau
        return (self._history[-1] + tau * self._history[-2]) % 100

    def _track_diversity(self):
        # Track coordinate repetition patterns
        recent_coords = self._history[-100:]
        duplicate_ratio = len(set(recent_coords)) / len(recent_coords)
        
        # Adjust tau based on diversity needs
        if duplicate_ratio < 0.6:
            self._current_tau *= 1.05
        elif duplicate_ratio > 0.8:
            self._current_tau *= 0.95

# Diversity tracking metric
tau_gauge = Gauge('soma_context_builder_tau', 'Current tau value for diversity adaptation', ['tenant_id'])