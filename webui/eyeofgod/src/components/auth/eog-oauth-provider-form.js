/**
 * OAuth Provider Form - Reusable Lit Component
 * 
 * Configures OAuth identity providers (Google, Facebook, GitHub, Keycloak, OIDC)
 * with all required fields. Secrets referenced via vault path (never stored client-side).
 * 
 * Reusable across:
 * - Platform admin (Eye of God)
 * - Tenant admin
 * - Any future OAuth configuration needs
 */

import { LitElement, html, css } from 'lit';

export class EogOauthProviderForm extends LitElement {
    static properties = {
        provider: { type: Object },
        providerType: { type: String },
        mode: { type: String }, // 'create' | 'edit'
        isLoading: { type: Boolean },
        errors: { type: Object },
        isPlatformLevel: { type: Boolean }, // Platform vs Tenant scope
    };

    static styles = css`
    :host {
      display: block;
      font-family: 'Inter', system-ui, sans-serif;
    }

    .form-container {
      background: var(--eog-surface, #1a1a2e);
      border-radius: 12px;
      padding: 24px;
      color: var(--eog-text, #e4e4e7);
    }

    .form-section {
      margin-bottom: 24px;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--eog-border, #27273a);
    }

    .form-section:last-child {
      border-bottom: none;
      margin-bottom: 0;
    }

    .section-title {
      font-size: 14px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--eog-text-muted, #a1a1aa);
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .section-title.secrets {
      color: var(--eog-warning, #fbbf24);
    }

    .form-group {
      margin-bottom: 16px;
    }

    label {
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: var(--eog-text-muted, #a1a1aa);
      margin-bottom: 6px;
    }

    label.required::after {
      content: ' *';
      color: var(--eog-danger, #ef4444);
    }

    input, select, textarea {
      width: 100%;
      padding: 10px 14px;
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 8px;
      background: var(--eog-input-bg, #0f0f1a);
      color: var(--eog-text, #e4e4e7);
      font-size: 14px;
      transition: border-color 0.2s, box-shadow 0.2s;
      box-sizing: border-box;
    }

    input:focus, select:focus, textarea:focus {
      outline: none;
      border-color: var(--eog-primary, #6366f1);
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
    }

    input.error, select.error {
      border-color: var(--eog-danger, #ef4444);
    }

    .error-message {
      color: var(--eog-danger, #ef4444);
      font-size: 12px;
      margin-top: 4px;
    }

    .help-text {
      color: var(--eog-text-muted, #71717a);
      font-size: 12px;
      margin-top: 4px;
    }

    .vault-indicator {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(251, 191, 36, 0.1);
      color: var(--eog-warning, #fbbf24);
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      margin-left: 8px;
    }

    .secret-field {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .secret-field input {
      flex: 1;
    }

    .btn-icon {
      padding: 10px;
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 8px;
      background: transparent;
      color: var(--eog-text-muted, #a1a1aa);
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-icon:hover {
      background: var(--eog-border, #27273a);
      color: var(--eog-text, #e4e4e7);
    }

    .array-field {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .array-item {
      display: flex;
      gap: 8px;
    }

    .array-item input {
      flex: 1;
    }

    .btn-add {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 12px;
      border: 1px dashed var(--eog-border, #27273a);
      border-radius: 8px;
      background: transparent;
      color: var(--eog-primary, #6366f1);
      cursor: pointer;
      font-size: 13px;
      transition: all 0.2s;
    }

    .btn-add:hover {
      border-color: var(--eog-primary, #6366f1);
      background: rgba(99, 102, 241, 0.1);
    }

    .checkbox-group {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
    }

    .checkbox-item {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .checkbox-item input[type="checkbox"] {
      width: auto;
      accent-color: var(--eog-primary, #6366f1);
    }

    .scope-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 8px;
    }

    .scope-tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      background: var(--eog-primary-muted, rgba(99, 102, 241, 0.2));
      color: var(--eog-primary, #6366f1);
      border-radius: 16px;
      font-size: 12px;
    }

    .scope-tag button {
      background: none;
      border: none;
      color: inherit;
      cursor: pointer;
      padding: 0;
      font-size: 14px;
      line-height: 1;
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 24px;
      padding-top: 24px;
      border-top: 1px solid var(--eog-border, #27273a);
    }

    .btn {
      padding: 10px 20px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }

    .btn-secondary {
      background: transparent;
      border: 1px solid var(--eog-border, #27273a);
      color: var(--eog-text, #e4e4e7);
    }

    .btn-secondary:hover {
      background: var(--eog-border, #27273a);
    }

    .btn-primary {
      background: var(--eog-primary, #6366f1);
      border: none;
      color: white;
    }

    .btn-primary:hover {
      background: var(--eog-primary-hover, #4f46e5);
    }

    .btn-primary:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .btn-test {
      background: var(--eog-success-muted, rgba(34, 197, 94, 0.2));
      border: 1px solid var(--eog-success, #22c55e);
      color: var(--eog-success, #22c55e);
    }

    .btn-test:hover {
      background: var(--eog-success, #22c55e);
      color: white;
    }

    .provider-type-selector {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }

    .provider-option {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 16px;
      border: 2px solid var(--eog-border, #27273a);
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.2s;
    }

    .provider-option:hover {
      border-color: var(--eog-primary, #6366f1);
    }

    .provider-option.selected {
      border-color: var(--eog-primary, #6366f1);
      background: rgba(99, 102, 241, 0.1);
    }

    .provider-icon {
      font-size: 32px;
    }

    .provider-name {
      font-size: 13px;
      font-weight: 500;
    }
  `;

