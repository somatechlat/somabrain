"""Module opa."""

from ninja import Router
from django.http import HttpRequest
from ninja.errors import HttpError

from django.conf import settings
import somabrain.opa.policy_manager as policy_manager
import somabrain.opa.signature as opa_signature
from somabrain.auth import require_admin_auth
from somabrain.opa.client import opa_client
from somabrain.opa.policy_builder import build_policy
from somabrain.services.constitution import get_constitution_engine
import logging

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

    if not policy_manager.store_policy(policy_str, sig):
        logging.getLogger("somabrain.opa").warning(
            "Failed to store OPA policy in Redis – proceeding without persistence"
        )

    try:
        if not opa_client.reload_policy():
            logging.getLogger("somabrain.opa").warning(
                "OPA reload failed – continuing without error"
            )
    except Exception:
        logging.getLogger("somabrain.opa").exception(
            "Exception during OPA reload – ignoring"
        )

    return {"detail": "OPA policy updated and reloaded", "signature": sig}
