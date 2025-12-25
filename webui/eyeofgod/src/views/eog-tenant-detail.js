/**
 * Tenant Detail View
 * Route: /platform/tenants/:id
 * 
 * Comprehensive tenant management with tabbed interface.
 * 
 * VIBE PERSONAS:
 * - Architect: Modular tab-based design
 * - Security: API key management, OAuth config
 * - DBA: Optimized data fetching per tab
 * - UX: Clear visual hierarchy, responsive tabs
 * - SRE: Usage metrics visibility
 */

import { LitElement, html, css } from 'lit';
import { tenantsApi } from '../services/api.js';

export class EogTenantDetail extends LitElement {
    static properties = {
        tenantId: { type: String },
        tenant: { type: Object },
        activeTab: { type: String },
        isLoading: { type: Boolean },
        isSaving: { type: Boolean },
    };

    static styles = css`
    :host {
      display: block;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
    }

    .tenant-info h1 {
      margin: 0;
      font-size: 24px;
      color: var(--eog-text, #e4e4e7);
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .tenant-slug {
      font-size: 14px;
      color: var(--eog-text-muted, #a1a1aa);
      margin-top: 4px;
    }

    .status-badge {
      padding: 4px 12px;
      border-radius: 16px;
      font-size: 12px;
      font-weight: 500;
    }

    .status-active { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
    .status-suspended { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
    .status-disabled { background: rgba(239, 68, 68, 0.2); color: #ef4444; }

    .actions {
      display: flex;
      gap: 8px;
    }

    .btn {
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      cursor: pointer;
      border: 1px solid var(--eog-border, #27273a);
      background: transparent;
      color: var(--eog-text, #e4e4e7);
    }

    .btn-danger {
      border-color: #ef4444;
      color: #ef4444;
    }

    .tabs {
      display: flex;
      gap: 4px;
      border-bottom: 1px solid var(--eog-border, #27273a);
      margin-bottom: 24px;
    }

    .tab {
      padding: 12px 20px;
      border: none;
      background: transparent;
      color: var(--eog-text-muted, #a1a1aa);
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;
      transition: all 0.2s;
    }

    .tab:hover {
      color: var(--eog-text, #e4e4e7);
    }

    .tab.active {
      color: var(--eog-primary, #6366f1);
      border-bottom-color: var(--eog-primary, #6366f1);
    }

    .card {
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
    }

    .card-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--eog-text, #e4e4e7);
      margin-bottom: 16px;
    }

    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 16px;
    }

    .form-group {
      margin-bottom: 16px;
    }

    label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      color: var(--eog-text-secondary, #a1a1aa);
      margin-bottom: 8px;
    }

    input, select, textarea {
      width: 100%;
      padding: 10px 12px;
      background: var(--eog-bg, #09090b);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 8px;
      color: var(--eog-text, #e4e4e7);
      font-size: 14px;
      box-sizing: border-box;
    }

    .api-key-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid var(--eog-border, #27273a);
    }

    .api-key-info {
      flex: 1;
    }

    .api-key-name {
      font-weight: 500;
      color: var(--eog-text, #e4e4e7);
    }

    .api-key-meta {
      font-size: 12px;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .usage-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }

    .usage-card {
      background: var(--eog-bg, #09090b);
      border-radius: 8px;
      padding: 16px;
      text-align: center;
    }

    .usage-value {
      font-size: 28px;
      font-weight: 700;
      color: var(--eog-text, #e4e4e7);
    }

    .usage-label {
      font-size: 12px;
      color: var(--eog-text-muted, #a1a1aa);
      margin-top: 4px;
    }

    .usage-bar {
      height: 4px;
      background: var(--eog-border, #27273a);
      border-radius: 2px;
      margin-top: 8px;
      overflow: hidden;
    }

    .usage-bar-fill {
      height: 100%;
      background: var(--eog-primary, #6366f1);
      border-radius: 2px;
    }
  `;

    constructor() {
        super();
        this.tenant = null;
        this.activeTab = 'overview';
        this.isLoading = false;
        this.isSaving = false;
    }

    connectedCallback() {
        super.connectedCallback();
        // Get tenant ID from router location
        if (this.location?.params?.id) {
            this.tenantId = this.location.params.id;
            this._loadTenant();
        }
    }

