/**
 * Subscriptions View (Screen 8)
 * Route: /platform/subscriptions
 * 
 * Displays list of all subscription tiers.
 * Actions: Create Tier, Edit Tier, View Stats.
 */

import { LitElement, html, css } from 'lit';
import { tiersApi } from '../services/api.js';
import '../components/billing/eog-tier-card.js';

export class EogSubscriptions extends LitElement {
    static properties = {
        tiers: { type: Array },
        isLoading: { type: Boolean },
    };

    static styles = css`
    :host {
      display: block;
      padding-bottom: 40px;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }

    .title h1 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
      color: var(--eog-text, #e4e4e7);
    }

    .title p {
      margin: 4px 0 0 0;
      color: var(--eog-text-muted, #a1a1aa);
      font-size: 14px;
    }

    .btn-create {
      background: var(--eog-primary, #6366f1);
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 8px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }

    .btn-create:hover {
      background: var(--eog-primary-hover, #4f46e5);
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 24px;
    }

    .empty-state {
      text-align: center;
      padding: 60px;
      background: var(--eog-surface, #1a1a2e);
      border-radius: 12px;
      border: 1px dashed var(--eog-border, #27273a);
      color: var(--eog-text-muted, #a1a1aa);
    }
  `;

    constructor() {
        super();
        this.tiers = [];
        this.isLoading = false;
    }

    connectedCallback() {
        super.connectedCallback();
        this._loadTiers();
    }

    async _loadTiers() {
        this.isLoading = true;
        try {
            this.tiers = await tiersApi.list();
        } catch (err) {
            console.error('Failed to load tiers:', err);
        } finally {
            this.isLoading = false;
        }
    }

    _handleCreate() {
        this.dispatchEvent(new CustomEvent('navigate', {
            detail: { path: '/platform/subscriptions/new' },
            bubbles: true,
            composed: true
        }));
    }

    _handleEdit(tier) {
        this.dispatchEvent(new CustomEvent('navigate', {
            detail: { path: `/platform/subscriptions/${tier.id}` },
            bubbles: true,
            composed: true
        }));
    }

    render() {
        return html`
      <div class="view">
        <div class="header">
          <div class="title">
            <h1>Subscription Tiers</h1>
            <p>Manage pricing plans and feature sets</p>
          </div>
          <button class="btn-create" @click=${this._handleCreate}>
            <span>+</span> Create Tier
          </button>
        </div>

        ${this.isLoading ? html`<div>Loading...</div>` : ''}

        ${!this.isLoading && this.tiers.length === 0 ? html`
          <div class="empty-state">
            <h3>No tiers defined</h3>
            <p>Create your first subscription tier to get started.</p>
          </div>
        ` : ''}

        <div class="grid">
          ${this.tiers.map(tier => html`
            <eog-tier-card 
              .tier=${tier}
              .stats=${{ tenantCount: 0 }} 
              @click=${() => this._handleEdit(tier)}
            ></eog-tier-card>
          `)}
        </div>
      </div>
    `;
    }
}

customElements.define('eog-subscriptions', EogSubscriptions);
