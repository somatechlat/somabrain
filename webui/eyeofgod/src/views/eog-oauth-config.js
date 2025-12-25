/**
 * OAuth Configuration View
 * Route: /platform/oauth
 * 
 * Manage platform and tenant OAuth identity providers.
 * 
 * VIBE PERSONAS:
 * - Security: Vault secret references, no plaintext secrets
 * - Architect: Multi-provider support (Google, GitHub, Keycloak, OIDC)
 * - UX: Clear provider cards with test buttons
 * - DevOps: Connection testing
 */

import { LitElement, html, css } from 'lit';
import { oauthApi } from '../services/api.js';

export class EogOauthConfig extends LitElement {
    static properties = {
        providers: { type: Array },
        isLoading: { type: Boolean },
        selectedProvider: { type: Object },
    };

    static styles = css`
    :host {
      display: block;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }

    h1 {
      margin: 0;
      font-size: 24px;
      color: var(--eog-text, #e4e4e7);
    }

    .btn-create {
      background: var(--eog-primary, #6366f1);
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 8px;
      font-weight: 500;
      cursor: pointer;
    }

    .providers-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
    }

    .provider-card {
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      padding: 20px;
    }

    .provider-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
    }

    .provider-icon {
      width: 40px;
      height: 40px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      background: rgba(255, 255, 255, 0.05);
    }

    .provider-info {
      flex: 1;
    }

    .provider-name {
      font-weight: 600;
      color: var(--eog-text, #e4e4e7);
    }

    .provider-type {
      font-size: 12px;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .provider-status {
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 500;
    }

    .provider-status.enabled { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
    .provider-status.disabled { background: rgba(239, 68, 68, 0.2); color: #ef4444; }

    .provider-details {
      font-size: 13px;
      color: var(--eog-text-muted, #a1a1aa);
      margin-bottom: 16px;
    }

    .detail-row {
      display: flex;
      justify-content: space-between;
      padding: 6px 0;
      border-bottom: 1px solid var(--eog-border, #27273a);
    }

    .detail-row:last-child {
      border-bottom: none;
    }

    .provider-actions {
      display: flex;
      gap: 8px;
    }

    .btn {
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      cursor: pointer;
      border: 1px solid var(--eog-border, #27273a);
      background: transparent;
      color: var(--eog-text, #e4e4e7);
    }

    .btn:hover {
      background: rgba(255, 255, 255, 0.05);
    }

    .btn-primary {
      background: var(--eog-primary, #6366f1);
      border-color: var(--eog-primary, #6366f1);
      color: white;
    }
  `;

    constructor() {
        super();
        // Mock providers until API connected
        this.providers = [
            {
                id: '1',
                name: 'Google OAuth',
                provider_type: 'google',
                client_id: '123456789.apps.googleusercontent.com',
                is_enabled: true,
                is_default: true,
                tenant: null,
            },
            {
                id: '2',
                name: 'GitHub OAuth',
                provider_type: 'github',
                client_id: 'Iv1.abcdef123456',
                is_enabled: true,
                is_default: false,
                tenant: null,
            },
            {
                id: '3',
                name: 'Keycloak (Enterprise)',
                provider_type: 'keycloak',
                client_id: 'somabrain-client',
                is_enabled: false,
                is_default: false,
                tenant: null,
            },
        ];
        this.isLoading = false;
        this.selectedProvider = null;
    }

    _getProviderIcon(type) {
        const icons = {
            google: '🔵',
            github: '⚫',
            facebook: '🔷',
            keycloak: '🔐',
            oidc: '🔑',
        };
        return icons[type] || '🔗';
    }

    _getProviderLabel(type) {
        const labels = {
            google: 'Google OAuth',
            github: 'GitHub OAuth',
            facebook: 'Facebook OAuth',
            keycloak: 'Keycloak',
            oidc: 'OpenID Connect',
        };
        return labels[type] || type;
    }

    async _testProvider(provider) {
        alert(`Testing ${provider.name}...`);
        // TODO: Implement API test
    }

    render() {
        return html`
      <div class="view">
        <div class="header">
          <h1>OAuth Providers</h1>
          <button class="btn-create">+ Add Provider</button>
        </div>

        <div class="providers-grid">
          ${this.providers.map(provider => html`
            <div class="provider-card">
              <div class="provider-header">
                <div class="provider-icon">${this._getProviderIcon(provider.provider_type)}</div>
                <div class="provider-info">
                  <div class="provider-name">${provider.name}</div>
                  <div class="provider-type">${this._getProviderLabel(provider.provider_type)}</div>
                </div>
                <span class="provider-status ${provider.is_enabled ? 'enabled' : 'disabled'}">
                  ${provider.is_enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>

              <div class="provider-details">
                <div class="detail-row">
                  <span>Client ID</span>
                  <span>${provider.client_id.slice(0, 15)}...</span>
                </div>
                <div class="detail-row">
                  <span>Scope</span>
                  <span>${provider.tenant ? provider.tenant.slug : 'Platform-wide'}</span>
                </div>
                <div class="detail-row">
                  <span>Default</span>
                  <span>${provider.is_default ? '✓ Yes' : 'No'}</span>
                </div>
              </div>

              <div class="provider-actions">
                <button class="btn" @click=${() => this._testProvider(provider)}>Test</button>
                <button class="btn">Edit</button>
                <button class="btn">${provider.is_enabled ? 'Disable' : 'Enable'}</button>
              </div>
            </div>
          `)}
        </div>
      </div>
    `;
    }
}

customElements.define('eog-oauth-config', EogOauthConfig);
