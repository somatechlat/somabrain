/**
 * Eye of God - Header Component
 * 
 * Top bar with page title, breadcrumbs, and user menu.
 */

import { LitElement, html, css } from 'lit';

export class EogHeader extends LitElement {
    static properties = {
        pageTitle: { type: String },
        user: { type: Object },
        showUserMenu: { type: Boolean },
    };

    static styles = css`
    :host {
      display: block;
      height: 64px;
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      padding: 0 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    
    .header-left {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    
    .page-title {
      font-size: 20px;
      font-weight: 600;
      color: var(--text-primary, #111);
    }
    
    .header-right {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    
    .search-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: var(--bg-subtle, rgba(0, 0, 0, 0.04));
      border-radius: var(--radius-lg, 12px);
      border: 1px solid transparent;
      transition: all 0.15s ease;
    }
    
    .search-bar:focus-within {
      background: var(--bg-main, #fff);
      border-color: var(--accent, #3b82f6);
    }
    
    .search-bar input {
      border: none;
      background: transparent;
      outline: none;
      font-size: 14px;
      width: 200px;
      color: var(--text-primary, #111);
    }
    
    .search-bar input::placeholder {
      color: var(--text-tertiary, #888);
    }
    
    .icon-btn {
      width: 40px;
      height: 40px;
      border-radius: var(--radius-md, 8px);
      border: none;
      background: transparent;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-secondary, #555);
      transition: all 0.15s ease;
      position: relative;
    }
    
    .icon-btn:hover {
      background: var(--bg-subtle, rgba(0, 0, 0, 0.04));
      color: var(--text-primary, #111);
    }
    
    .notification-badge {
      position: absolute;
      top: 6px;
      right: 6px;
      width: 8px;
      height: 8px;
      background: var(--error, #ef4444);
      border-radius: 50%;
    }
    
    .user-menu {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 8px 4px 4px;
      border-radius: var(--radius-lg, 12px);
      cursor: pointer;
      transition: all 0.15s ease;
    }
    
    .user-menu:hover {
      background: var(--bg-subtle, rgba(0, 0, 0, 0.04));
    }
    
    .user-avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: var(--accent, #3b82f6);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      font-size: 14px;
    }
    
    .user-info {
      display: flex;
      flex-direction: column;
    }
    
    .user-name {
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary, #111);
    }
    
    .user-role {
      font-size: 12px;
      color: var(--text-tertiary, #888);
    }
    
    .dropdown-menu {
      position: absolute;
      top: calc(100% + 8px);
      right: 0;
      background: var(--glass-bg, rgba(255, 255, 255, 0.95));
      backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-lg, 12px);
      box-shadow: var(--glass-shadow-lg, 0 12px 40px -8px rgba(0,0,0,0.12));
      min-width: 180px;
      padding: 8px;
      z-index: 100;
    }
    
    .dropdown-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      border-radius: var(--radius-md, 8px);
      font-size: 14px;
      color: var(--text-secondary, #555);
      cursor: pointer;
      transition: all 0.15s ease;
    }
    
    .dropdown-item:hover {
      background: var(--bg-subtle, rgba(0, 0, 0, 0.04));
      color: var(--text-primary, #111);
    }
    
    .dropdown-item.danger {
      color: var(--error, #ef4444);
    }
    
    .dropdown-divider {
      height: 1px;
      background: var(--glass-border, rgba(0, 0, 0, 0.06));
      margin: 8px 0;
    }
    
    .user-menu-container {
      position: relative;
    }
  `;

    constructor() {
        super();
        this.pageTitle = 'Dashboard';
        this.user = { name: 'Admin', role: 'Platform Admin' };
        this.showUserMenu = false;
    }

    render() {
        return html`
      <div class="header-left">
        <h1 class="page-title">${this.pageTitle}</h1>
      </div>
      
      <div class="header-right">
        <div class="search-bar">
          <span>🔍</span>
          <input type="text" placeholder="Search..." />
        </div>
        
        <button class="icon-btn">
          🔔
          <span class="notification-badge"></span>
        </button>
        
        <div class="user-menu-container">
          <div class="user-menu" @click=${this._toggleUserMenu}>
            <div class="user-avatar">${this._getInitials()}</div>
            <div class="user-info">
              <span class="user-name">${this.user?.name || 'User'}</span>
              <span class="user-role">${this.user?.role || 'Admin'}</span>
            </div>
            <span>▼</span>
          </div>
          
          ${this.showUserMenu ? html`
            <div class="dropdown-menu">
              <div class="dropdown-item">👤 Profile</div>
              <div class="dropdown-item">⚙️ Settings</div>
              <div class="dropdown-divider"></div>
              <div class="dropdown-item danger" @click=${this._logout}>🚪 Logout</div>
            </div>
          ` : ''}
        </div>
      </div>
    `;
    }

    _getInitials() {
        if (!this.user?.name) return '?';
        return this.user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }

    _toggleUserMenu() {
        this.showUserMenu = !this.showUserMenu;
    }

    _logout() {
        // TODO: Implement logout
        console.log('Logout clicked');
    }
}

customElements.define('eog-header', EogHeader);