    constructor() {
        super();
        this.provider = {};
        this.providerType = '';
        this.mode = 'create';
        this.isLoading = false;
        this.errors = {};
        this.isPlatformLevel = true;
        this._redirectUris = [''];
        this._jsOrigins = [''];
        this._scopes = ['openid', 'email', 'profile'];
    }

    // Provider type configurations
    get providerConfigs() {
        return {
            google: {
                name: 'Google OAuth',
                icon: '🔵',
                defaultAuthUri: 'https://accounts.google.com/o/oauth2/auth',
                defaultTokenUri: 'https://oauth2.googleapis.com/token',
                defaultCertsUrl: 'https://www.googleapis.com/oauth2/v1/certs',
                defaultScopes: ['openid', 'email', 'profile'],
                fields: ['client_id', 'project_id', 'client_secret', 'auth_uri', 'token_uri', 'certs_url', 'redirect_uris', 'javascript_origins']
            },
            facebook: {
                name: 'Facebook OAuth',
                icon: '🔷',
                defaultAuthUri: 'https://www.facebook.com/v18.0/dialog/oauth',
                defaultTokenUri: 'https://graph.facebook.com/v18.0/oauth/access_token',
                defaultCertsUrl: '',
                defaultScopes: ['email', 'public_profile'],
                fields: ['client_id', 'client_secret', 'auth_uri', 'token_uri', 'redirect_uris']
            },
            github: {
                name: 'GitHub OAuth',
                icon: '⚫',
                defaultAuthUri: 'https://github.com/login/oauth/authorize',
                defaultTokenUri: 'https://github.com/login/oauth/access_token',
                defaultCertsUrl: '',
                defaultScopes: ['read:user', 'user:email'],
                fields: ['client_id', 'client_secret', 'auth_uri', 'token_uri', 'redirect_uris']
            },
            keycloak: {
                name: 'Keycloak',
                icon: '🔐',
                defaultAuthUri: '',
                defaultTokenUri: '',
                defaultCertsUrl: '',
                defaultScopes: ['openid', 'email', 'profile'],
                fields: ['client_id', 'client_secret', 'auth_uri', 'token_uri', 'certs_url', 'redirect_uris']
            },
            oidc: {
                name: 'Generic OIDC',
                icon: '🔗',
                defaultAuthUri: '',
                defaultTokenUri: '',
                defaultCertsUrl: '',
                defaultScopes: ['openid', 'email', 'profile'],
                fields: ['client_id', 'client_secret', 'auth_uri', 'token_uri', 'certs_url', 'redirect_uris', 'javascript_origins']
            }
        };
    }

