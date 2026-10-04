"""Module opa."""

import logging

from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

import somabrain.opa.signature as opa_signature
from somabrain.api.auth import require_admin_auth
from somabrain.opa import policy_manager
from somabrain.opa.client import opa_client
from somabrain.opa.policy_builder import build_policy
from somabrain.services.constitution import get_constitution_engine

router = Router(tags=["opa"])


@router.get("/policy")
def get_policy(request: HttpRequest):
    """Return the stored OPA policy and its signature."""
    require_admin_auth(request, settings)
    policy, sig = policy_manager.load_policy()
    if policy is None:
        raise HttpError(404, "OPA policy not found")
    return {"policy": policy, "signature": sig}


@router.post("/policy")
def update_policy(request: HttpRequest):
    """Generate a new OPA policy from the current constitution."""
    require_admin_auth(request, settings)
    engine = get_constitution_engine()

    # Check if engine is ready
    if not engine or not engine.get_constitution():
        # Unlike FastAPI which checks getattr(engine, 'get_constitution'), we just call it
        # since we know the type if it's not None.
        if not engine:
            raise HttpError(500, "Constitution engine unavailable")
        if not engine.get_constitution():
            raise HttpError(500, "Constitution not loaded")

    constitution = engine.get_constitution()
    policy_str = build_policy(constitution)

    priv_key_path = getattr(settings, "opa_privkey_path", None)
    sig = opa_signature.sign_policy(policy_str, priv_key_path)

    pub_key_path = getattr(settings, "opa_pubkey_path", None)
    if pub_key_path and not opa_signature.verify_policy(policy_str, sig, pub_key_path):
        raise HttpError(500, "Signature verification failed")

    # Fail-closed: a policy that is not persisted or not reloaded is not an
    # update. Reporting success here would let the gate silently drift open.
    if not policy_manager.store_policy(policy_str, sig):
        raise HttpError(500, "Failed to store OPA policy; refusing to report success")

    try:
        reloaded = opa_client.reload_policy()
    except Exception as exc:
        logging.getLogger("somabrain.opa").exception("OPA reload raised")
        raise HttpError(500, f"OPA reload failed; refusing to report success: {exc}")
    if not reloaded:
        raise HttpError(500, "OPA reload failed; refusing to report success")

    return {"detail": "OPA policy updated and reloaded", "signature": sig}
