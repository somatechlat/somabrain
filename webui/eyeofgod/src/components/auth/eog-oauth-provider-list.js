/**
 * OAuth Provider List - Reusable Lit Component
 * 
 * Displays list of configured OAuth identity providers with status.
 * Supports: Google, Facebook, GitHub, Keycloak, Generic OIDC
 * 
 * Reusable across platform admin and tenant admin views.
 */

import { LitElement, html, css } from 'lit';

export class EogOauthProviderList extends LitElement {
    static properties = {
        providers: { type: Array },
        isLoading: { type: Boolean },
        isPlatformLevel: { type: Boolean },
        selectedProviderId: { type: String },
    };

    static styles = css`
    :host {
      display: block;
      font-family: 'Inter', system-ui, sans-serif;
    }

    .provider-list-container {
      background: var(--eog-surface, #1a1a2e);
      border-radius: 12px;
      padding: 20px;
      color: var(--eog-text, #e4e4e7);
    }

    .list-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .list-title {
      font-size: 18px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .list-title .icon {
      font-size: 24px;
    }

    .btn-add {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 16px;
      background: var(--eog-primary, #6366f1);
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-add:hover {
      background: var(--eog-primary-hover, #4f46e5);
    }

    .provider-cards {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .provider-card {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 16px;
      background: var(--eog-card-bg, #0f0f1a);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.2s;
    }

    .provider-card:hover {
      border-color: var(--eog-primary, #6366f1);
      background: rgba(99, 102, 241, 0.05);
    }

    .provider-card.selected {
      border-color: var(--eog-primary, #6366f1);
      background: rgba(99, 102, 241, 0.1);
    }

    .provider-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
    }

    .provider-icon.google {
      background: linear-gradient(135deg, #4285f4, #34a853);
    }

    .provider-icon.facebook {
      background: linear-gradient(135deg, #1877f2, #3b5998);
    }

    .provider-icon.github {
      background: linear-gradient(135deg, #333, #24292e);
    }

    .provider-icon.keycloak {
      background: linear-gradient(135deg, #4d4d4d, #333);
    }

    .provider-icon.oidc {
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
    }

    .provider-info {
      flex: 1;
    }

    .provider-name {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .provider-details {
      display: flex;
      align-items: center;
      gap: 16px;
      font-size: 13px;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .provider-type {
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .provider-scope {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 8px;
      background: rgba(99, 102, 241, 0.2);
      color: var(--eog-primary, #6366f1);
      border-radius: 12px;
      font-size: 11px;
    }

    .provider-status {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 500;
    }

    .status-badge.active {
      background: rgba(34, 197, 94, 0.2);
      color: var(--eog-success, #22c55e);
    }

    .status-badge.inactive {
      background: rgba(239, 68, 68, 0.2);
      color: var(--eog-danger, #ef4444);
    }

    .status-badge.default {
      background: rgba(251, 191, 36, 0.2);
      color: var(--eog-warning, #fbbf24);
    }

    .provider-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .btn-action {
      padding: 8px;
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 8px;
      background: transparent;
      color: var(--eog-text-muted, #a1a1aa);
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-action:hover {
      background: var(--eog-border, #27273a);
      color: var(--eog-text, #e4e4e7);
    }

    .btn-action.danger:hover {
      background: rgba(239, 68, 68, 0.2);
      color: var(--eog-danger, #ef4444);
      border-color: var(--eog-danger, #ef4444);
    }

    .empty-state {
      padding: 48px 24px;
      text-align: center;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .empty-icon {
      font-size: 48px;
      margin-bottom: 16px;
    }

    .empty-title {
      font-size: 18px;
      font-weight: 600;
      color: var(--eog-text, #e4e4e7);
      margin-bottom: 8px;
    }

    .empty-description {
      margin-bottom: 24px;
    }

    .loading-state {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .skeleton-card {
      height: 80px;
      background: linear-gradient(90deg, #1a1a2e 25%, #27273a 50%, #1a1a2e 75%);
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite;
      border-radius: 12px;
    }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  `;

    constructor() {
        super();
        this.providers = [];
        this.isLoading = false;
        this.isPlatformLevel = true;
        this.selectedProviderId = null;
    }

    _getProviderIcon(type) {
        const icons = {
            google: '🔵',
            facebook: '🔷',
            github: '⚫',
            keycloak: '🔐',
            oidc: '🔗'
        };
        return icons[type] || '🔗';
    }

