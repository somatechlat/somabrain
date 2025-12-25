/**
 * Eye of God - Tenant List View
 * 
 * Catalog of all tenants as cards with search/filter.
 * Click card → opens tenant detail modal.
 */

import { LitElement, html, css } from 'lit';

export class EogTenantList extends LitElement {
    static properties = {
        tenants: { type: Array },
        loading: { type: Boolean },
        searchQuery: { type: String },
        statusFilter: { type: String },
        tierFilter: { type: String },
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
    
    .header-left {
      display: flex;
      gap: 12px;
    }
    
    .search-box {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 16px;
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-lg, 12px);
      width: 280px;
    }
    
    .search-box input {
      border: none;
      background: transparent;
      outline: none;
      flex: 1;
      font-size: 14px;
    }
    
    .filter-select {
      padding: 10px 16px;
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-lg, 12px);
      font-size: 14px;
      cursor: pointer;
    }
    
    .btn-primary {
      padding: 10px 20px;
      background: var(--accent, #3b82f6);
      color: white;
      border: none;
      border-radius: var(--radius-lg, 12px);
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.15s ease;
    }
    
    .btn-primary:hover {
      background: var(--accent-hover, #2563eb);
    }
    
    /* Card Catalog */
    .tenant-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
    }
    
    .tenant-card {
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-xl, 16px);
      padding: 24px;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    
    .tenant-card:hover {
      transform: translateY(-4px);
      box-shadow: var(--glass-shadow-lg, 0 12px 40px -8px rgba(0,0,0,0.12));
    }
    
    .tenant-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }
    
    .tenant-name {
      font-size: 18px;
      font-weight: 600;
      color: var(--text-primary, #111);
    }
    
    .tenant-id {
      font-size: 12px;
      color: var(--text-tertiary, #888);
      margin-top: 4px;
    }
    
    .status-badge {
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 500;
    }
    
    .status-badge.active {
      background: rgba(34, 197, 94, 0.1);
      color: #16a34a;
    }
    
    .status-badge.trial {
      background: rgba(249, 115, 22, 0.1);
      color: #ea580c;
    }
    
    .status-badge.suspended {
      background: rgba(239, 68, 68, 0.1);
      color: #dc2626;
    }
    
    .tenant-meta {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 16px;
    }
    
    .meta-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    
    .meta-label {
      font-size: 12px;
      color: var(--text-tertiary, #888);
    }
    
    .meta-value {
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary, #111);
    }
    
    .tier-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
    }
    
    .tier-badge.free { background: #f3f4f6; color: #6b7280; }
    .tier-badge.starter { background: #dbeafe; color: #2563eb; }
    .tier-badge.pro { background: #fef3c7; color: #d97706; }
    .tier-badge.enterprise { background: #ede9fe; color: #7c3aed; }
    
    .tenant-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 16px;
      border-top: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
    }
    
    .tenant-created {
      font-size: 12px;
      color: var(--text-tertiary, #888);
    }
    
    .tenant-actions {
      display: flex;
      gap: 8px;
    }
    
    .action-btn {
      width: 32px;
      height: 32px;
      border: none;
      background: var(--bg-subtle, rgba(0, 0, 0, 0.04));
      border-radius: var(--radius-md, 8px);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .action-btn:hover {
      background: rgba(0, 0, 0, 0.08);
    }
    
    /* Summary bar */
    .summary-bar {
      margin-top: 24px;
      padding: 16px 24px;
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-lg, 12px);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .summary-stats {
      display: flex;
      gap: 24px;
    }
    
    .summary-item {
      font-size: 14px;
    }
    
    .summary-label {
      color: var(--text-tertiary, #888);
    }
    
    .summary-value {
      font-weight: 600;
      color: var(--text-primary, #111);
    }
  `;

    constructor() {
        super();
        this.loading = false;
        this.searchQuery = '';
        this.statusFilter = 'all';
        this.tierFilter = 'all';
        this.tenants = [
            { id: 'acme-corp', name: 'Acme Corp', tier: 'pro', status: 'active', users: 12, created: 'Jan 15, 2024' },
            { id: 'beta-inc', name: 'Beta Inc', tier: 'starter', status: 'active', users: 5, created: 'Feb 20, 2024' },
            { id: 'gamma-llc', name: 'Gamma LLC', tier: 'free', status: 'trial', users: 2, created: 'Dec 20, 2024' },
            { id: 'delta-co', name: 'Delta Co', tier: 'pro', status: 'suspended', users: 8, created: 'Mar 10, 2024' },
            { id: 'epsilon-ai', name: 'Epsilon AI', tier: 'enterprise', status: 'active', users: 45, created: 'Nov 05, 2024' },
            { id: 'zeta-tech', name: 'Zeta Tech', tier: 'starter', status: 'active', users: 7, created: 'Dec 01, 2024' },
        ];
    }

    render() {
        const filtered = this._filterTenants();

        return html`
      <div class="header">
        <div class="header-left">
          <div class="search-box">
            <span>🔍</span>
            <input 
              type="text" 
              placeholder="Search tenants..." 
              .value=${this.searchQuery}
              @input=${e => this.searchQuery = e.target.value}
            />
          </div>
          <select class="filter-select" @change=${e => this.statusFilter = e.target.value}>
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="trial">Trial</option>
            <option value="suspended">Suspended</option>
          </select>
          <select class="filter-select" @change=${e => this.tierFilter = e.target.value}>
            <option value="all">All Tiers</option>
            <option value="free">Free</option>
            <option value="starter">Starter</option>
            <option value="pro">Pro</option>
            <option value="enterprise">Enterprise</option>
          </select>
        </div>
        <button class="btn-primary" @click=${this._createTenant}>
          <span>+</span> Create Tenant
        </button>
      </div>
      
      <div class="tenant-grid">
        ${filtered.map(t => html`
          <div class="tenant-card" @click=${() => this._viewTenant(t.id)}>
            <div class="tenant-header">
              <div>
                <div class="tenant-name">${t.name}</div>
                <div class="tenant-id">${t.id}</div>
              </div>
              <span class="status-badge ${t.status}">${t.status}</span>
            </div>
            
            <div class="tenant-meta">
              <div class="meta-item">
                <span class="meta-label">Tier</span>
                <span class="tier-badge ${t.tier}">${this._getTierIcon(t.tier)} ${t.tier}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Users</span>
                <span class="meta-value">${t.users}</span>
              </div>
            </div>
            
            <div class="tenant-footer">
              <span class="tenant-created">Created ${t.created}</span>
              <div class="tenant-actions">
                <button class="action-btn" @click=${e => { e.stopPropagation(); this._viewTenant(t.id); }}>⚙️</button>
                <button class="action-btn" @click=${e => { e.stopPropagation(); this._viewUsers(t.id); }}>👤</button>
              </div>
            </div>
          </div>
        `)}
      </div>
      
      <div class="summary-bar">
        <div class="summary-stats">
          <div class="summary-item">
            <span class="summary-label">Active:</span>
            <span class="summary-value">${this.tenants.filter(t => t.status === 'active').length}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Trial:</span>
            <span class="summary-value">${this.tenants.filter(t => t.status === 'trial').length}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Suspended:</span>
            <span class="summary-value">${this.tenants.filter(t => t.status === 'suspended').length}</span>
          </div>
        </div>
        <span>Showing ${filtered.length} of ${this.tenants.length} tenants</span>
      </div>
    `;
    }

    _filterTenants() {
        return this.tenants.filter(t => {
            const matchesSearch = t.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                t.id.toLowerCase().includes(this.searchQuery.toLowerCase());
            const matchesStatus = this.statusFilter === 'all' || t.status === this.statusFilter;
            const matchesTier = this.tierFilter === 'all' || t.tier === this.tierFilter;
            return matchesSearch && matchesStatus && matchesTier;
        });
    }

    _getTierIcon(tier) {
        const icons = { free: '🆓', starter: '🚀', pro: '⭐', enterprise: '🏢' };
        return icons[tier] || '';
    }

    _createTenant() {
        window.history.pushState({}, '', '/platform/tenants/new');
        window.dispatchEvent(new PopStateEvent('popstate'));
    }

    _viewTenant(id) {
        window.history.pushState({}, '', `/platform/tenants/${id}`);
        window.dispatchEvent(new PopStateEvent('popstate'));
    }

    _viewUsers(id) {
        console.log('View users for:', id);
    }
}

customElements.define('eog-tenant-list', EogTenantList);
