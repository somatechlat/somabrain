/**
 * Memory Overview View
 * Route: /platform/memory
 * 
 * Platform-wide memory metrics and health.
 * 
 * VIBE PERSONAS:
 * - SRE: Memory system health monitoring
 * - Architect: Multi-tenant memory isolation overview
 * - DBA: Vector storage metrics
 * - UX: Clear visualizations
 */

import { LitElement, html, css } from 'lit';

export class EogMemoryOverview extends LitElement {
    static properties = {
        stats: { type: Object },
        isLoading: { type: Boolean },
    };

    static styles = css`
    :host {
      display: block;
    }

    h1 {
      margin: 0 0 24px 0;
      font-size: 24px;
      color: var(--eog-text, #e4e4e7);
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 20px;
      margin-bottom: 32px;
    }

    .stat-card {
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      padding: 20px;
    }

    .stat-value {
      font-size: 32px;
      font-weight: 700;
      color: var(--eog-text, #e4e4e7);
    }

    .stat-label {
      font-size: 14px;
      color: var(--eog-text-muted, #a1a1aa);
      margin-top: 4px;
    }

    .stat-trend {
      font-size: 12px;
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

    .section-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--eog-text, #e4e4e7);
      margin-bottom: 16px;
    }

    .tenant-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid var(--eog-border, #27273a);
    }

    .tenant-row:last-child {
      border-bottom: none;
    }

    .tenant-name {
      font-weight: 500;
      color: var(--eog-text, #e4e4e7);
    }

    .tenant-stats {
      display: flex;
      gap: 24px;
      font-size: 13px;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .bar {
      height: 8px;
      background: var(--eog-border, #27273a);
      border-radius: 4px;
      overflow: hidden;
      width: 120px;
    }

    .bar-fill {
      height: 100%;
      background: var(--eog-primary, #6366f1);
      border-radius: 4px;
    }
  `;

    constructor() {
        super();
        // Mock data
        this.stats = {
            totalNodes: 145230,
            totalEdges: 892140,
            totalTenants: 24,
            avgQueryTime: 42,
            topTenants: [
                { name: 'Acme Corp', slug: 'acme', nodes: 45000, usage: 0.75 },
                { name: 'TechStart', slug: 'techstart', nodes: 32000, usage: 0.52 },
                { name: 'DataFlow', slug: 'dataflow', nodes: 28000, usage: 0.45 },
                { name: 'AI Labs', slug: 'ailabs', nodes: 21000, usage: 0.34 },
            ]
        };
        this.isLoading = false;
    }

    render() {
        return html`
      <h1>Memory Overview</h1>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">${(this.stats.totalNodes / 1000).toFixed(1)}K</div>
          <div class="stat-label">Total Nodes</div>
          <div class="stat-trend trend-up">↑ 12% this week</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${(this.stats.totalEdges / 1000).toFixed(1)}K</div>
          <div class="stat-label">Total Edges</div>
          <div class="stat-trend trend-up">↑ 8% this week</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${this.stats.totalTenants}</div>
          <div class="stat-label">Active Tenants</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${this.stats.avgQueryTime}ms</div>
          <div class="stat-label">Avg Query Time</div>
          <div class="stat-trend trend-down">↓ 5ms from last week</div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">Top Tenants by Memory Usage</div>
        ${this.stats.topTenants.map(tenant => html`
          <div class="tenant-row">
            <div class="tenant-name">${tenant.name}</div>
            <div class="tenant-stats">
              <span>${(tenant.nodes / 1000).toFixed(1)}K nodes</span>
              <div class="bar">
                <div class="bar-fill" style="width:${tenant.usage * 100}%"></div>
              </div>
              <span>${(tenant.usage * 100).toFixed(0)}%</span>
            </div>
          </div>
        `)}
      </div>

      <div class="section">
        <div class="section-title">Storage Distribution</div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;">
          <div>
            <div style="font-size:24px;font-weight:600;color:var(--eog-text);">2.4 GB</div>
            <div style="font-size:13px;color:var(--eog-text-muted);">Milvus Vectors</div>
          </div>
          <div>
            <div style="font-size:24px;font-weight:600;color:var(--eog-text);">1.2 GB</div>
            <div style="font-size:13px;color:var(--eog-text-muted);">PostgreSQL Metadata</div>
          </div>
          <div>
            <div style="font-size:24px;font-weight:600;color:var(--eog-text);">890 MB</div>
            <div style="font-size:13px;color:var(--eog-text-muted);">Redis Cache</div>
          </div>
        </div>
      </div>
    `;
    }
}

customElements.define('eog-memory-overview', EogMemoryOverview);
