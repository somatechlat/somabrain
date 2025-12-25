/**
 * Tier Card Component
 * 
 * Displays a subscription tier summary.
 * Used in Subscription list view.
 */

import { LitElement, html, css } from 'lit';

export class EogTierCard extends LitElement {
    static properties = {
        tier: { type: Object },
        stats: { type: Object }, // { tenantCount: 12 }
    };

    static styles = css`
    :host {
      display: block;
    }

    .card {
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      padding: 20px;
      transition: all 0.2s;
      cursor: pointer;
      position: relative;
      overflow: hidden;
    }

    .card:hover {
      border-color: var(--eog-primary, #6366f1);
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }

    .card.active {
      border-color: var(--eog-success, #22c55e);
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }

    .name {
      font-size: 18px;
      font-weight: 600;
      color: var(--eog-text, #e4e4e7);
    }

    .price {
      font-size: 24px;
      font-weight: 700;
      color: var(--eog-text, #e4e4e7);
    }

    .period {
      font-size: 13px;
      color: var(--eog-text-muted, #a1a1aa);
      font-weight: 400;
    }

    .limits {
      margin-bottom: 20px;
    }

    .limit-item {
      display: flex;
      justify-content: space-between;
      font-size: 14px;
      margin-bottom: 8px;
      color: var(--eog-text-secondary, #a1a1aa);
    }

    .limit-val {
      color: var(--eog-text, #e4e4e7);
      font-weight: 500;
    }

    .footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 16px;
      border-top: 1px solid var(--eog-border, #27273a);
    }

    .stat {
      font-size: 13px;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .badge {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 10px;
      background: var(--eog-border, #27273a);
      color: var(--eog-text-muted, #a1a1aa);
    }
  `;

    render() {
        if (!this.tier) return html``;

        return html`
      <div class="card" @click=${this._handleClick}>
        <div class="header">
          <div>
            <div class="name">${this.tier.name}</div>
            <div class="badge">${this.tier.code || 'CUSTOM'}</div>
          </div>
          <div class="price">
            $${this.tier.price} <span class="period">/mo</span>
          </div>
        </div>

        <div class="limits">
          <div class="limit-item">
            <span>Users</span>
            <span class="limit-val">${this.tier.max_users === -1 ? '∞' : this.tier.max_users}</span>
          </div>
          <div class="limit-item">
            <span>Agents</span>
            <span class="limit-val">${this.tier.max_agents === -1 ? '∞' : this.tier.max_agents}</span>
          </div>
          <div class="limit-item">
            <span>Tokens</span>
            <span class="limit-val">${this.tier.features?.find(f => f.code === 'max_tokens')?.value || 'Std'}</span>
          </div>
        </div>

        <div class="footer">
          <span class="stat">🏢 ${this.stats?.tenantCount || 0} Tenants</span>
          <span class="stat">Created ${new Date(this.tier.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    `;
    }

    _handleClick() {
        this.dispatchEvent(new CustomEvent('click', { bubbles: true }));
    }
}

customElements.define('eog-tier-card', EogTierCard);
