/**
 * Eye of God - Dashboard View
 * 
 * Main admin dashboard with KPI cards, service status, and activity feed.
 */

import { LitElement, html, css } from 'lit';

export class EogDashboard extends LitElement {
  static properties = {
    stats: { type: Object },
    services: { type: Array },
    activity: { type: Array },
    loading: { type: Boolean },
  };

  static styles = css`
    :host {
      display: block;
    }
    
    .dashboard-grid {
      display: grid;
      gap: 24px;
    }
    
    /* KPI Cards Row */
    .kpi-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }
    
    .kpi-card {
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-xl, 16px);
      padding: 20px;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    
    .kpi-card:hover {
      transform: translateY(-2px);
      box-shadow: var(--glass-shadow-lg, 0 12px 40px -8px rgba(0,0,0,0.12));
    }
    
    .kpi-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }
    
    .kpi-icon {
      width: 40px;
      height: 40px;
      border-radius: var(--radius-md, 8px);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
    }
    
    .kpi-icon.blue { background: rgba(59, 130, 246, 0.1); }
    .kpi-icon.green { background: rgba(34, 197, 94, 0.1); }
    .kpi-icon.purple { background: rgba(168, 85, 247, 0.1); }
    .kpi-icon.orange { background: rgba(249, 115, 22, 0.1); }
    
    .kpi-change {
      font-size: 12px;
      font-weight: 500;
      padding: 4px 8px;
      border-radius: 20px;
    }
    
    .kpi-change.positive {
      background: rgba(34, 197, 94, 0.1);
      color: #16a34a;
    }
    
    .kpi-change.negative {
      background: rgba(239, 68, 68, 0.1);
      color: #dc2626;
    }
    
    .kpi-value {
      font-size: 28px;
      font-weight: 700;
      color: var(--text-primary, #111);
      margin-bottom: 4px;
    }
    
    .kpi-label {
      font-size: 14px;
      color: var(--text-tertiary, #888);
    }
    
    /* Service Status Card */
    .section-card {
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-xl, 16px);
      padding: 24px;
    }
    
    .section-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary, #111);
      margin-bottom: 16px;
    }
    
    .services-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 12px;
    }
    
    .service-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      border-radius: var(--radius-md, 8px);
      background: var(--bg-subtle, rgba(0, 0, 0, 0.02));
    }
    
    .service-status {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
    
    .service-status.up { background: #22c55e; }
    .service-status.down { background: #ef4444; }
    .service-status.degraded { background: #f59e0b; }
    
    .service-info {
      flex: 1;
    }
    
    .service-name {
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary, #111);
    }
    
    .service-port {
      font-size: 12px;
      color: var(--text-tertiary, #888);
    }
    
    /* Activity Feed */
    .activity-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    
    .activity-item {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 12px;
      border-radius: var(--radius-md, 8px);
      background: var(--bg-subtle, rgba(0, 0, 0, 0.02));
    }
    
    .activity-time {
      font-size: 12px;
      color: var(--text-tertiary, #888);
      white-space: nowrap;
    }
    
    .activity-text {
      font-size: 14px;
      color: var(--text-secondary, #555);
    }
    
    /* Quick Actions */
    .quick-actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    
    .action-btn {
      padding: 12px 20px;
      border: none;
      border-radius: var(--radius-lg, 12px);
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    
    .action-btn.primary {
      background: var(--accent, #3b82f6);
      color: white;
    }
    
    .action-btn.primary:hover {
      background: var(--accent-hover, #2563eb);
    }
    
    .action-btn.secondary {
      background: var(--bg-subtle, rgba(0, 0, 0, 0.04));
      color: var(--text-primary, #111);
    }
    
    .action-btn.secondary:hover {
      background: rgba(0, 0, 0, 0.08);
    }
    
    .two-col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    
    @media (max-width: 900px) {
      .two-col {
        grid-template-columns: 1fr;
      }
    }
  `;

  constructor() {
    super();
    this.loading = false;
    this.stats = {};
    this.services = [];
    this.activity = [];
    this.error = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._loadDashboard();
  }

