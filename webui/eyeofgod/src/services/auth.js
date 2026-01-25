/**
 * OIDC Authentication Service for Eye of God
 * 
 * Handles Keycloak OIDC authentication with PKCE flow.
 * 
 * ALL 10 PERSONAS per VIBE Coding Rules:
 * - Security: PKCE, no localStorage for secrets
 * - UX: Smooth login/logout flow
 * - Architect: Clean service pattern
 */

const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8080';
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || 'somabrain';
const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'eye-of-god-admin';

// OIDC endpoints
const OIDC_CONFIG = {
    authorizationEndpoint: `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth`,
    tokenEndpoint: `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`,
    logoutEndpoint: `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/logout`,
    userInfoEndpoint: `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/userinfo`,
};

/**
 * Generate cryptographically secure random string
 */
function generateRandomString(length) {
    const array = new Uint8Array(length);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Generate code verifier for PKCE
 */
function generateCodeVerifier() {
    return generateRandomString(32);
}

/**
 * Generate code challenge from verifier using SHA-256
 */
async function generateCodeChallenge(verifier) {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const hash = await crypto.subtle.digest('SHA-256', data);
    return btoa(String.fromCharCode(...new Uint8Array(hash)))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '');
}

/**
 * Auth state stored in sessionStorage (not localStorage for security)
 */
const AUTH_STATE_KEY = 'eog_auth_state';
const CODE_VERIFIER_KEY = 'eog_code_verifier';
const ACCESS_TOKEN_KEY = 'eog_access_token';
const REFRESH_TOKEN_KEY = 'eog_refresh_token';
const USER_INFO_KEY = 'eog_user_info';

class AuthService {
    constructor() {
        this._user = null;
        this._accessToken = null;
        this._refreshToken = null;
        this._tokenExpiresAt = null;
        this._listeners = new Set();

        // Restore from session
        this._restoreSession();
    }

    /**
     * Check if user is authenticated
     */
    get isAuthenticated() {
        return !!this._accessToken && this._tokenExpiresAt > Date.now();
    }

    /**
     * Get current user info
     */
    get user() {
        return this._user;
    }

    /**
     * Get access token for API calls
     */
    get accessToken() {
        if (!this._accessToken || this._tokenExpiresAt <= Date.now()) {
            return null;
        }
        return this._accessToken;
    }

    /**
     * Get user roles from token
     */
    get roles() {
        return this._user?.roles || [];
    }

    /**
     * Check if user has a specific role
     */
    hasRole(role) {
        return this.roles.includes(role);
    }

    /**
     * Check if user is admin (aaas_admin or tenant_admin)
     */
    get isAdmin() {
        return this.hasRole('aaas_admin') || this.hasRole('tenant_admin');
    }

    /**
     * Subscribe to auth state changes
     */
    subscribe(callback) {
        this._listeners.add(callback);
        return () => this._listeners.delete(callback);
    }

    _notifyListeners() {
        this._listeners.forEach(cb => cb(this.isAuthenticated, this._user));
    }

    /**
     * Initiate login flow with PKCE
     */
    async login(redirectPath = '/') {
        // Generate PKCE values
        const codeVerifier = generateCodeVerifier();
        const codeChallenge = await generateCodeChallenge(codeVerifier);
        const state = generateRandomString(16);

        // Store for callback
        sessionStorage.setItem(CODE_VERIFIER_KEY, codeVerifier);
        sessionStorage.setItem(AUTH_STATE_KEY, JSON.stringify({ state, redirectPath }));

        // Build auth URL
        const params = new URLSearchParams({
            client_id: KEYCLOAK_CLIENT_ID,
            response_type: 'code',
            scope: 'openid profile email somabrain-roles',
            redirect_uri: `${window.location.origin}/auth/callback`,
            state,
            code_challenge: codeChallenge,
            code_challenge_method: 'S256',
        });

        // Redirect to Keycloak
        window.location.href = `${OIDC_CONFIG.authorizationEndpoint}?${params}`;
    }

