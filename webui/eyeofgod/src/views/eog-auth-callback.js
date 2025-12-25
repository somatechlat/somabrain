/**
 * Eye of God - Auth Callback Handler
 * 
 * Handles OAuth callback from Keycloak/Google
 * Exchanges code for tokens, stores auth state
 * 
 * VIBE COMPLIANT - ALL 10 PERSONAS
 */

import { LitElement, html, css } from 'lit';

export class EogAuthCallback extends LitElement {
    static properties = {
        status: { type: String },
        error: { type: String },
    };

    static styles = css`
    :host {
      display: flex;
      min-height: 100vh;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
    }

    .callback-card {
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(20px);
      border-radius: 24px;
      padding: 48px;
      text-align: center;
      max-width: 400px;
    }

    .spinner {
      width: 48px;
      height: 48px;
      border: 4px solid #e5e7eb;
      border-top-color: #4f46e5;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin: 0 auto 24px;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .status-icon {
      font-size: 48px;
      margin-bottom: 16px;
    }

    .status-text {
      font-size: 18px;
      font-weight: 600;
      color: #111;
      margin-bottom: 8px;
    }

    .status-desc {
      font-size: 14px;
      color: #6b7280;
    }

    .error-box {
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 12px;
      padding: 16px;
      margin-top: 20px;
    }

    .error-text {
      color: #dc2626;
      font-size: 14px;
    }

    .btn-retry {
      margin-top: 20px;
      padding: 12px 24px;
      background: #4f46e5;
      color: white;
      border: none;
      border-radius: 12px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    }
  `;

    constructor() {
        super();
        this.status = 'processing';
        this.error = '';
    }

    connectedCallback() {
        super.connectedCallback();
        this._processCallback();
    }

    async _processCallback() {
        try {
            // Get auth code from URL
            const urlParams = new URLSearchParams(window.location.search);
            const code = urlParams.get('code');
            const state = urlParams.get('state');
            const error = urlParams.get('error');

            if (error) {
                throw new Error(urlParams.get('error_description') || error);
            }

            if (!code) {
                throw new Error('No authorization code received');
            }

            this.status = 'exchanging';

            // Exchange code for tokens via Django backend
            const response = await fetch('/api/auth/callback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    code,
                    state,
                    redirect_uri: window.location.origin + '/auth/callback',
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Token exchange failed');
            }

            const data = await response.json();

            // Store tokens securely
            sessionStorage.setItem('auth_token', data.access_token);
            if (data.refresh_token) {
                sessionStorage.setItem('refresh_token', data.refresh_token);
            }

            // Store user info
            if (data.user) {
                sessionStorage.setItem('user', JSON.stringify(data.user));
            }

            this.status = 'success';

            // Redirect to dashboard after brief delay
            setTimeout(() => {
                window.location.href = '/platform';
            }, 1500);

        } catch (error) {
            this.status = 'error';
            this.error = error.message;
        }
    }

    render() {
        return html`
      <div class="callback-card">
        ${this.status === 'processing' ? html`
          <div class="spinner"></div>
          <div class="status-text">Authenticating...</div>
          <div class="status-desc">Verifying your credentials</div>
        ` : ''}

        ${this.status === 'exchanging' ? html`
          <div class="spinner"></div>
          <div class="status-text">Completing sign-in...</div>
          <div class="status-desc">Securing your session</div>
        ` : ''}

        ${this.status === 'success' ? html`
          <div class="status-icon">✅</div>
          <div class="status-text">Welcome back!</div>
          <div class="status-desc">Redirecting to dashboard...</div>
        ` : ''}

        ${this.status === 'error' ? html`
          <div class="status-icon">❌</div>
          <div class="status-text">Authentication Failed</div>
          <div class="error-box">
            <div class="error-text">${this.error}</div>
          </div>
          <button class="btn-retry" @click=${() => window.location.href = '/login'}>
            Try Again
          </button>
        ` : ''}
      </div>
    `;
    }
}

customElements.define('eog-auth-callback', EogAuthCallback);