  async _loadDashboard() {
    this.loading = true;
    try {
      // Load from real APIs
      const [statsResult, healthResult, activityResult] = await Promise.allSettled([
        import('../services/api.js').then(m => m.statsApi.dashboard()),
        import('../services/api.js').then(m => m.healthApi.full()),
        import('../services/api.js').then(m => m.auditApi.list({ limit: 5 }))
      ]);

      if (statsResult.status === 'fulfilled') {
        this.stats = statsResult.value || {};
      }
      if (healthResult.status === 'fulfilled') {
        const health = healthResult.value;
        this.services = (health.services || []).map(s => ({
          name: s.name,
          port: s.port || '',
          status: s.status === 'healthy' ? 'up' : s.status === 'degraded' ? 'degraded' : 'down'
        }));
      }
      if (activityResult.status === 'fulfilled') {
        const logs = activityResult.value?.logs || activityResult.value || [];
        this.activity = logs.slice(0, 5).map(log => ({
          time: new Date(log.timestamp || log.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
          text: log.action || log.message || 'Activity'
        }));
      }
    } catch (err) {
      console.error('Failed to load dashboard:', err);
      this.error = err.message;
    } finally {
      this.loading = false;
    }
  }

  render() {
    return html`
      <div class="dashboard-grid">
        <!-- KPI Cards -->
        <div class="kpi-row">
          <div class="kpi-card">
            <div class="kpi-header">
              <div class="kpi-icon blue">💳</div>
              <span class="kpi-change positive">${this.stats.mrrChange} ↑</span>
            </div>
            <div class="kpi-value">${this.stats.mrr}</div>
            <div class="kpi-label">Monthly Recurring Revenue</div>
          </div>
          
          <div class="kpi-card">
            <div class="kpi-header">
              <div class="kpi-icon green">🏢</div>
              <span class="kpi-change positive">${this.stats.tenantsChange} this week</span>
            </div>
            <div class="kpi-value">${this.stats.tenants}</div>
            <div class="kpi-label">Active Tenants</div>
          </div>
          
          <div class="kpi-card">
            <div class="kpi-header">
              <div class="kpi-icon purple">👥</div>
            </div>
            <div class="kpi-value">${this.stats.users}</div>
            <div class="kpi-label">Active Users</div>
          </div>
          
          <div class="kpi-card">
            <div class="kpi-header">
              <div class="kpi-icon orange">📊</div>
            </div>
            <div class="kpi-value">${this.stats.apiCalls}</div>
            <div class="kpi-label">API Calls Today</div>
          </div>
        </div>
        
        <!-- Two Column Section -->
        <div class="two-col">
          <!-- Service Status -->
          <div class="section-card">
            <div class="section-title">🔧 Service Status</div>
            <div class="services-grid">
              ${this.services.map(s => html`
                <div class="service-item">
                  <div class="service-status ${s.status}"></div>
                  <div class="service-info">
                    <div class="service-name">${s.name}</div>
                    <div class="service-port">${s.port}</div>
                  </div>
                </div>
              `)}
            </div>
          </div>
          
          <!-- Recent Activity -->
          <div class="section-card">
            <div class="section-title">📋 Recent Activity</div>
            <div class="activity-list">
              ${this.activity.map(a => html`
                <div class="activity-item">
                  <span class="activity-time">${a.time}</span>
                  <span class="activity-text">${a.text}</span>
                </div>
              `)}
            </div>
          </div>
        </div>
        
        <!-- Quick Actions -->
        <div class="section-card">
          <div class="section-title">⚡ Quick Actions</div>
          <div class="quick-actions">
            <button class="action-btn primary" @click=${this._createTenant}>+ Create Tenant</button>
            <button class="action-btn secondary">View All Tenants</button>
            <button class="action-btn secondary">System Settings</button>
          </div>
        </div>
      </div>
    `;
  }

  _createTenant() {
    window.history.pushState({}, '', '/platform/tenants/new');
    window.dispatchEvent(new PopStateEvent('popstate'));
  }
}

customElements.define('eog-dashboard', EogDashboard);
