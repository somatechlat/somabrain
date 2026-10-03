"""MemoryClient has no hardcoded endpoint and no default tenant (Rule 91).

``controls/memory_client.py`` used to fall back to
``http://localhost:21000`` when ``SOMABRAIN_MEMORY_HTTP_ENDPOINT`` was
unset. That default is the wrong port (SFM serves on 10101) and a hardcoded
URL: if the setting is missing the client must refuse, not invent a target.

``tenant="default"`` is the same class of defect. A caller that forgets the
tenant would silently write into a shared partition. Tenant must be supplied;
a missing tenant raises.
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django

BRAIN_ROOT = Path(__file__).resolve().parents[2]
MEMORY_CLIENT = BRAIN_ROOT / "somabrain" / "controls" / "memory_client.py"

# The wrong-port default that used to live at memory_client.py:53.
FORBIDDEN_URL = "http://localhost:21000"


def test_no_hardcoded_memory_endpoint_in_source():
    """Static: the wrong-port localhost URL must be gone entirely."""
    source = MEMORY_CLIENT.read_text(encoding="utf-8")
    assert FORBIDDEN_URL not in source
    assert "localhost:21000" not in source


def test_store_and_search_have_no_default_tenant():
    """Static: ``tenant`` must not carry a default on store/search."""
    tree = ast.parse(MEMORY_CLIENT.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in {"store", "search"}:
            continue
        # Skip nested/protocol stubs that only declare a docstring.
        args = node.args
        all_args = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
        for arg in all_args:
            if arg.arg != "tenant":
                continue
            default = None
            if arg in args.kwonlyargs:
                idx = args.kwonlyargs.index(arg)
                if idx < len(args.kw_defaults):
                    default = args.kw_defaults[idx]
            else:
                positional = list(args.posonlyargs) + list(args.args)
                idx = positional.index(arg)
                # defaults align to the end of the positional list
                offset = len(positional) - len(args.defaults)
                if idx >= offset and args.defaults:
                    default = args.defaults[idx - offset]
            if default is not None:
                offenders.append(f"{node.name}:{node.lineno} has default {ast.dump(default)}")
    assert offenders == [], f"tenant must be required, found defaults: {offenders}"


@pytest.fixture
def memory_settings():
    """Minimal Django settings so MemoryClient can be imported and constructed."""
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            DEBUG=False,
            DATABASES={},
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                }
            },
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            SOMABRAIN_MEMORY_MODE="http",
            SOMABRAIN_MEMORY_HTTP_ENDPOINT="http://127.0.0.1:10101",
            SOMABRAIN_MEMORY_HTTP_TOKEN="test-only-token-not-a-credential",
        )
        import django

        django.setup()
    # pytest-django's mailbox autoclear expects django.core.mail.outbox.
    import django.core.mail as mail

    if not hasattr(mail, "outbox"):
        mail.outbox = []
    return settings


def _import_memory_client():
    import importlib

    return importlib.import_module("somabrain.controls.memory_client").MemoryClient


def test_unset_endpoint_raises(memory_settings):
    """No endpoint configured -> ImproperlyConfigured, not a guessed URL."""
    MemoryClient = _import_memory_client()
    had = hasattr(memory_settings, "SOMABRAIN_MEMORY_HTTP_ENDPOINT")
    previous = getattr(memory_settings, "SOMABRAIN_MEMORY_HTTP_ENDPOINT", None)
    try:
        if had:
            del memory_settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT
        with pytest.raises(Exception) as excinfo:
            MemoryClient()
        assert "SOMABRAIN_MEMORY_HTTP_ENDPOINT" in str(excinfo.value)
    finally:
        if had:
            memory_settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT = previous


def test_empty_endpoint_raises(memory_settings):
    """An empty endpoint is unset, not a license to invent localhost:21000."""
    MemoryClient = _import_memory_client()
    previous = memory_settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT
    memory_settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT = ""
    try:
        with pytest.raises(Exception) as excinfo:
            MemoryClient()
        assert "SOMABRAIN_MEMORY_HTTP_ENDPOINT" in str(excinfo.value)
    finally:
        memory_settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT = previous


def test_store_requires_tenant(memory_settings):
    """Omitting tenant is a TypeError; an empty tenant is a ValueError."""
    MemoryClient = _import_memory_client()
    client = MemoryClient()

    with pytest.raises(TypeError):
        asyncio.run(client.store([0.1, 0.2], {"type": "test"}))

    with pytest.raises(ValueError):
        asyncio.run(client.store([0.1, 0.2], {"type": "test"}, tenant=""))


def test_search_requires_tenant(memory_settings):
    """Search is scoped by tenant exactly like store."""
    MemoryClient = _import_memory_client()
    client = MemoryClient()

    with pytest.raises(TypeError):
        asyncio.run(client.search("query", top_k=1))

    with pytest.raises(ValueError):
        asyncio.run(client.search("query", top_k=1, tenant="   "))


def test_constructor_accepts_configured_endpoint(memory_settings):
    """A configured endpoint is used as-is (topology, no rewriting)."""
    MemoryClient = _import_memory_client()
    client = MemoryClient()
    assert client.endpoint == memory_settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT
    assert "21000" not in client.endpoint