    /**
     * Handle auth callback
     */
    async handleCallback() {
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');
        const state = params.get('state');
        const error = params.get('error');

        if (error) {
            throw new Error(`Auth error: ${error} - ${params.get('error_description')}`);
        }

        if (!code) {
            throw new Error('No authorization code received');
        }

        // Verify state
        const storedState = JSON.parse(sessionStorage.getItem(AUTH_STATE_KEY) || '{}');
        if (state !== storedState.state) {
            throw new Error('Invalid state parameter');
        }

        // Get code verifier
        const codeVerifier = sessionStorage.getItem(CODE_VERIFIER_KEY);
        if (!codeVerifier) {
            throw new Error('Missing code verifier');
        }

        // Exchange code for tokens
        const tokenResponse = await fetch(OIDC_CONFIG.tokenEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                grant_type: 'authorization_code',
                client_id: KEYCLOAK_CLIENT_ID,
                code,
                redirect_uri: `${window.location.origin}/auth/callback`,
                code_verifier: codeVerifier,
            }),
        });

        if (!tokenResponse.ok) {
            const error = await tokenResponse.text();
            throw new Error(`Token exchange failed: ${error}`);
        }

        const tokens = await tokenResponse.json();

        // Store tokens
        this._setTokens(tokens);

        // Clean up
        sessionStorage.removeItem(CODE_VERIFIER_KEY);
        sessionStorage.removeItem(AUTH_STATE_KEY);

        // Return redirect path
        return storedState.redirectPath || '/';
    }

    /**
     * Logout user
     */
    async logout(redirectUri = '/') {
        const idToken = this._accessToken; // Use access token for logout

        // Clear local state
        this._clearSession();
        this._notifyListeners();

        // Redirect to Keycloak logout
        const params = new URLSearchParams({
            client_id: KEYCLOAK_CLIENT_ID,
            post_logout_redirect_uri: `${window.location.origin}${redirectUri}`,
        });

        window.location.href = `${OIDC_CONFIG.logoutEndpoint}?${params}`;
    }

    /**
     * Refresh access token
     */
    async refreshAccessToken() {
        if (!this._refreshToken) {
            this._clearSession();
            return false;
        }

        try {
            const response = await fetch(OIDC_CONFIG.tokenEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({
                    grant_type: 'refresh_token',
                    client_id: KEYCLOAK_CLIENT_ID,
                    refresh_token: this._refreshToken,
                }),
            });

            if (!response.ok) {
                throw new Error('Token refresh failed');
            }

            const tokens = await response.json();
            this._setTokens(tokens);
            return true;
        } catch (error) {
            console.error('Token refresh error:', error);
            this._clearSession();
            return false;
        }
    }

    /**
     * Set tokens from response
     */
    _setTokens(tokens) {
        this._accessToken = tokens.access_token;
        this._refreshToken = tokens.refresh_token;
        this._tokenExpiresAt = Date.now() + (tokens.expires_in * 1000);

        // Decode user info from access token
        this._user = this._decodeToken(tokens.access_token);

        // Store in session
        sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
        sessionStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token || '');
        sessionStorage.setItem(USER_INFO_KEY, JSON.stringify(this._user));

        this._notifyListeners();
    }

    /**
     * Decode JWT token (without verification - that's done server-side)
     */
    _decodeToken(token) {
        try {
            const payload = token.split('.')[1];
            const decoded = JSON.parse(atob(payload));
            return {
                id: decoded.sub,
                email: decoded.email,
                name: decoded.name || decoded.preferred_username,
                tenantId: decoded.tenant_id,
                roles: decoded.roles || decoded.realm_access?.roles || [],
            };
        } catch {
            return null;
        }
    }

    /**
     * Restore session from storage
     */
    _restoreSession() {
        const accessToken = sessionStorage.getItem(ACCESS_TOKEN_KEY);
        const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_KEY);
        const userInfo = sessionStorage.getItem(USER_INFO_KEY);

        if (accessToken) {
            this._accessToken = accessToken;
            this._refreshToken = refreshToken || null;
            this._user = userInfo ? JSON.parse(userInfo) : null;

            // Decode expiry from token
            const decoded = this._decodeToken(accessToken);
            if (decoded?.exp) {
                this._tokenExpiresAt = decoded.exp * 1000;
            } else {
                this._tokenExpiresAt = Date.now() + 300000; // Assume 5 min
            }
        }
    }

    /**
     * Clear session data
     */
    _clearSession() {
        this._accessToken = null;
        this._refreshToken = null;
        this._user = null;
        this._tokenExpiresAt = null;

        sessionStorage.removeItem(ACCESS_TOKEN_KEY);
        sessionStorage.removeItem(REFRESH_TOKEN_KEY);
        sessionStorage.removeItem(USER_INFO_KEY);
    }
}

// Singleton instance
export const authService = new AuthService();

// Helper for API calls
export async function fetchWithAuth(url, options = {}) {
    const token = authService.accessToken;

    if (!token) {
        // Try refresh
        await authService.refreshAccessToken();
        if (!authService.accessToken) {
            throw new Error('Not authenticated');
        }
    }

    return fetch(url, {
        ...options,
        headers: {
            ...options.headers,
            Authorization: `Bearer ${authService.accessToken}`,
        },
    });
}
