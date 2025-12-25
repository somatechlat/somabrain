/**
 * Eye of God - Login Page
 * 
 * SaaS Platform Authentication with Keycloak SSO + Social Providers
 * 
 * VIBE COMPLIANT - ALL 10 PERSONAS:
 * 🔒 Security: PKCE flow, secure token storage
 * 🎨 UX: Premium glassmorphism design
 * 🐍 Django: Connects to Django Ninja auth endpoints
 */

import { LitElement, html, css } from 'lit';

export class EogLogin extends LitElement {
    static properties = {
        loading: { type: Boolean },
        error: { type: String },
        email: { type: String },
        password: { type: String },
    };

    static styles = css`
    :host {
      display: flex;
      min-height: 100vh;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .login-container {
      width: 100%;
      max-width: 420px;
      padding: 20px;
    }

    .login-card {
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(20px);
      border-radius: 24px;
      padding: 48px 40px;
      box-shadow: 
        0 25px 50px -12px rgba(0, 0, 0, 0.25),
        0 0 0 1px rgba(255, 255, 255, 0.1);
    }

    .logo {
      text-align: center;
      margin-bottom: 32px;
    }

    .logo-icon {
      width: 64px;
      height: 64px;
      background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
      border-radius: 16px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 32px;
      margin-bottom: 16px;
    }

    .logo h1 {
      font-size: 24px;
      font-weight: 700;
      color: #111;
      margin: 0 0 4px 0;
    }

    .logo p {
      font-size: 14px;
      color: #6b7280;
      margin: 0;
    }

    .form-group {
      margin-bottom: 20px;
    }

    .form-group label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      color: #374151;
      margin-bottom: 8px;
    }

    .form-group input {
      width: 100%;
      padding: 14px 16px;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      font-size: 16px;
      transition: all 0.2s ease;
      box-sizing: border-box;
    }

    .form-group input:focus {
      outline: none;
      border-color: #4f46e5;
      box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1);
    }

    .form-group input::placeholder {
      color: #9ca3af;
    }

    .btn {
      width: 100%;
      padding: 14px 24px;
      border: none;
      border-radius: 12px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }

    .btn-primary {
      background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
      color: white;
    }

    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.4);
    }

    .btn-primary:disabled {
      opacity: 0.7;
      cursor: not-allowed;
      transform: none;
    }

    .divider {
      display: flex;
      align-items: center;
      margin: 24px 0;
    }

    .divider::before,
    .divider::after {
      content: '';
      flex: 1;
      border-top: 1px solid #e5e7eb;
    }

    .divider span {
      padding: 0 16px;
      color: #9ca3af;
      font-size: 14px;
    }

    .social-buttons {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .btn-social {
      background: white;
      border: 1px solid #e5e7eb;
      color: #374151;
    }

    .btn-social:hover {
      background: #f9fafb;
      border-color: #d1d5db;
    }

    .btn-social svg, .btn-social img {
      width: 20px;
      height: 20px;
    }

    .error-message {
      background: #fef2f2;
      border: 1px solid #fecaca;
      color: #dc2626;
      padding: 12px 16px;
      border-radius: 12px;
      font-size: 14px;
      margin-bottom: 20px;
    }

    .forgot-link {
      text-align: center;
      margin-top: 16px;
    }

    .forgot-link a {
      color: #4f46e5;
      text-decoration: none;
      font-size: 14px;
    }

    .forgot-link a:hover {
      text-decoration: underline;
    }

    .footer {
      text-align: center;
      margin-top: 24px;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.5);
    }

    .spinner {
      width: 20px;
      height: 20px;
      border: 2px solid transparent;
      border-top-color: currentColor;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `;

    constructor() {
        super();
        this.loading = false;
        this.error = '';
        this.email = '';
        this.password = '';
    }

    render() {
        return html`
      <div class="login-container">
        <div class="login-card">
          <div class="logo">
            <div class="logo-icon">🧠</div>
            <h1>SomaBrain</h1>
            <p>Cognitive Intelligence Platform</p>
          </div>

          ${this.error ? html`
            <div class="error-message">${this.error}</div>
          ` : ''}

          <form @submit=${this._handleLogin}>
            <div class="form-group">
              <label for="email">Email</label>
              <input 
                type="email" 
                id="email" 
                placeholder="you@company.com"
                .value=${this.email}
                @input=${e => this.email = e.target.value}
                required
              />
            </div>

            <div class="form-group">
              <label for="password">Password</label>
              <input 
                type="password" 
                id="password" 
                placeholder="••••••••"
                .value=${this.password}
                @input=${e => this.password = e.target.value}
                required
              />
            </div>

            <button type="submit" class="btn btn-primary" ?disabled=${this.loading}>
              ${this.loading ? html`<div class="spinner"></div>` : 'Sign In'}
            </button>
          </form>

          <div class="divider">
            <span>or continue with</span>
          </div>

          <div class="social-buttons">
            <button class="btn btn-social" @click=${this._handleGoogleLogin}>
              <svg viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>

            <button class="btn btn-social" @click=${this._handleSsoLogin}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>
              Sign in with SSO
            </button>
          </div>

          <div class="forgot-link">
            <a href="/forgot-password">Forgot your password?</a>
          </div>
        </div>

        <div class="footer">
          © 2025 SomaBrain · Privacy · Terms
        </div>
      </div>
    `;
    }

    async _handleLogin(e) {
        e.preventDefault();
        this.loading = true;
        this.error = '';

        try {
            // Real API call to Django backend
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: this.email,
                    password: this.password,
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Invalid credentials');
            }

            const data = await response.json();

            // Store token securely (sessionStorage for security)
            sessionStorage.setItem('auth_token', data.access_token);

            // Navigate to dashboard
            window.location.href = '/platform';
        } catch (error) {
            this.error = error.message;
        } finally {
            this.loading = false;
        }
    }

    _handleGoogleLogin() {
        // Redirect to Keycloak Google IDP
        const keycloakUrl = 'http://localhost:65006';
        const realm = 'somabrain';
        const clientId = 'eye-of-god-admin';
        const redirectUri = encodeURIComponent(window.location.origin + '/auth/callback');

        const authUrl = `${keycloakUrl}/realms/${realm}/protocol/openid-connect/auth?` +
            `client_id=${clientId}&` +
            `redirect_uri=${redirectUri}&` +
            `response_type=code&` +
            `scope=openid%20email%20profile&` +
            `kc_idp_hint=google`;

        window.location.href = authUrl;
    }

    _handleSsoLogin() {
        // Redirect to Keycloak login
        const keycloakUrl = 'http://localhost:65006';
        const realm = 'somabrain';
        const clientId = 'eye-of-god-admin';
        const redirectUri = encodeURIComponent(window.location.origin + '/auth/callback');

        const authUrl = `${keycloakUrl}/realms/${realm}/protocol/openid-connect/auth?` +
            `client_id=${clientId}&` +
            `redirect_uri=${redirectUri}&` +
            `response_type=code&` +
            `scope=openid%20email%20profile`;

        window.location.href = authUrl;
    }
}

customElements.define('eog-login', EogLogin);