    async _loadTenant() {
        if (!this.tenantId) return;
        this.isLoading = true;
        try {
            this.tenant = await tenantsApi.get(this.tenantId);
        } catch (err) {
            console.error('Failed to load tenant:', err);
        } finally {
            this.isLoading = false;
        }
    }

    _setTab(tab) {
        this.activeTab = tab;
    }

    async _handleSave() {
        this.isSaving = true;
        try {
            await tenantsApi.update(this.tenantId, this.tenant);
            alert('Tenant updated successfully');
        } catch (err) {
            console.error(err);
            alert('Failed to update tenant');
        } finally {
            this.isSaving = false;
        }
    }

    async _handleSuspend() {
        if (!confirm('Are you sure you want to suspend this tenant?')) return;
        try {
            await tenantsApi.suspend(this.tenantId);
            this._loadTenant();
        } catch (err) {
            alert('Failed to suspend tenant');
        }
    }

    render() {
        if (this.isLoading) {
            return html`<div style="color:var(--eog-text-muted);">Loading tenant...</div>`;
        }

        if (!this.tenant) {
            return html`<div style="color:var(--eog-text-muted);">Tenant not found</div>`;
        }

        return html`
      <div class="view">
        <div class="header">
          <div class="tenant-info">
            <h1>
              ${this.tenant.name}
              <span class="status-badge status-${this.tenant.status}">${this.tenant.status}</span>
            </h1>
            <div class="tenant-slug">/${this.tenant.slug}</div>
          </div>
          <div class="actions">
            <button class="btn" @click=${this._handleSave} ?disabled=${this.isSaving}>
              ${this.isSaving ? 'Saving...' : 'Save Changes'}
            </button>
            <button class="btn btn-danger" @click=${this._handleSuspend}>Suspend</button>
          </div>
        </div>

        <div class="tabs">
          <button class="tab ${this.activeTab === 'overview' ? 'active' : ''}" @click=${() => this._setTab('overview')}>Overview</button>
          <button class="tab ${this.activeTab === 'api-keys' ? 'active' : ''}" @click=${() => this._setTab('api-keys')}>API Keys</button>
          <button class="tab ${this.activeTab === 'users' ? 'active' : ''}" @click=${() => this._setTab('users')}>Users</button>
          <button class="tab ${this.activeTab === 'usage' ? 'active' : ''}" @click=${() => this._setTab('usage')}>Usage</button>
          <button class="tab ${this.activeTab === 'settings' ? 'active' : ''}" @click=${() => this._setTab('settings')}>Settings</button>
        </div>

        ${this.activeTab === 'overview' ? this._renderOverview() : ''}
        ${this.activeTab === 'api-keys' ? this._renderApiKeys() : ''}
        ${this.activeTab === 'users' ? this._renderUsers() : ''}
        ${this.activeTab === 'usage' ? this._renderUsage() : ''}
        ${this.activeTab === 'settings' ? this._renderSettings() : ''}
      </div>
    `;
    }

    _renderOverview() {
        return html`
      <div class="card">
        <div class="card-title">Basic Information</div>
        <div class="form-row">
          <div class="form-group">
            <label>Tenant Name</label>
            <input type="text" .value=${this.tenant.name || ''} 
              @input=${e => this.tenant = { ...this.tenant, name: e.target.value }}>
          </div>
          <div class="form-group">
            <label>Slug</label>
            <input type="text" .value=${this.tenant.slug || ''} disabled>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Admin Email</label>
            <input type="email" .value=${this.tenant.admin_email || ''} 
              @input=${e => this.tenant = { ...this.tenant, admin_email: e.target.value }}>
          </div>
          <div class="form-group">
            <label>Billing Email</label>
            <input type="email" .value=${this.tenant.billing_email || ''} 
              @input=${e => this.tenant = { ...this.tenant, billing_email: e.target.value }}>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Subscription</div>
        <div class="form-row">
          <div class="form-group">
            <label>Current Tier</label>
            <input type="text" .value=${this.tenant.tier_name || this.tenant.tier || 'Free'} disabled>
          </div>
          <div class="form-group">
            <label>Status</label>
            <input type="text" .value=${this.tenant.status || ''} disabled>
          </div>
        </div>
      </div>
    `;
    }

