/**
 * Tenant Create View
 * Route: /platform/tenants/new
 * 
 * Form for creating a new tenant.
 * 
 * VIBE PERSONAS:
 * - 🔒 Security: Validated input
 * - 🏛️ Architect: Clean form patterns
 * - 🎨 UX: Clear feedback on submit
 */

import { LitElement, html, css } from 'lit';
import { tenantsApi, tiersApi } from '../services/api.js';

export class EogTenantCreate extends LitElement {
    static properties = {
        formData: { type: Object },
        tiers: { type: Array },
        isSubmitting: { type: Boolean },
        error: { type: String },
    };

    static styles = css`
    :host {
      display: block;
      max-width: 600px;
      margin: 0 auto;
    }

    h1 {
      margin: 0 0 24px 0;
      font-size: 24px;
      color: var(--eog-text, #e4e4e7);
    }

    .card {
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      padding: 24px;
    }

    .form-group {
      margin-bottom: 20px;
    }

    label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      color: var(--eog-text-secondary, #a1a1aa);
      margin-bottom: 8px;
    }

    input, select {
      width: 100%;
      padding: 12px;
      background: var(--eog-bg, #09090b);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 8px;
      color: var(--eog-text, #e4e4e7);
      font-size: 14px;
      box-sizing: border-box;
    }

    input:focus, select:focus {
      outline: none;
      border-color: var(--eog-primary, #6366f1);
    }

    .error {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      border-radius: 8px;
      padding: 12px;
      color: #ef4444;
      margin-bottom: 16px;
    }

    .actions {
      display: flex;
      gap: 12px;
      justify-content: flex-end;
      margin-top: 24px;
    }

    .btn {
      padding: 12px 24px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      border: none;
    }

    .btn-secondary {
      background: transparent;
      border: 1px solid var(--eog-border, #27273a);
      color: var(--eog-text, #e4e4e7);
    }

    .btn-primary {
      background: var(--eog-primary, #6366f1);
      color: white;
    }

    .btn-primary:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  `;

    constructor() {
        super();
        this.formData = {
            name: '',
            slug: '',
            tier_id: '',
        };
        this.tiers = [];
        this.isSubmitting = false;
        this.error = null;
    }

    connectedCallback() {
        super.connectedCallback();
        this._loadTiers();
    }

    async _loadTiers() {
        try {
            const result = await tiersApi.list();
            this.tiers = result.tiers || result || [];
        } catch (err) {
            console.error('Failed to load tiers:', err);
        }
    }

    _updateField(field, value) {
        this.formData = { ...this.formData, [field]: value };

        // Auto-generate slug from name
        if (field === 'name') {
            this.formData.slug = value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
        }
    }

    async _handleSubmit(e) {
        e.preventDefault();
        this.isSubmitting = true;
        this.error = null;

        try {
            await tenantsApi.create(this.formData);
            // Navigate back to tenant list
            window.history.pushState({}, '', '/platform/tenants');
            window.dispatchEvent(new PopStateEvent('popstate'));
        } catch (err) {
            console.error('Failed to create tenant:', err);
            this.error = err.message;
        } finally {
            this.isSubmitting = false;
        }
    }

    _handleCancel() {
        window.history.pushState({}, '', '/platform/tenants');
        window.dispatchEvent(new PopStateEvent('popstate'));
    }

    render() {
        return html`
      <h1>Create New Tenant</h1>

      <div class="card">
        ${this.error ? html`<div class="error">${this.error}</div>` : ''}

        <form @submit=${this._handleSubmit}>
          <div class="form-group">
            <label>Organization Name *</label>
            <input 
              type="text" 
              .value=${this.formData.name}
              @input=${e => this._updateField('name', e.target.value)}
              placeholder="Acme Corporation"
              required
            >
          </div>

          <div class="form-group">
            <label>Slug (URL identifier)</label>
            <input 
              type="text" 
              .value=${this.formData.slug}
              @input=${e => this._updateField('slug', e.target.value)}
              placeholder="acme-corp"
            >
          </div>

          <div class="form-group">
            <label>Subscription Tier *</label>
            <select 
              .value=${this.formData.tier_id}
              @change=${e => this._updateField('tier_id', e.target.value)}
              required
            >
              <option value="">Select a tier...</option>
              ${this.tiers.map(tier => html`
                <option value=${tier.id}>${tier.name}</option>
              `)}
            </select>
          </div>

          <div class="actions">
            <button type="button" class="btn btn-secondary" @click=${this._handleCancel}>
              Cancel
            </button>
            <button type="submit" class="btn btn-primary" ?disabled=${this.isSubmitting}>
              ${this.isSubmitting ? 'Creating...' : 'Create Tenant'}
            </button>
          </div>
        </form>
      </div>
    `;
    }
}

customElements.define('eog-tenant-create', EogTenantCreate);
