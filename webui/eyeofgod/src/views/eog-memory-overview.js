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
import { memoryApi, statsApi } from '../services/api.js';

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
    this.stats = {
      totalNodes: 0,
      totalEdges: 0,
      totalTenants: 0,
      avgQueryTime: 0,
      topTenants: [],
      storage: { milvus: 0, postgres: 0, redis: 0 }
    };
    this.isLoading = false;
    this.error = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._loadStats();
  }

  async _loadStats() {
    this.isLoading = true;
    try {
      const result = await memoryApi.stats();
      this.stats = {
        totalNodes: result.total_nodes || result.totalNodes || 0,
        totalEdges: result.total_edges || result.totalEdges || 0,
        totalTenants: result.total_tenants || result.totalTenants || 0,
        avgQueryTime: result.avg_query_time_ms || result.avgQueryTime || 0,
        topTenants: result.top_tenants || result.topTenants || [],
        storage: result.storage || { milvus: 0, postgres: 0, redis: 0 }
      };
    } catch (err) {
      console.error('Failed to load memory stats:', err);
      this.error = err.message;
    } finally {
      this.isLoading = false;
    }
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
