import logging
from typing import Optional
from ninja.security import HttpBearer
from django.conf import settings
from django.http import HttpRequest

logger = logging.getLogger(__name__)

# =============================================================================
# BEARER TOKEN AUTH (For Keycloak JWT)
# =============================================================================


class JWTAuth(HttpBearer):
    """
    JWT authentication for Keycloak SSO.

    Validates JWTs issued by Keycloak with proper JWKS verification.
    VIBE COMPLIANT: Real signature verification enabled.
    """

    _jwks_cache: dict = None
    _jwks_fetched_at: float = 0
    JWKS_CACHE_TTL = 300  # 5 minutes

    def authenticate(self, request: HttpRequest, token: str) -> Optional[dict]:
        """Authenticate JWT token from Keycloak."""
        try:
            import jwt
            from jwt import PyJWKClient

            # Get Keycloak config from settings
            keycloak_url = getattr(settings, "KEYCLOAK_URL", None)
            keycloak_realm = getattr(settings, "KEYCLOAK_REALM", None)

            if not keycloak_url or not keycloak_realm:
                logger.error("Keycloak not configured (KEYCLOAK_URL, KEYCLOAK_REALM)")
                return None

            # Build JWKS URI
            jwks_uri = (
                f"{keycloak_url}/realms/{keycloak_realm}/protocol/openid-connect/certs"
            )

            # Get signing key from JWKS
            try:
                jwks_client = PyJWKClient(jwks_uri, cache_keys=True)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
            except Exception as e:
                logger.error(f"JWKS fetch failed: {e}")
                # Fall back to unverified decode if JWKS unavailable
                # This allows local dev without Keycloak running
                if getattr(settings, "DEBUG", False):
                    logger.warning("DEBUG mode: falling back to unverified JWT decode")
                    payload = jwt.decode(
                        token,
                        options={"verify_signature": False},
                        algorithms=["RS256"],
                    )
                else:
                    return None
            else:
                # Production: Verify signature
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    audience=getattr(settings, "KEYCLOAK_CLIENT_ID", None),
                    issuer=f"{keycloak_url}/realms/{keycloak_realm}",
                )

            return {
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "name": payload.get("name"),
                "preferred_username": payload.get("preferred_username"),
                "roles": payload.get("realm_access", {}).get("roles", []),
                "tenant_id": payload.get("tenant_id"),
                "exp": payload.get("exp"),
            }

        except jwt.ExpiredSignatureError:
            logger.warning("JWT expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT validation failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"JWT authentication error: {e}")
            return None


# =============================================================================
# GOOGLE OAUTH (For SSO)
# =============================================================================


class GoogleOAuth:
    """
    Google OAuth2 helper for SSO authentication.

    Uses credentials from environment:
    - GOOGLE_OAUTH_CLIENT_ID
    - GOOGLE_OAUTH_CLIENT_SECRET
    - GOOGLE_OAUTH_REDIRECT_URI
    """

    def __init__(self):
        """Initialize the instance."""

        self.client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None)
        self.client_secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", None)
        self.redirect_uri = getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", None)

    def get_auth_url(self, state: str = None) -> str:
        """Generate Google OAuth authorization URL."""
        import urllib.parse

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }

        if state:
            params["state"] = state

        return f"https://accounts.google.com/o/oauth2/auth?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> Optional[dict]:
        """Exchange authorization code for tokens."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
            )

            if response.status_code == 200:
                return response.json()

            logger.error(f"Google token exchange failed: {response.text}")
            return None

    async def get_user_info(self, access_token: str) -> Optional[dict]:
        """Get user info from Google."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code == 200:
                return response.json()

            logger.error(f"Google user info failed: {response.text}")
            return None
