"""Package placeholder for observability utilities used by the somabrain
services.

In production this package would provide OpenTelemetry tracing and metrics
integration.  For the purpose of unit testing we only need the symbols
``init_tracing`` and ``get_tracer`` defined in ``provider.py``.  The module is
kept deliberately minimal – it simply marks the package as importable.
"""