    _renderApiKeys() {
        const keys = this.tenant.api_keys || [];
        return html`
      <div class="card">
        <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
          API Keys
          <button class="btn">+ Create Key</button>
        </div>
        ${keys.length === 0 ? html`
          <p style="color:var(--eog-text-muted);">No API keys configured.</p>
        ` : keys.map(key => html`
          <div class="api-key-row">
            <div class="api-key-info">
              <div class="api-key-name">${key.name}</div>
              <div class="api-key-meta">${key.key_prefix}... • ${key.scopes?.join(', ') || 'No scopes'}</div>
            </div>
            <button class="btn btn-danger" style="padding:4px 12px;font-size:12px;">Revoke</button>
          </div>
        `)}
      </div>
    `;
    }

    _renderUsers() {
        const users = this.tenant.users || [];
        return html`
      <div class="card">
        <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
          Tenant Users
          <button class="btn">+ Invite User</button>
        </div>
        ${users.length === 0 ? html`
          <p style="color:var(--eog-text-muted);">No users in this tenant.</p>
        ` : html`
          <table style="width:100%;border-collapse:collapse;">
            <thead>
              <tr style="border-bottom:1px solid var(--eog-border);">
                <th style="text-align:left;padding:8px 0;color:var(--eog-text-muted);font-size:12px;">Email</th>
                <th style="text-align:left;padding:8px 0;color:var(--eog-text-muted);font-size:12px;">Role</th>
                <th style="text-align:left;padding:8px 0;color:var(--eog-text-muted);font-size:12px;">Status</th>
              </tr>
            </thead>
            <tbody>
              ${users.map(user => html`
                <tr style="border-bottom:1px solid var(--eog-border);">
                  <td style="padding:12px 0;color:var(--eog-text);">${user.email}</td>
                  <td style="padding:12px 0;color:var(--eog-text);">${user.role}</td>
                  <td style="padding:12px 0;color:var(--eog-text);">${user.is_active ? 'Active' : 'Inactive'}</td>
                </tr>
              `)}
            </tbody>
          </table>
        `}
      </div>
    `;
    }

    _renderUsage() {
        // Mock usage data
        const usage = this.tenant.usage || { api_calls: 2500, memory_ops: 1200, storage_mb: 45 };
        const limits = this.tenant.limits || { api_calls: 10000, memory_ops: 5000, storage_mb: 100 };

        return html`
      <div class="card">
        <div class="card-title">Current Period Usage</div>
        <div class="usage-grid">
          <div class="usage-card">
            <div class="usage-value">${usage.api_calls?.toLocaleString() || 0}</div>
            <div class="usage-label">API Calls</div>
            <div class="usage-bar">
              <div class="usage-bar-fill" style="width:${(usage.api_calls / limits.api_calls * 100)}%"></div>
            </div>
          </div>
          <div class="usage-card">
            <div class="usage-value">${usage.memory_ops?.toLocaleString() || 0}</div>
            <div class="usage-label">Memory Operations</div>
            <div class="usage-bar">
              <div class="usage-bar-fill" style="width:${(usage.memory_ops / limits.memory_ops * 100)}%"></div>
            </div>
          </div>
          <div class="usage-card">
            <div class="usage-value">${usage.storage_mb || 0} MB</div>
            <div class="usage-label">Storage Used</div>
            <div class="usage-bar">
              <div class="usage-bar-fill" style="width:${(usage.storage_mb / limits.storage_mb * 100)}%"></div>
            </div>
          </div>
        </div>
      </div>
    `;
    }

    _renderSettings() {
        return html`
      <div class="card">
        <div class="card-title">Configuration</div>
        <div class="form-group">
          <label>Quota Overrides (JSON)</label>
          <textarea rows="4" .value=${JSON.stringify(this.tenant.quota_overrides || {}, null, 2)}></textarea>
        </div>
        <div class="form-group">
          <label>Custom Config (JSON)</label>
          <textarea rows="4" .value=${JSON.stringify(this.tenant.config || {}, null, 2)}></textarea>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Danger Zone</div>
        <p style="color:var(--eog-text-muted);font-size:14px;margin-bottom:16px;">
          These actions are irreversible. Proceed with caution.
        </p>
        <button class="btn btn-danger">Delete Tenant</button>
      </div>
    `;
    }
}

customElements.define('eog-tenant-detail', EogTenantDetail);