    _selectProviderType(type) {
        this.providerType = type;
        const config = this.providerConfigs[type];
        if (config) {
            this.provider = {
                ...this.provider,
                provider_type: type,
                auth_uri: config.defaultAuthUri,
                token_uri: config.defaultTokenUri,
                certs_url: config.defaultCertsUrl,
            };
            this._scopes = [...config.defaultScopes];
        }
        this.requestUpdate();
    }

    _handleInput(e) {
        const { name, value, type, checked } = e.target;
        this.provider = {
            ...this.provider,
            [name]: type === 'checkbox' ? checked : value
        };
    }

    _addRedirectUri() {
        this._redirectUris = [...this._redirectUris, ''];
        this.requestUpdate();
    }

    _removeRedirectUri(index) {
        this._redirectUris = this._redirectUris.filter((_, i) => i !== index);
        this.requestUpdate();
    }

    _updateRedirectUri(index, value) {
        this._redirectUris[index] = value;
        this.requestUpdate();
    }

    _addScope(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const value = e.target.value.trim();
            if (value && !this._scopes.includes(value)) {
                this._scopes = [...this._scopes, value];
                e.target.value = '';
                this.requestUpdate();
            }
        }
    }

    _removeScope(scope) {
        this._scopes = this._scopes.filter(s => s !== scope);
        this.requestUpdate();
    }

    _testConnection() {
        this.dispatchEvent(new CustomEvent('test-connection', {
            detail: { provider: this._buildProvider() }
        }));
    }

    _buildProvider() {
        return {
            ...this.provider,
            redirect_uris: this._redirectUris.filter(u => u.trim()),
            javascript_origins: this._jsOrigins.filter(o => o.trim()),
            default_scopes: this._scopes,
        };
    }

    _handleSubmit() {
        this.dispatchEvent(new CustomEvent('submit', {
            detail: { provider: this._buildProvider() }
        }));
    }

    _handleCancel() {
        this.dispatchEvent(new CustomEvent('cancel'));
    }

    render() {
        return html`
      <div class="form-container">
        ${this.mode === 'create' ? this._renderProviderSelector() : ''}
        
        ${this.providerType ? html`
          <!-- Basic Configuration -->
          <div class="form-section">
            <div class="section-title">Basic Configuration</div>
            
            <div class="form-group">
              <label class="required">Provider Name</label>
              <input
                type="text"
                name="name"
                .value=${this.provider.name || ''}
                @input=${this._handleInput}
                placeholder="e.g., Google OAuth Production"
                class=${this.errors.name ? 'error' : ''}
              />
              ${this.errors.name ? html`<div class="error-message">${this.errors.name}</div>` : ''}
            </div>

            <div class="form-group">
              <label class="required">Client ID</label>
              <input
                type="text"
                name="client_id"
                .value=${this.provider.client_id || ''}
                @input=${this._handleInput}
                placeholder="Your OAuth client ID"
              />
            </div>

            ${this.providerType === 'google' ? html`
              <div class="form-group">
                <label>Project ID</label>
                <input
                  type="text"
                  name="project_id"
                  .value=${this.provider.project_id || ''}
                  @input=${this._handleInput}
                  placeholder="e.g., gen-lang-client-0525903828"
                />
              </div>
            ` : ''}
          </div>

          <!-- Secrets (Vault) -->
          <div class="form-section">
            <div class="section-title secrets">
              🔒 Secrets
              <span class="vault-indicator">🔐 Stored in Vault</span>
            </div>
            
            <div class="form-group">
              <label class="required">Client Secret</label>
              <div class="secret-field">
                <input
                  type="password"
                  name="client_secret"
                  .value=${this.provider.client_secret || ''}
                  @input=${this._handleInput}
                  placeholder="••••••••••••••••"
                />
                <button class="btn-icon" title="Show/Hide">👁️</button>
                <button class="btn-icon" title="Rotate">🔄</button>
              </div>
              <div class="help-text">
                Vault Path: vault://secrets/oauth/${this.providerType}/client_secret
              </div>
            </div>
          </div>

          <!-- Endpoints -->
          <div class="form-section">
            <div class="section-title">Endpoints</div>
            
            <div class="form-group">
              <label class="required">Auth URI</label>
              <input
                type="url"
                name="auth_uri"
                .value=${this.provider.auth_uri || ''}
                @input=${this._handleInput}
                placeholder="https://..."
              />
            </div>

            <div class="form-group">
              <label class="required">Token URI</label>
              <input
                type="url"
                name="token_uri"
                .value=${this.provider.token_uri || ''}
                @input=${this._handleInput}
                placeholder="https://..."
              />
            </div>

            <div class="form-group">
              <label>Certificates URL</label>
              <input
                type="url"
                name="certs_url"
                .value=${this.provider.certs_url || ''}
                @input=${this._handleInput}
                placeholder="https://..."
              />
            </div>
          </div>

          <!-- Redirect URIs -->
          <div class="form-section">
            <div class="section-title">Redirect URIs</div>
            
            <div class="array-field">
              ${this._redirectUris.map((uri, i) => html`
                <div class="array-item">
                  <input
                    type="url"
                    .value=${uri}
                    @input=${(e) => this._updateRedirectUri(i, e.target.value)}
                    placeholder="http://localhost:5173/auth/callback"
                  />
                  ${this._redirectUris.length > 1 ? html`
                    <button class="btn-icon" @click=${() => this._removeRedirectUri(i)}>✕</button>
                  ` : ''}
                </div>
              `)}
              <button class="btn-add" @click=${this._addRedirectUri}>
                + Add Redirect URI
              </button>
            </div>
          </div>

          <!-- Scopes -->
          <div class="form-section">
            <div class="section-title">Scopes & Claims</div>
            
            <div class="form-group">
              <label>Default Scopes</label>
              <div class="scope-tags">
                ${this._scopes.map(scope => html`
                  <span class="scope-tag">
                    ${scope}
                    <button @click=${() => this._removeScope(scope)}>✕</button>
                  </span>
                `)}
              </div>
              <input
                type="text"
                placeholder="Type and press Enter to add scope"
                @keydown=${this._addScope}
              />
            </div>
          </div>

          <!-- Status -->
          <div class="form-section">
            <div class="section-title">Status</div>
            
            <div class="checkbox-group">
              <label class="checkbox-item">
                <input
                  type="checkbox"
                  name="is_enabled"
                  ?checked=${this.provider.is_enabled !== false}
                  @change=${this._handleInput}
                />
                Enabled
              </label>
              <label class="checkbox-item">
                <input
                  type="checkbox"
                  name="is_default"
                  ?checked=${this.provider.is_default}
                  @change=${this._handleInput}
                />
                Default Provider
              </label>
              <label class="checkbox-item">
                <input
                  type="checkbox"
                  name="trust_email"
                  ?checked=${this.provider.trust_email !== false}
                  @change=${this._handleInput}
                />
                Trust Email
              </label>
              <label class="checkbox-item">
                <input
                  type="checkbox"
                  name="store_token"
                  ?checked=${this.provider.store_token !== false}
                  @change=${this._handleInput}
                />
                Store Token
              </label>
            </div>
          </div>

          <!-- Actions -->
          <div class="form-actions">
            <button class="btn btn-test" @click=${this._testConnection}>
              🔌 Test Connection
            </button>
            <button class="btn btn-secondary" @click=${this._handleCancel}>
              Cancel
            </button>
            <button 
              class="btn btn-primary" 
              @click=${this._handleSubmit}
              ?disabled=${this.isLoading}
            >
              ${this.isLoading ? '⏳' : '💾'} 
              ${this.mode === 'create' ? 'Create Provider' : 'Save Changes'}
            </button>
          </div>
        ` : ''}
      </div>
    `;
    }

    _renderProviderSelector() {
        return html`
      <div class="form-section">
        <div class="section-title">Select Provider Type</div>
        <div class="provider-type-selector">
          ${Object.entries(this.providerConfigs).map(([type, config]) => html`
            <div 
              class="provider-option ${this.providerType === type ? 'selected' : ''}"
              @click=${() => this._selectProviderType(type)}
            >
              <span class="provider-icon">${config.icon}</span>
              <span class="provider-name">${config.name}</span>
            </div>
          `)}
        </div>
      </div>
    `;
    }
}

customElements.define('eog-oauth-provider-form', EogOauthProviderForm);
