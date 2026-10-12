"""Hot API middleware slimming for Django Ninja memory routes.

SomaBrain is an HTTP + Ninja service. Browser middleware (sessions, CSRF for
cookie forms, flash messages, session auth) is not the trust boundary for
``/memory/*`` — that is ``StandaloneAPIKeyAuth`` bearer + OPA + Controls +
credential-tenant binding.

This module **does not disable security**. It only avoids loading unused
session/message machinery on the hot write path so accept latency is not paid
for browser concerns. OPA and Controls stay on every request.
"""

from __future__ import annotations

from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.middleware.csrf import CsrfViewMiddleware

def _hot_api_prefixes() -> tuple[str, ...]:
    from somabrain.settings.resolve import require_setting

    value = require_setting("HOT_API_PREFIXES")
    return tuple(str(p) for p in value)


def is_hot_api_path(path: str) -> bool:
    """True for the bearer-authenticated memory API surface (HOT_API_PREFIXES)."""
    text = path or ""
    return text.startswith(_hot_api_prefixes())


class SlimSessionMiddleware(SessionMiddleware):
    """Skip session load/store for bearer memory API requests."""

    def process_request(self, request):
        if is_hot_api_path(request.path):
            request.session = self.SessionStore()
            return None
        return super().process_request(request)

    def process_response(self, request, response):
        if is_hot_api_path(request.path):
            return response
        return super().process_response(request, response)


class SlimCsrfMiddleware(CsrfViewMiddleware):
    """CSRF is for cookie-session forms; bearer Ninja API is not cookie auth.

    Ninja routes already authenticate with ``Authorization: Bearer``. We keep
    CSRF on for every non-memory path.
    """

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if is_hot_api_path(request.path):
            return None
        return super().process_view(request, callback, callback_args, callback_kwargs)


class SlimMessagesMiddleware(MessageMiddleware):
    """Flash messages are unused on the JSON memory API."""

    def __init__(self, get_response):
        super().__init__(get_response)

    def __call__(self, request):
        if is_hot_api_path(request.path):
            return self.get_response(request)
        return super().__call__(request)


class SlimAuthenticationMiddleware(AuthenticationMiddleware):
    """Session user is unused on bearer memory API (tenant comes from request.auth)."""

    def process_request(self, request):
        if is_hot_api_path(request.path):
            from django.contrib.auth.models import AnonymousUser

            request.user = AnonymousUser()
            return None
        return super().process_request(request)
