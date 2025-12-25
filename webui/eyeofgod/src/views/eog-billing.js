/**
 * Platform Billing Dashboard (Screen 11)
 * Route: /platform/billing
 * 
 * Displays platform-wide revenue metrics and Lago sync status.
 */

import { LitElement, html, css } from 'lit';
import { billingApi, statsApi } from '../services/api.js';

export class EogBilling extends LitElement {
  static properties = {
    revenueStats: { type: Object },
    tierBreakdown: { type: Array },
    lagoStatus: { type: Object },
    isLoading: { type: Boolean },
    error: { type: String },
  };

  static styles = css`
    :host {
      display: block;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 24px;
      margin-bottom: 32px;
    }

    .stat-card {
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      padding: 24px;
    }

    .stat-title {
      color: var(--eog-text-muted, #a1a1aa);
      font-size: 14px;
      margin-bottom: 8px;
    }

    .stat-value {
      font-size: 32px;
      font-weight: 700;
      color: var(--eog-text, #e4e4e7);
    }

    .stat-trend {
      font-size: 13px;
      margin-top: 8px;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .trend-up { color: var(--eog-success, #22c55e); }
    .trend-down { color: var(--eog-error, #ef4444); }

    .section {
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
    }

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    h2 {
      margin: 0;
      font-size: 18px;
      color: var(--eog-text, #e4e4e7);
    }

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      color: var(--eog-text, #e4e4e7);
    }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--eog-text-muted, #a1a1aa);
    }

    .dot.connected { background: var(--eog-success, #22c55e); }
    .dot.error { background: var(--eog-error, #ef4444); }

    .btn {
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      cursor: pointer;
      border: 1px solid var(--eog-border, #27273a);
      background: transparent;
      color: var(--eog-text, #e4e4e7);
    }
    
    .btn:hover {
      background: rgba(255, 255, 255, 0.05);
    }

    /* Tier Revenue Table */
    .tier-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 16px;
    }

    .tier-table th,
    .tier-table td {
      text-align: left;
      padding: 12px;
      border-bottom: 1px solid var(--eog-border, #27273a);
      color: var(--eog-text, #e4e4e7);
    }

    .tier-table th {
      color: var(--eog-text-muted, #a1a1aa);
      font-weight: 500;
      font-size: 13px;
    }

    .tier-table td.money {
      font-family: 'SF Mono', monospace;
      font-weight: 600;
    }

    .error-msg {
      color: var(--eog-error, #ef4444);
      padding: 16px;
      background: rgba(239, 68, 68, 0.1);
      border-radius: 8px;
      margin-bottom: 24px;
    }
  `;

  constructor() {
    super();
    this.revenueStats = {
      mrr: 0,
      arr: 0,
      active_subs: 0,
      mrr_growth: 0
    };
    this.tierBreakdown = [];
    this.lagoStatus = { connected: false, version: 'Unknown' };
    this.isLoading = false;
    this.error = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._loadData();
  }

  async _loadData() {
    this.isLoading = true;
    this.error = null;
    try {
      // Parallel load - NO MOCKS per VIBE rules
      const [rev, lago] = await Promise.all([
        statsApi.revenue(),
        billingApi.getConfig().catch(() => ({ connected: false }))
      ]);

      this.revenueStats = rev;
      this.tierBreakdown = rev.by_tier || [];
      this.lagoStatus = lago;
    } catch (err) {
      console.error('Failed to load revenue data:', err);
      this.error = 'Failed to load revenue data. Is Lago connected?';
    } finally {
      this.isLoading = false;
    }
  }

  render() {
    const growth = this.revenueStats.mrr_growth || 0;
    const trendClass = growth >= 0 ? 'trend-up' : 'trend-down';
    const trendArrow = growth >= 0 ? '↑' : '↓';

    return html`
      <div class="view">
        <h1 style="color:white;margin-bottom:24px;">Billing Overview</h1>

        ${this.error ? html`<div class="error-msg">${this.error}</div>` : ''}

        <div class="grid">
          <div class="stat-card">
            <div class="stat-title">Monthly Recurring Revenue</div>
            <div class="stat-value">$${(this.revenueStats.mrr || 0).toLocaleString()}</div>
            <div class="stat-trend ${trendClass}">
              <span>${trendArrow} ${Math.abs(growth)}%</span> vs last month
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-title">Annual Run Rate</div>
            <div class="stat-value">$${(this.revenueStats.arr || 0).toLocaleString()}</div>
          </div>
          <div class="stat-card">
            <div class="stat-title">Active Subscriptions</div>
            <div class="stat-value">${this.revenueStats.active_subs || 0}</div>
          </div>
        </div>

        <!-- Tier Revenue Breakdown -->
        ${this.tierBreakdown.length > 0 ? html`
        <div class="section">
          <div class="section-header">
            <h2>Revenue by Tier</h2>
          </div>
          <table class="tier-table">
            <thead>
              <tr>
                <th>Tier</th>
                <th>Subscribers</th>
                <th>MRR</th>
                <th>ARR</th>
              </tr>
            </thead>
            <tbody>
              ${this.tierBreakdown.map(tier => html`
                <tr>
                  <td>${tier.tier_name}</td>
                  <td>${tier.subscription_count}</td>
                  <td class="money">$${tier.mrr.toLocaleString()}</td>
                  <td class="money">$${tier.arr.toLocaleString()}</td>
                </tr>
              `)}
            </tbody>
          </table>
        </div>
        ` : ''}

        <div class="section">
          <div class="section-header">
            <h2>Lago Integration Status</h2>
            <div class="status-indicator">
              <div class="dot ${this.lagoStatus.connected ? 'connected' : 'error'}"></div>
              ${this.lagoStatus.connected ? 'Connected' : 'Disconnected'}
            </div>
          </div>
          
          <div style="color:var(--eog-text-secondary);font-size:14px;margin-bottom:16px;">
            Billing engine: <strong>Lago Community Edition</strong><br>
            Version: ${this.lagoStatus.version || 'Detection failed'}
          </div>

          <button class="btn" @click=${this._testConnection}>Test Connection</button>
        </div>
      </div>
    `;
  }

  async _testConnection() {
    try {
      await billingApi.testConnection({});
      this._loadData(); // Refresh
      alert('Connection successful');
    } catch (e) {
      alert('Connection failed');
    }
  }
}

customElements.define('eog-billing', EogBilling);
