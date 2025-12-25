/**
 * Tier Builder View (Screen 9)
 * Route: /platform/subscriptions/:id
 * 
 * Edit subscription tier details and feature sets.
 */

import { LitElement, html, css } from 'lit';
import { tiersApi } from '../services/api.js';
import '../components/billing/eog-feature-toggle.js';

export class EogTierBuilder extends LitElement {
    static properties = {
        tierId: { type: String },
        tier: { type: Object },
        isLoading: { type: Boolean },
        isSaving: { type: Boolean },
    };

    static styles = css`
    :host {
      display: block;
      max-width: 800px;
      margin: 0 auto;
    }

    .card {
      background: var(--eog-surface, #1a1a2e);
      border-radius: 12px;
      border: 1px solid var(--eog-border, #27273a);
      padding: 32px;
    }

    h1 {
      margin: 0 0 24px 0;
      font-size: 24px;
      color: var(--eog-text, #e4e4e7);
    }

    .form-group {
      margin-bottom: 24px;
    }

    label {
      display: block;
      margin-bottom: 8px;
      font-size: 14px;
      font-weight: 500;
      color: var(--eog-text-secondary, #a1a1aa);
    }

    input, textarea, select {
      width: 100%;
      padding: 10px 12px;
      background: var(--eog-bg, #09090b);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 8px;
      color: var(--eog-text, #e4e4e7);
      font-size: 14px;
      box-sizing: border-box;
    }

    input:focus, textarea:focus {
      outline: none;
      border-color: var(--eog-primary, #6366f1);
    }

    .row {
      display: flex;
      gap: 20px;
    }

    .col {
      flex: 1;
    }

    .section-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--eog-text, #e4e4e7);
      margin: 32px 0 16px 0;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--eog-border, #27273a);
    }

    .actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 40px;
      padding-top: 24px;
      border-top: 1px solid var(--eog-border, #27273a);
    }

    .btn {
      padding: 10px 24px;
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
  `;

    constructor() {
        super();
        this.tier = {
            name: '',
            code: '',
            price: 0,
            features: []
        };
        this.isLoading = false;
        this.isSaving = false;
    }

    connectedCallback() {
        super.connectedCallback();
        if (this.location?.params?.id && this.location.params.id !== 'new') {
            this.tierId = this.location.params.id;
            this._loadTier();
        }
    }

    async _loadTier() {
        this.isLoading = true;
        try {
            this.tier = await tiersApi.get(this.tierId);
        } catch (err) {
            console.error(err);
        } finally {
            this.isLoading = false;
        }
    }

    async _handleSave() {
        this.isSaving = true;
        try {
            if (this.tierId) {
                await tiersApi.update(this.tierId, this.tier);
            } else {
                await tiersApi.create(this.tier);
            }
            this._navigateBack();
        } catch (err) {
            console.error(err);
            alert('Failed to save tier');
        } finally {
            this.isSaving = false;
        }
    }

    _navigateBack() {
        this.dispatchEvent(new CustomEvent('navigate', {
            detail: { path: '/platform/subscriptions' },
            bubbles: true,
            composed: true
        }));
    }

    _updateField(e) {
        const field = e.target.dataset.field;
        const val = e.target.type === 'number' ? parseFloat(e.target.value) : e.target.value;
        this.tier = { ...this.tier, [field]: val };
    }

    render() {
        if (this.isLoading) return html`<div>Loading...</div>`;

        return html`
      <div class="card">
        <h1>${this.tierId ? 'Edit Tier' : 'Create New Tier'}</h1>

        <div class="row">
          <div class="col form-group">
            <label>Name</label>
            <input type="text" .value=${this.tier.name} data-field="name" @input=${this._updateField} placeholder="e.g. Pro Plan">
          </div>
          <div class="col form-group">
            <label>Code</label>
            <input type="text" .value=${this.tier.code} data-field="code" @input=${this._updateField} placeholder="e.g. pro_v1">
          </div>
        </div>

        <div class="row">
          <div class="col form-group">
            <label>Monthly Price ($)</label>
            <input type="number" .value=${this.tier.price} data-field="price" @input=${this._updateField}>
          </div>
          <div class="col form-group">
            <label>Lago Plan Code (Sync)</label>
            <input type="text" .value=${this.tier.lago_code || ''} data-field="lago_code" @input=${this._updateField} placeholder="Sync with billing">
          </div>
        </div>

        <div class="section-title">Limits</div>
        <div class="row">
          <div class="col form-group">
            <label>Max Users (-1 for unlimited)</label>
            <input type="number" .value=${this.tier.max_users || 0} data-field="max_users" @input=${this._updateField}>
          </div>
          <div class="col form-group">
            <label>Max Agents</label>
            <input type="number" .value=${this.tier.max_agents || 0} data-field="max_agents" @input=${this._updateField}>
          </div>
        </div>

        <div class="section-title">Features</div>
        <!-- Feature toggles placeholder - normally would load all available features -->
        <p style="color:var(--eog-text-muted);font-size:14px;">Manage specific feature flags in the Features tab.</p>

        <div class="actions">
          <button class="btn btn-secondary" @click=${this._navigateBack}>Cancel</button>
          <button class="btn btn-primary" ?disabled=${this.isSaving} @click=${this._handleSave}>
            ${this.isSaving ? 'Saving...' : 'Save Tier'}
          </button>
        </div>
      </div>
    `;
    }
}

customElements.define('eog-tier-builder', EogTierBuilder);
