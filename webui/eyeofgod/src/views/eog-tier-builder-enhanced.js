/**
 * Eye of God - Subscription Tier Builder
 * 
 * Visual tier/plan builder for SaaS subscriptions
 * Connects to Django Ninja /saas/tiers/ endpoint
 * 
 * VIBE COMPLIANT - ALL 10 PERSONAS
 */

import { LitElement, html, css } from 'lit';

export class EogTierBuilderEnhanced extends LitElement {
    static properties = {
        tiers: { type: Array },
        editing: { type: Object },
        showForm: { type: Boolean },
        loading: { type: Boolean },
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

    .header h1 {
      font-size: 24px;
      font-weight: 700;
      color: var(--text-primary, #111);
      margin: 0;
    }

    .btn-add {
      padding: 12px 20px;
      background: var(--accent, #4f46e5);
      color: white;
      border: none;
      border-radius: var(--radius-lg, 12px);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .tiers-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 24px;
    }

    .tier-card {
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-xl, 16px);
      padding: 28px;
      position: relative;
      transition: all 0.2s ease;
    }

    .tier-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 20px 50px -12px rgba(0, 0, 0, 0.15);
    }

    .tier-card.popular {
      border: 2px solid var(--accent, #4f46e5);
    }

    .popular-badge {
      position: absolute;
      top: -12px;
      left: 50%;
      transform: translateX(-50%);
      background: var(--accent, #4f46e5);
      color: white;
      padding: 4px 16px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
    }

    .tier-icon {
      width: 56px;
      height: 56px;
      border-radius: var(--radius-lg, 12px);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      margin-bottom: 16px;
    }

    .tier-icon.free { background: rgba(107, 114, 128, 0.1); }
    .tier-icon.starter { background: rgba(59, 130, 246, 0.1); }
    .tier-icon.pro { background: rgba(168, 85, 247, 0.1); }
    .tier-icon.enterprise { background: rgba(34, 197, 94, 0.1); }

    .tier-name {
      font-size: 20px;
      font-weight: 700;
      color: var(--text-primary, #111);
      margin-bottom: 8px;
    }

    .tier-price {
      display: flex;
      align-items: baseline;
      margin-bottom: 20px;
    }

    .price-amount {
      font-size: 36px;
      font-weight: 800;
      color: var(--text-primary, #111);
    }

    .price-period {
      font-size: 14px;
      color: var(--text-tertiary, #888);
      margin-left: 4px;
    }

    .tier-features {
      list-style: none;
      padding: 0;
      margin: 0 0 24px 0;
    }

    .tier-features li {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 0;
      font-size: 14px;
      color: var(--text-secondary, #555);
      border-bottom: 1px solid rgba(0, 0, 0, 0.04);
    }

    .tier-features li:last-child {
      border-bottom: none;
    }

    .feature-check {
      color: #22c55e;
      font-weight: bold;
    }

    .feature-value {
      font-weight: 600;
      color: var(--text-primary, #111);
    }

    .tier-actions {
      display: flex;
      gap: 10px;
    }

    .tier-btn {
      flex: 1;
      padding: 12px;
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-md, 8px);
      background: white;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .tier-btn:hover {
      background: rgba(0, 0, 0, 0.02);
    }

    .tier-btn.primary {
      background: var(--accent, #4f46e5);
      color: white;
      border-color: var(--accent);
    }

    /* Limits display */
    .limits-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      margin: 16px 0;
    }

    .limit-item {
      background: rgba(0, 0, 0, 0.02);
      padding: 12px;
      border-radius: var(--radius-md, 8px);
      text-align: center;
    }

    .limit-value {
      font-size: 18px;
      font-weight: 700;
      color: var(--text-primary, #111);
    }

    .limit-label {
      font-size: 11px;
      color: var(--text-tertiary, #888);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    /* Form Modal */
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .modal {
      background: white;
      border-radius: var(--radius-xl, 16px);
      width: 100%;
      max-width: 560px;
      max-height: 90vh;
      overflow-y: auto;
    }

    .modal-header {
      padding: 24px 24px 0;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .modal-title {
      font-size: 20px;
      font-weight: 600;
      margin: 0;
    }

    .modal-close {
      background: none;
      border: none;
      font-size: 24px;
      cursor: pointer;
      color: var(--text-tertiary, #888);
    }

    .modal-body {
      padding: 24px;
    }

    .form-group {
      margin-bottom: 20px;
    }

    .form-group label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      color: var(--text-secondary, #555);
      margin-bottom: 8px;
    }

    .form-group input,
    .form-group select {
      width: 100%;
      padding: 12px 14px;
      border: 1px solid #e5e7eb;
      border-radius: var(--radius-md, 8px);
      font-size: 14px;
      box-sizing: border-box;
    }

    .form-row {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
    }

    .features-editor {
      border: 1px solid #e5e7eb;
      border-radius: var(--radius-md, 8px);
      padding: 16px;
    }

    .feature-row {
      display: flex;
      gap: 12px;
      margin-bottom: 12px;
      align-items: center;
    }

    .feature-row input {
      flex: 1;
      padding: 8px 12px;
      border: 1px solid #e5e7eb;
      border-radius: 6px;
      font-size: 13px;
    }

    .feature-row button {
      padding: 8px;
      border: none;
      background: rgba(239, 68, 68, 0.1);
      color: #dc2626;
      border-radius: 6px;
      cursor: pointer;
    }

    .add-feature-btn {
      width: 100%;
      padding: 10px;
      border: 1px dashed #e5e7eb;
      background: transparent;
      border-radius: 6px;
      cursor: pointer;
      color: var(--text-tertiary, #888);
      font-size: 13px;
    }

    .modal-footer {
      padding: 16px 24px 24px;
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }

    .btn-cancel {
      padding: 12px 20px;
      border: 1px solid #e5e7eb;
      background: white;
      border-radius: var(--radius-md, 8px);
      font-size: 14px;
      cursor: pointer;
    }

    .btn-save {
      padding: 12px 20px;
      background: var(--accent, #4f46e5);
      color: white;
      border: none;
      border-radius: var(--radius-md, 8px);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    }

    .loading {
      display: flex;
      justify-content: center;
      padding: 64px;
    }

    .spinner {
      width: 40px;
      height: 40px;
      border: 3px solid var(--glass-border);
      border-top-color: var(--accent, #4f46e5);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `;

    constructor() {
        super();
        this.loading = true;
        this.tiers = [];
        this.editing = null;
        this.showForm = false;
    }

    connectedCallback() {
        super.connectedCallback();
        this._loadTiers();
    }

    async _loadTiers() {
        this.loading = true;
        try {
            const response = await fetch('/api/saas/tiers');
            if (!response.ok) throw new Error('Failed to load tiers');
            this.tiers = await response.json();

            // Default tiers if none exist
            if (this.tiers.length === 0) {
                this.tiers = [
                    {
                        id: '1',
                        name: 'Free',
                        slug: 'free',
                        icon: '🆓',
                        price: 0,
                        popular: false,
                        limits: { api_calls: 1000, memory_ops: 500, embeddings: 100 },
                        features: ['Basic API access', 'Community support', '1 project']
                    },
                    {
                        id: '2',
                        name: 'Starter',
                        slug: 'starter',
                        icon: '🚀',
                        price: 49,
                        popular: false,
                        limits: { api_calls: 10000, memory_ops: 5000, embeddings: 1000 },
                        features: ['10x API calls', 'Email support', '5 projects', 'Basic analytics']
                    },
                    {
                        id: '3',
                        name: 'Pro',
                        slug: 'pro',
                        icon: '⭐',
                        price: 199,
                        popular: true,
                        limits: { api_calls: 100000, memory_ops: 50000, embeddings: 10000 },
                        features: ['100x API calls', 'Priority support', 'Unlimited projects', 'Advanced analytics', 'SSO', 'Custom integrations']
                    },
                    {
                        id: '4',
                        name: 'Enterprise',
                        slug: 'enterprise',
                        icon: '🏢',
                        price: null,
                        popular: false,
                        limits: { api_calls: -1, memory_ops: -1, embeddings: -1 },
                        features: ['Unlimited everything', '24/7 support', 'SLA guarantee', 'Dedicated account manager', 'On-premise option', 'Custom contracts']
                    }
                ];
            }
        } catch (error) {
            console.error('Failed to load tiers:', error);
            this.tiers = [];
        } finally {
            this.loading = false;
        }
    }

    _formatLimit(value) {
        if (value === -1) return '∞';
        if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
        if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
        return value.toLocaleString();
    }

    render() {
        if (this.loading) {
            return html`
        <div class="loading">
          <div class="spinner"></div>
        </div>
      `;
        }

        return html`
      <div class="header">
        <h1>💎 Subscription Tiers</h1>
        <button class="btn-add" @click=${() => this.showForm = true}>
          + Create Tier
        </button>
      </div>

      <div class="tiers-grid">
        ${this.tiers.map(tier => html`
          <div class="tier-card ${tier.popular ? 'popular' : ''}">
            ${tier.popular ? html`<span class="popular-badge">Most Popular</span>` : ''}
            
            <div class="tier-icon ${tier.slug}">${tier.icon}</div>
            <div class="tier-name">${tier.name}</div>
            
            <div class="tier-price">
              ${tier.price === null ? html`
                <span class="price-amount">Custom</span>
              ` : html`
                <span class="price-amount">$${tier.price}</span>
                <span class="price-period">/month</span>
              `}
            </div>

            <div class="limits-grid">
              <div class="limit-item">
                <div class="limit-value">${this._formatLimit(tier.limits?.api_calls)}</div>
                <div class="limit-label">API Calls</div>
              </div>
              <div class="limit-item">
                <div class="limit-value">${this._formatLimit(tier.limits?.memory_ops)}</div>
                <div class="limit-label">Memory Ops</div>
              </div>
            </div>

            <ul class="tier-features">
              ${(tier.features || []).map(feature => html`
                <li>
                  <span class="feature-check">✓</span>
                  <span>${feature}</span>
                </li>
              `)}
            </ul>

            <div class="tier-actions">
              <button class="tier-btn" @click=${() => this._editTier(tier)}>Edit</button>
              <button class="tier-btn" @click=${() => this._duplicateTier(tier)}>Duplicate</button>
            </div>
          </div>
        `)}
      </div>

      ${this.showForm ? this._renderForm() : ''}
    `;
    }

    _renderForm() {
        const tier = this.editing || {
            name: '',
            slug: '',
            icon: '📦',
            price: 0,
            popular: false,
            limits: { api_calls: 1000, memory_ops: 500, embeddings: 100 },
            features: []
        };

        return html`
      <div class="modal-overlay" @click=${this._closeForm}>
        <div class="modal" @click=${e => e.stopPropagation()}>
          <div class="modal-header">
            <h2 class="modal-title">${this.editing ? 'Edit' : 'Create'} Tier</h2>
            <button class="modal-close" @click=${this._closeForm}>×</button>
          </div>
          <div class="modal-body">
            <div class="form-row">
              <div class="form-group">
                <label>Tier Name</label>
                <input type="text" id="tierName" .value=${tier.name} placeholder="e.g., Pro" />
              </div>
              <div class="form-group">
                <label>Slug</label>
                <input type="text" id="tierSlug" .value=${tier.slug} placeholder="e.g., pro" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Price ($/month)</label>
                <input type="number" id="tierPrice" .value=${tier.price || 0} min="0" />
              </div>
              <div class="form-group">
                <label>Icon</label>
                <input type="text" id="tierIcon" .value=${tier.icon} placeholder="⭐" />
              </div>
            </div>

            <h4>Limits</h4>
            <div class="form-row">
              <div class="form-group">
                <label>API Calls/mo</label>
                <input type="number" id="limitApi" .value=${tier.limits?.api_calls || 1000} />
              </div>
              <div class="form-group">
                <label>Memory Ops/mo</label>
                <input type="number" id="limitMemory" .value=${tier.limits?.memory_ops || 500} />
              </div>
            </div>

            <div class="form-group">
              <label>Features</label>
              <div class="features-editor">
                ${(tier.features || []).map((f, i) => html`
                  <div class="feature-row">
                    <input type="text" .value=${f} data-index=${i} />
                    <button @click=${() => this._removeFeature(i)}>×</button>
                  </div>
                `)}
                <button class="add-feature-btn" @click=${this._addFeature}>+ Add Feature</button>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click=${this._closeForm}>Cancel</button>
            <button class="btn-save" @click=${this._saveTier}>Save Tier</button>
          </div>
        </div>
      </div>
    `;
    }

    _closeForm() {
        this.showForm = false;
        this.editing = null;
    }

    _editTier(tier) {
        this.editing = { ...tier };
        this.showForm = true;
    }

    _duplicateTier(tier) {
        this.editing = { ...tier, id: null, name: `${tier.name} (Copy)`, slug: `${tier.slug}-copy` };
        this.showForm = true;
    }

    _addFeature() {
        if (!this.editing) this.editing = { features: [] };
        this.editing.features = [...(this.editing.features || []), ''];
        this.requestUpdate();
    }

    _removeFeature(index) {
        this.editing.features = this.editing.features.filter((_, i) => i !== index);
        this.requestUpdate();
    }

    async _saveTier() {
        const form = {
            name: this.shadowRoot.getElementById('tierName').value,
            slug: this.shadowRoot.getElementById('tierSlug').value,
            price: parseFloat(this.shadowRoot.getElementById('tierPrice').value),
            icon: this.shadowRoot.getElementById('tierIcon').value,
            limits: {
                api_calls: parseInt(this.shadowRoot.getElementById('limitApi').value),
                memory_ops: parseInt(this.shadowRoot.getElementById('limitMemory').value),
            },
            features: this.editing?.features || [],
        };

        try {
            const url = this.editing?.id
                ? `/api/saas/tiers/${this.editing.id}`
                : '/api/saas/tiers';
            const method = this.editing?.id ? 'PATCH' : 'POST';

            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(form),
            });

            if (response.ok) {
                this._closeForm();
                this._loadTiers();
            }
        } catch (error) {
            console.error('Failed to save tier:', error);
        }
    }
}

customElements.define('eog-tier-builder-enhanced', EogTierBuilderEnhanced);
