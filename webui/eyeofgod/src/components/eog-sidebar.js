/**
 * Eye of God - Sidebar Navigation
 * 
 * Left navigation panel with sections for all admin areas.
 * Uses glassmorphism styling from somastack-ui.css design system.
 */

import { LitElement, html, css } from 'lit';

export class EogSidebar extends LitElement {
    static properties = {
        currentRoute: { type: String },
        collapsed: { type: Boolean },
    };

    static styles = css`
    :host {
      display: block;
      width: 260px;
      height: 100%;
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-right: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      display: flex;
      flex-direction: column;
    }
    
    :host([collapsed]) {
      width: 64px;
    }
    
    .sidebar-header {
      padding: 20px;
      border-bottom: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
    }
    
    .logo {
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 700;
      font-size: 18px;
      color: var(--text-primary, #111);
    }
    
    .logo-icon {
      width: 32px;
      height: 32px;
      background: var(--accent, #3b82f6);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 18px;
    }
    
    .nav-section {
      padding: 16px 12px;
    }
    
    .nav-section-title {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-tertiary, #888);
      padding: 0 8px;
      margin-bottom: 8px;
    }
    
    .nav-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      border-radius: var(--radius-md, 8px);
      color: var(--text-secondary, #555);
      cursor: pointer;
      transition: all 0.15s ease;
      text-decoration: none;
      font-size: 14px;
    }
    
    .nav-item:hover {
      background: var(--bg-subtle, rgba(0, 0, 0, 0.04));
      color: var(--text-primary, #111);
    }
    
    .nav-item.active {
      background: var(--accent-subtle, rgba(59, 130, 246, 0.1));
      color: var(--accent, #3b82f6);
      font-weight: 500;
    }
    
    .nav-icon {
      width: 20px;
      height: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .sidebar-footer {
      margin-top: auto;
      padding: 16px;
      border-top: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
    }
    
    .collapse-btn {
      width: 100%;
      padding: 8px;
      border: none;
      background: transparent;
      color: var(--text-tertiary, #888);
      cursor: pointer;
      border-radius: var(--radius-md, 8px);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .collapse-btn:hover {
      background: var(--bg-subtle, rgba(0, 0, 0, 0.04));
    }
  `;

    constructor() {
        super();
        this.currentRoute = '/platform';
        this.collapsed = false;
    }

    render() {
        return html`
      <div class="sidebar-header">
        <div class="logo">
          <div class="logo-icon">🔱</div>
          ${!this.collapsed ? html`<span>Eye of God</span>` : ''}
        </div>
      </div>
      
      <div class="nav-section">
        <div class="nav-item ${this._isActive('/platform') ? 'active' : ''}"
             @click=${() => this._navigate('/platform')}>
          <span class="nav-icon">📊</span>
          ${!this.collapsed ? html`<span>Dashboard</span>` : ''}
        </div>
      </div>
      
      <div class="nav-section">
        <div class="nav-section-title">${!this.collapsed ? 'Tenant Management' : ''}</div>
        <div class="nav-item ${this._isActive('/platform/tenants') ? 'active' : ''}"
             @click=${() => this._navigate('/platform/tenants')}>
          <span class="nav-icon">🏢</span>
          ${!this.collapsed ? html`<span>Tenants</span>` : ''}
        </div>
        <div class="nav-item ${this._isActive('/platform/tenants/new') ? 'active' : ''}"
             @click=${() => this._navigate('/platform/tenants/new')}>
          <span class="nav-icon">➕</span>
          ${!this.collapsed ? html`<span>Create Tenant</span>` : ''}
        </div>
      </div>
      
      <div class="nav-section">
        <div class="nav-section-title">${!this.collapsed ? 'Memory' : ''}</div>
        <div class="nav-item ${this._isActive('/platform/memory') ? 'active' : ''}"
             @click=${() => this._navigate('/platform/memory')}>
          <span class="nav-icon">🧠</span>
          ${!this.collapsed ? html`<span>Memory Overview</span>` : ''}
        </div>
        <div class="nav-item" @click=${() => this._navigate('/platform/memory/browse')}>
          <span class="nav-icon">📂</span>
          ${!this.collapsed ? html`<span>Browse</span>` : ''}
        </div>
        <div class="nav-item" @click=${() => this._navigate('/platform/memory/graph')}>
          <span class="nav-icon">🔗</span>
          ${!this.collapsed ? html`<span>Graph Explorer</span>` : ''}
        </div>
      </div>
      
      <div class="nav-section">
        <div class="nav-section-title">${!this.collapsed ? 'Billing' : ''}</div>
        <div class="nav-item ${this._isActive('/platform/billing') ? 'active' : ''}"
             @click=${() => this._navigate('/platform/billing')}>
          <span class="nav-icon">💳</span>
          ${!this.collapsed ? html`<span>Revenue</span>` : ''}
        </div>
        <div class="nav-item ${this._isActive('/platform/billing/plans') ? 'active' : ''}"
             @click=${() => this._navigate('/platform/billing/plans')}>
          <span class="nav-icon">📋</span>
          ${!this.collapsed ? html`<span>Plans</span>` : ''}
        </div>
        <div class="nav-item ${this._isActive('/platform/billing/invoices') ? 'active' : ''}"
             @click=${() => this._navigate('/platform/billing/invoices')}>
          <span class="nav-icon">📄</span>
          ${!this.collapsed ? html`<span>Invoices</span>` : ''}
        </div>
      </div>
      
      <div class="nav-section">
        <div class="nav-section-title">${!this.collapsed ? 'System' : ''}</div>
        <div class="nav-item ${this._isActive('/platform/services') ? 'active' : ''}"
             @click=${() => this._navigate('/platform/services')}>
          <span class="nav-icon">🔧</span>
          ${!this.collapsed ? html`<span>Services</span>` : ''}
        </div>
        <div class="nav-item ${this._isActive('/platform/audit') ? 'active' : ''}"
             @click=${() => this._navigate('/platform/audit')}>
          <span class="nav-icon">📜</span>
          ${!this.collapsed ? html`<span>Audit Log</span>` : ''}
        </div>
        <div class="nav-item ${this._isActive('/platform/users') ? 'active' : ''}"
             @click=${() => this._navigate('/platform/users')}>
          <span class="nav-icon">👥</span>
          ${!this.collapsed ? html`<span>Users</span>` : ''}
        </div>
        <div class="nav-item ${this._isActive('/platform/settings') ? 'active' : ''}"
             @click=${() => this._navigate('/platform/settings')}>
          <span class="nav-icon">⚙️</span>
          ${!this.collapsed ? html`<span>Settings</span>` : ''}
        </div>
      </div>
      
      <div class="sidebar-footer">
        <button class="collapse-btn" @click=${this._toggleCollapse}>
          ${this.collapsed ? '→' : '←'}
        </button>
      </div>
    `;
    }

    _isActive(path) {
        if (path === '/platform' && this.currentRoute === '/platform') {
            return true;
        }
        if (path !== '/platform' && this.currentRoute.startsWith(path)) {
            return true;
        }
        return false;
    }

    _navigate(path) {
        this.dispatchEvent(new CustomEvent('navigate', {
            detail: { path },
            bubbles: true,
            composed: true
        }));
    }

    _toggleCollapse() {
        this.collapsed = !this.collapsed;
    }
}

customElements.define('eog-sidebar', EogSidebar);
