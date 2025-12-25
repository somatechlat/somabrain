/**
 * Service Health Dashboard (System Screen)
 * Route: /platform/services
 * 
 * Real-time visualization of all SomaBrain infrastructure health.
 * Consumes /api/health/full endpoint.
 * 
 * VIBE PERSONAS:
 * - SRE: Complete observability, latency tracking
 * - Architect: Service dependency awareness
 * - UX: Clear status indicators, auto-refresh
 */

import { LitElement, html, css } from 'lit';
import { healthApi } from '../services/api.js';

export class EogServiceHealth extends LitElement {
    static properties = {
        health: { type: Object },
        isLoading: { type: Boolean },
        autoRefresh: { type: Boolean },
        lastUpdated: { type: String },
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

    .title h1 {
      margin: 0;
      font-size: 24px;
      color: var(--eog-text, #e4e4e7);
    }

    .actions {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .btn {
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      cursor: pointer;
      border: 1px solid var(--eog-border, #27273a);
      background: transparent;
      color: var(--eog-text, #e4e4e7);
      transition: all 0.2s;
    }

    .btn:hover {
      background: rgba(255, 255, 255, 0.05);
    }

    .status-badge {
      padding: 6px 12px;
      border-radius: 16px;
      font-size: 13px;
      font-weight: 500;
    }

    .status-healthy { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
    .status-degraded { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
    .status-critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }

    .summary-cards {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin-bottom: 32px;
    }

    .summary-card {
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      padding: 20px;
      text-align: center;
    }

    .summary-value {
      font-size: 36px;
      font-weight: 700;
      color: var(--eog-text, #e4e4e7);
    }

    .summary-label {
      font-size: 14px;
      color: var(--eog-text-muted, #a1a1aa);
      margin-top: 4px;
    }

    .section-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--eog-text-muted, #a1a1aa);
      margin-bottom: 16px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .services-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }

    .service-card {
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      padding: 16px;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .service-icon {
      width: 40px;
      height: 40px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
    }

    .service-icon.healthy { background: rgba(34, 197, 94, 0.2); }
    .service-icon.degraded, .service-icon.unavailable { background: rgba(251, 191, 36, 0.2); }
    .service-icon.unhealthy { background: rgba(239, 68, 68, 0.2); }

    .service-info { flex: 1; }

    .service-name {
      font-weight: 500;
      color: var(--eog-text, #e4e4e7);
    }

    .service-status {
      font-size: 12px;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .service-latency {
      font-size: 12px;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .last-updated {
      font-size: 12px;
      color: var(--eog-text-muted, #a1a1aa);
    }
  `;

    constructor() {
        super();
        this.health = null;
        this.isLoading = false;
        this.autoRefresh = true;
        this.lastUpdated = '';
        this._interval = null;
    }

    connectedCallback() {
        super.connectedCallback();
        this._loadHealth();
        if (this.autoRefresh) {
            this._interval = setInterval(() => this._loadHealth(), 30000);
        }
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        if (this._interval) clearInterval(this._interval);
    }

    async _loadHealth() {
        this.isLoading = true;
        try {
            this.health = await healthApi.services();
            this.lastUpdated = new Date().toLocaleTimeString();
        } catch (err) {
            console.error('Failed to load health:', err);
        } finally {
            this.isLoading = false;
        }
    }

    _toggleAutoRefresh() {
        this.autoRefresh = !this.autoRefresh;
        if (this.autoRefresh) {
            this._interval = setInterval(() => this._loadHealth(), 30000);
        } else {
            if (this._interval) clearInterval(this._interval);
        }
    }

    _getStatusIcon(status) {
        const icons = {
            healthy: '✓',
            degraded: '⚠',
            unavailable: '○',
            unhealthy: '✗',
            not_configured: '○'
        };
        return icons[status] || '?';
    }

    _getServiceEmoji(name) {
        const emojis = {
            postgresql: '🐘',
            redis: '🔴',
            kafka: '📨',
            milvus: '🧠',
            opa: '🔐',
            minio: '📦',
            keycloak: '🔑',
            lago: '💳',
            schema_registry: '📋',
            soma_fractal_memory: '💎',
            cognitive: '🧩',
            embedder: '🔢'
        };
        return emojis[name.toLowerCase().replace(' ', '_')] || '⚙️';
    }

    render() {
        const overall = this.health?.status || 'unknown';

        return html`
      <div class="view">
        <div class="header">
          <div class="title">
            <h1>Service Health</h1>
          </div>
          <div class="actions">
            <span class="last-updated">Last: ${this.lastUpdated || '-'}</span>
            <button class="btn" @click=${this._toggleAutoRefresh}>
              ${this.autoRefresh ? '⏸️ Pause' : '▶️ Resume'}
            </button>
            <button class="btn" @click=${() => this._loadHealth()}>🔄 Refresh</button>
            <span class="status-badge status-${overall}">${overall.toUpperCase()}</span>
          </div>
        </div>

        <div class="summary-cards">
          <div class="summary-card">
            <div class="summary-value" style="color:#22c55e">${this.health?.healthy_count || 0}</div>
            <div class="summary-label">Healthy</div>
          </div>
          <div class="summary-card">
            <div class="summary-value" style="color:#fbbf24">${this.health?.degraded_count || 0}</div>
            <div class="summary-label">Degraded</div>
          </div>
          <div class="summary-card">
            <div class="summary-value" style="color:#ef4444">${this.health?.unhealthy_count || 0}</div>
            <div class="summary-label">Unhealthy</div>
          </div>
        </div>

        <div class="section-title">Infrastructure</div>
        <div class="services-grid">
          ${this._renderServiceCards(this.health?.infrastructure || {})}
        </div>

        <div class="section-title">Internal Services</div>
        <div class="services-grid">
          ${this._renderServiceCards(this.health?.internal_services || {})}
        </div>
      </div>
    `;
    }

    _renderServiceCards(services) {
        return Object.entries(services).map(([key, svc]) => html`
      <div class="service-card">
        <div class="service-icon ${svc.status}">${this._getServiceEmoji(key)}</div>
        <div class="service-info">
          <div class="service-name">${svc.name || key}</div>
          <div class="service-status">${svc.status} ${svc.error ? `- ${svc.error.slice(0, 50)}` : ''}</div>
        </div>
        <div class="service-latency">${svc.response_time_ms || '-'}ms</div>
      </div>
    `);
    }
}

customElements.define('eog-service-health', EogServiceHealth);
