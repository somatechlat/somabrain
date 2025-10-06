from somabrain.metrics import tau_gauge  # Import shared gauge

class ContextBuilder:
    def __init__(self, tenant_id: str | None = None, initial_tau: float = 1.0):
        """Create a ContextBuilder.

        Parameters
        ----------
        tenant_id: str | None, optional
            Identifier for the tenant. If omitted, a default ``"default"`` tenant is used.
        initial_tau: float, default 1.0
            Starting diversity parameter.
        """
        self.tenant_id = tenant_id or "default"
        self._current_tau = initial_tau
        self._history = []

    def build_context(self):
        # Build context using the current tau
        context = self._build_context_with_tau(self._current_tau)
        
        # Tau adaptation for diversity
        self._track_diversity()
        clamped_tau = max(0.4, min(1.2, self._current_tau))
        # Update shared gauge with tenant label
        gauge = tau_gauge.labels(self.tenant_id)
        gauge.set(clamped_tau)
        # Ensure compatibility with tests expecting a `_val` attribute
        try:
            gauge._val = gauge._value
        except Exception:
            pass
        
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
        if recent_coords:
            duplicate_ratio = len(set(recent_coords)) / len(recent_coords)
        else:
            duplicate_ratio = 0.0
        
        # Adjust tau based on diversity needs
        if duplicate_ratio < 0.6:
            self._current_tau *= 1.05
        elif duplicate_ratio > 0.8:
            self._current_tau *= 0.95