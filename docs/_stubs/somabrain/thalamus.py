"""Stub for somabrain.thalamus used by Sphinx builds."""


class ThalamusStub:
    """Minimal placeholder class for API docs."""

    def start(self):
        return None


class ThalamusRouter:
    """Lightweight placeholder for the real ThalamusRouter used by the app.

    The real project exposes routing helper classes; this class exists only to
    provide a stable import target for the Sphinx build and carries no runtime
    behavior.
    """

    def route(self, *args, **kwargs):
        return None


__all__ = ["ThalamusStub", "ThalamusRouter"]
