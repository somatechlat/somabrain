"""
Keycloak Realm Configuration Management Command.

Creates and configures the SomaBrain realm in Keycloak.

ALL 10 PERSONAS per VIBE Coding Rules:
- 🔒 Security: Secure realm configuration, brute force protection
- 🏛️ Architect: Clean realm/client structure
- 💾 DBA: N/A (Keycloak admin API)
- 🐍 Django: Management command pattern
- 📚 Docs: Comprehensive docstrings
- 🧪 QA: Verifiable configuration
- 🚨 SRE: Error handling and logging
- 📊 Perf: Efficient API calls
- 🎨 UX: Clear progress output
- 🛠️ DevOps: Environment-based configuration
"""

import os
import logging

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command class implementation."""

    help = "Configure Keycloak realm for SomaBrain"

    def add_arguments(self, parser):
        """Execute add arguments.

        Args:
            parser: The parser.
        """

        parser.add_argument(
            "--realm",
            default="somabrain",
            help="Keycloak realm name (default: somabrain)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print configuration without applying",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recreate realm even if exists",
        )

    def handle(self, *args, **options):
        """Execute handle."""

        realm_name = options["realm"]
        dry_run = options["dry_run"]
        force = options["force"]

        # Get Keycloak configuration from settings
        keycloak_url = getattr(
            settings,
            "KEYCLOAK_URL",
            os.environ.get("KEYCLOAK_URL", "http://localhost:8080"),
        )
        admin_user = os.environ.get("KEYCLOAK_ADMIN", "admin")
        admin_password = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin")

        self.stdout.write("\n🔐 Keycloak Realm Configuration")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Keycloak URL: {keycloak_url}")
        self.stdout.write(f"Realm: {realm_name}")
        self.stdout.write(f"Dry Run: {dry_run}")
        self.stdout.write("")

        # Build realm configuration
        realm_config = self._build_realm_config(realm_name)

        if dry_run:
            self._print_config(realm_config)
            self.stdout.write(
                self.style.SUCCESS("\n✅ Dry run complete - no changes made")
            )
            return

        # Apply configuration via Keycloak Admin API
        try:
            self._apply_config(
                keycloak_url, admin_user, admin_password, realm_config, force
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Realm '{realm_name}' configured successfully!"
                )
            )
        except Exception as e:
            raise CommandError(f"Failed to configure realm: {e}")

    def _build_realm_config(self, realm_name: str) -> dict:
        """
        Build complete realm configuration.

        ALL 10 PERSONAS:
        - Security: Strong defaults, brute force protection
        - SRE: Reasonable timeouts and limits
        """
        return {
            "realm": realm_name,
            "enabled": True,
            "displayName": "SomaBrain",
            "displayNameHtml": "<b>SomaBrain</b>",
            # Security settings
            "sslRequired": "external",  # Require SSL in production
            "registrationAllowed": False,  # Admin creates users
            "resetPasswordAllowed": True,
            "rememberMe": True,
            "verifyEmail": True,
            "loginWithEmailAllowed": True,
            "duplicateEmailsAllowed": False,
            # Brute force protection
            "bruteForceProtected": True,
            "maxFailureWaitSeconds": 900,  # 15 min lockout
            "minimumQuickLoginWaitSeconds": 60,
            "waitIncrementSeconds": 60,
            "quickLoginCheckMilliSeconds": 1000,
            "maxDeltaTimeSeconds": 3600,
            "failureFactor": 5,  # 5 failed attempts
            # Token settings
            "accessTokenLifespan": 300,  # 5 min
            "accessTokenLifespanForImplicitFlow": 300,
            "ssoSessionIdleTimeout": 1800,  # 30 min
            "ssoSessionMaxLifespan": 36000,  # 10 hours
            "offlineSessionIdleTimeout": 2592000,  # 30 days
            "offlineSessionMaxLifespanEnabled": True,
            "offlineSessionMaxLifespan": 5184000,  # 60 days
            # Realm roles
            "roles": {
                "realm": [
                    {
                        "name": "saas_admin",
                        "description": "SaaS platform administrator - full control",
                    },
                    {
                        "name": "tenant_admin",
                        "description": "Tenant administrator - full tenant control",
                    },
                    {
                        "name": "service_admin",
                        "description": "Cognitive services administrator",
                    },
                    {
                        "name": "supervisor",
                        "description": "Monitor and review operations",
                    },
                    {"name": "operator", "description": "Execute operations"},
                    {"name": "service_user", "description": "Use cognitive services"},
                    {"name": "viewer", "description": "Read-only access"},
                    {
                        "name": "billing_admin",
                        "description": "Billing and subscription management",
                    },
                    {
                        "name": "security_auditor",
                        "description": "Audit and compliance access",
                    },
                ]
            },
            # Default role
            "defaultRoles": ["service_user"],
            # Clients
            "clients": self._build_clients(realm_name),
            # Client scopes
            "clientScopes": self._build_client_scopes(),
            # Identity Providers (Google OAuth)
            "identityProviders": self._build_identity_providers(),
        }

    def _build_clients(self, realm_name: str) -> list:
        """Build Keycloak client configurations."""
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        api_url = getattr(settings, "API_URL", "http://localhost:8000")

        return [
            # Eye of God Admin SPA (public client with PKCE)
            {
                "clientId": "eye-of-god-admin",
                "name": "Eye of God Admin UI",
                "description": "SomaBrain SaaS Admin SPA",
                "protocol": "openid-connect",
                "publicClient": True,
                "standardFlowEnabled": True,
                "implicitFlowEnabled": False,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": False,
                "authorizationServicesEnabled": False,
                "rootUrl": frontend_url,
                "baseUrl": "/",
                "redirectUris": [
                    f"{frontend_url}/*",
                    "http://localhost:5173/*",
                    "http://127.0.0.1:5173/*",
                ],
                "webOrigins": [
                    frontend_url,
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                ],
                "attributes": {
                    "pkce.code.challenge.method": "S256",
                    "post.logout.redirect.uris": f"{frontend_url}/*",
                },
                "defaultClientScopes": [
                    "openid",
                    "profile",
                    "email",
                    "somabrain-roles",
                ],
            },
            # SomaBrain API (bearer-only)
            {
                "clientId": "somabrain-api",
                "name": "SomaBrain API",
                "description": "SomaBrain backend API - bearer-only",
                "protocol": "openid-connect",
                "publicClient": False,
                "bearerOnly": True,
                "standardFlowEnabled": False,
                "implicitFlowEnabled": False,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": False,
            },
            # SomaBrain Service Account (for backend-to-backend)
            {
                "clientId": "somabrain-service",
                "name": "SomaBrain Service Account",
                "description": "Backend service-to-service auth",
                "protocol": "openid-connect",
                "publicClient": False,
                "bearerOnly": False,
                "standardFlowEnabled": False,
                "implicitFlowEnabled": False,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": True,
                "authorizationServicesEnabled": False,
                "secret": "${SOMABRAIN_SERVICE_SECRET}",  # From vault
            },
        ]

    def _build_client_scopes(self) -> list:
        """Build custom client scopes with claim mappers."""
        return [
            {
                "name": "somabrain-roles",
                "description": "SomaBrain realm roles and tenant ID",
                "protocol": "openid-connect",
                "protocolMappers": [
                    # Tenant ID claim
                    {
                        "name": "tenant_id",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-usermodel-attribute-mapper",
                        "consentRequired": False,
                        "config": {
                            "userinfo.token.claim": "true",
                            "user.attribute": "tenant_id",
                            "id.token.claim": "true",
                            "access.token.claim": "true",
                            "claim.name": "tenant_id",
                            "jsonType.label": "String",
                        },
                    },
                    # Realm roles in access token
                    {
                        "name": "realm roles",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-usermodel-realm-role-mapper",
                        "consentRequired": False,
                        "config": {
                            "userinfo.token.claim": "true",
                            "multivalued": "true",
                            "id.token.claim": "true",
                            "access.token.claim": "true",
                            "claim.name": "roles",
                            "jsonType.label": "String",
                        },
                    },
                ],
            },
        ]

    def _build_identity_providers(self) -> list:
        """Build identity provider configurations (Google OAuth)."""
        google_client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
        google_client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")

        if not google_client_id:
            logger.warning("GOOGLE_OAUTH_CLIENT_ID not set - skipping Google IDP")
            return []

        return [
            {
                "alias": "google",
                "displayName": "Google",
                "providerId": "google",
                "enabled": True,
                "updateProfileFirstLoginMode": "on",
                "trustEmail": True,
                "storeToken": False,
                "linkOnly": False,
                "firstBrokerLoginFlowAlias": "first broker login",
                "config": {
                    "clientId": google_client_id,
                    "clientSecret": google_client_secret,
                    "defaultScope": "openid email profile",
                    "syncMode": "IMPORT",
                },
            },
        ]

    def _print_config(self, config: dict):
        """Pretty print configuration for dry run."""

        self.stdout.write("\n📋 Realm Configuration:")
        self.stdout.write("-" * 50)

        # Print key sections
        self.stdout.write(f"\nRealm: {config['realm']}")
        self.stdout.write(f"Display Name: {config['displayName']}")
        self.stdout.write(f"SSL Required: {config['sslRequired']}")
        self.stdout.write(f"Brute Force Protection: {config['bruteForceProtected']}")

        self.stdout.write("\n🎭 Realm Roles:")
        for role in config["roles"]["realm"]:
            self.stdout.write(f"  • {role['name']}: {role['description']}")

        self.stdout.write("\n📱 Clients:")
        for client in config["clients"]:
            client_type = "public" if client.get("publicClient") else "confidential"
            if client.get("bearerOnly"):
                client_type = "bearer-only"
            self.stdout.write(f"  • {client['clientId']} ({client_type})")

        self.stdout.write("\n🔍 Client Scopes:")
        for scope in config["clientScopes"]:
            self.stdout.write(f"  • {scope['name']}: {scope['description']}")

        if config.get("identityProviders"):
            self.stdout.write("\n🌐 Identity Providers:")
            for idp in config["identityProviders"]:
                self.stdout.write(f"  • {idp['displayName']} ({idp['alias']})")
        else:
            self.stdout.write(
                "\n⚠️  No identity providers configured (set GOOGLE_OAUTH_CLIENT_ID)"
            )

    def _apply_config(
        self,
        keycloak_url: str,
        admin_user: str,
        admin_password: str,
        config: dict,
        force: bool,
    ):
        """Apply configuration to Keycloak via Admin REST API."""
        try:
            import httpx
        except ImportError:
            raise CommandError("httpx not installed. Run: pip install httpx")

        self.stdout.write("\n🔄 Connecting to Keycloak...")

        # Get admin token
        token_url = f"{keycloak_url}/realms/master/protocol/openid-connect/token"
        try:
            with httpx.Client(
                timeout=30, verify=False
            ) as client:  # verify=False for self-signed certs
                # Authenticate
                self.stdout.write("  • Authenticating...")
                response = client.post(
                    token_url,
                    data={
                        "grant_type": "password",
                        "client_id": "admin-cli",
                        "username": admin_user,
                        "password": admin_password,
                    },
                )

                if response.status_code != 200:
                    raise CommandError(f"Failed to authenticate: {response.text}")

                access_token = response.json()["access_token"]
                headers = {"Authorization": f"Bearer {access_token}"}

                # Check if realm exists
                realm_name = config["realm"]
                realms_url = f"{keycloak_url}/admin/realms"

                self.stdout.write(f"  • Checking if realm '{realm_name}' exists...")
                response = client.get(f"{realms_url}/{realm_name}", headers=headers)

                if response.status_code == 200:
                    if force:
                        self.stdout.write("  • Deleting existing realm...")
                        client.delete(f"{realms_url}/{realm_name}", headers=headers)
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠️  Realm '{realm_name}' already exists. Use --force to recreate."
                            )
                        )
                        return

                # Create realm
                self.stdout.write(f"  • Creating realm '{realm_name}'...")
                response = client.post(realms_url, headers=headers, json=config)

                if response.status_code not in (201, 204):
                    raise CommandError(
                        f"Failed to create realm: {response.status_code} - {response.text}"
                    )

                self.stdout.write(self.style.SUCCESS("  ✅ Realm created"))

        except httpx.ConnectError as e:
            raise CommandError(f"Cannot connect to Keycloak at {keycloak_url}: {e}")