    _getProviderTypeName(type) {
        const names = {
            google: 'Google OAuth',
            facebook: 'Facebook OAuth',
            github: 'GitHub OAuth',
            keycloak: 'Keycloak',
            oidc: 'Generic OIDC'
        };
        return names[type] || type;
    }

    _handleAddNew() {
        this.dispatchEvent(new CustomEvent('add-provider'));
    }

    _handleSelect(provider) {
        this.selectedProviderId = provider.id;
        this.dispatchEvent(new CustomEvent('select-provider', {
            detail: { provider }
        }));
    }

    _handleConfigure(provider, e) {
        e.stopPropagation();
        this.dispatchEvent(new CustomEvent('configure-provider', {
            detail: { provider }
        }));
    }

    _handleTestConnection(provider, e) {
        e.stopPropagation();
        this.dispatchEvent(new CustomEvent('test-connection', {
            detail: { provider }
        }));
    }

    _handleToggle(provider, e) {
        e.stopPropagation();
        this.dispatchEvent(new CustomEvent('toggle-provider', {
            detail: { provider, enabled: !provider.is_enabled }
        }));
    }

    _handleDelete(provider, e) {
        e.stopPropagation();
        if (confirm(`Are you sure you want to delete "${provider.name}"?`)) {
            this.dispatchEvent(new CustomEvent('delete-provider', {
                detail: { provider }
            }));
        }
    }

    render() {
        return html`
      <div class="provider-list-container">
        <div class="list-header">
          <div class="list-title">
            <span class="icon">🔐</span>
            Identity Providers
          </div>
          <button class="btn-add" @click=${this._handleAddNew}>
            + Add Provider
          </button>
        </div>

        ${this.isLoading ? this._renderLoading() :
                this.providers.length === 0 ? this._renderEmpty() :
                    this._renderProviders()}
      </div>
    `;
    }

    _renderLoading() {
        return html`
      <div class="loading-state">
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
      </div>
    `;
    }

    _renderEmpty() {
        return html`
      <div class="empty-state">
        <div class="empty-icon">🔐</div>
        <div class="empty-title">No Identity Providers Configured</div>
        <div class="empty-description">
          Add your first OAuth provider to enable user authentication.
        </div>
        <button class="btn-add" @click=${this._handleAddNew}>
          + Add Provider
        </button>
      </div>
    `;
    }

    _renderProviders() {
        return html`
      <div class="provider-cards">
        ${this.providers.map(provider => html`
          <div 
            class="provider-card ${this.selectedProviderId === provider.id ? 'selected' : ''}"
            @click=${() => this._handleSelect(provider)}
          >
            <div class="provider-icon ${provider.provider_type}">
              ${this._getProviderIcon(provider.provider_type)}
            </div>
            
            <div class="provider-info">
              <div class="provider-name">${provider.name}</div>
              <div class="provider-details">
                <span class="provider-type">
                  ${this._getProviderTypeName(provider.provider_type)}
                </span>
                ${provider.tenant_id ? html`
                  <span class="provider-scope">Tenant</span>
                ` : html`
                  <span class="provider-scope">Platform</span>
                `}
              </div>
            </div>

            <div class="provider-status">
              ${provider.is_default ? html`
                <span class="status-badge default">⭐ Default</span>
              ` : ''}
              <span class="status-badge ${provider.is_enabled ? 'active' : 'inactive'}">
                ${provider.is_enabled ? '✓ Active' : '○ Inactive'}
              </span>
            </div>

            <div class="provider-actions">
              <button 
                class="btn-action" 
                title="Configure"
                @click=${(e) => this._handleConfigure(provider, e)}
              >⚙️</button>
              <button 
                class="btn-action" 
                title="Test Connection"
                @click=${(e) => this._handleTestConnection(provider, e)}
              >🔌</button>
              <button 
                class="btn-action" 
                title="${provider.is_enabled ? 'Disable' : 'Enable'}"
                @click=${(e) => this._handleToggle(provider, e)}
              >${provider.is_enabled ? '⏸️' : '▶️'}</button>
              <button 
                class="btn-action danger" 
                title="Delete"
                @click=${(e) => this._handleDelete(provider, e)}
              >🗑️</button>
            </div>
          </div>
        `)}
      </div>
    `;
    }
}

customElements.define('eog-oauth-provider-list', EogOauthProviderList);
