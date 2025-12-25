/**
 * Eye of God - Main Application Shell
 * 
 * Contains sidebar navigation, header, and content outlet.
 * Handles routing and authentication state.
 */

import { LitElement, html, css } from 'lit';
import { Router } from '@vaadin/router';
import './eog-sidebar.js';
import './eog-header.js';

// Import view components
import '../views/eog-dashboard.js';
import '../views/eog-tenant-list.js';
import '../views/eog-tenant-create.js';
import '../views/eog-tenant-detail.js';
import '../views/eog-permissions.js';
import '../views/eog-subscriptions.js';
import '../views/eog-tier-builder.js';
import '../views/eog-feature-config.js';
import '../views/eog-billing.js';
import '../views/eog-service-health.js';
import '../views/eog-audit-logs.js';
import '../views/eog-settings.js';
import '../views/eog-users.js';
import '../views/eog-oauth-config.js';
import '../views/eog-memory-overview.js';
import '../views/eog-memory-browse.js';
import '../views/eog-memory-graph.js';

export class EogApp extends LitElement {
  static properties = {
    currentRoute: { type: String },
    user: { type: Object },
  };

  static styles = css`
    :host {
      display: block;
      height: 100vh;
    }
    
    .app-container {
      display: flex;
      height: 100%;
      overflow: hidden;
    }
    
    .main-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      min-width: 0;
    }
    
    .content-area {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      background: var(--bg-void);
    }
  `;

  constructor() {
    super();
    this.currentRoute = '/platform';
    this.user = { name: 'Admin', role: 'Platform Admin' };
  }

  firstUpdated() {
    const outlet = this.shadowRoot.querySelector('#outlet');
    const router = new Router(outlet);

    router.setRoutes([
      { path: '/', redirect: '/platform' },
      { path: '/platform', component: 'eog-dashboard' },
      { path: '/platform/tenants', component: 'eog-tenant-list' },
      { path: '/platform/tenants/new', component: 'eog-tenant-create' },
      { path: '/platform/tenants/:id', component: 'eog-tenant-detail' },
      { path: '/platform/permissions', component: 'eog-permissions' },
      { path: '/platform/subscriptions', component: 'eog-subscriptions' },
      { path: '/platform/subscriptions/new', component: 'eog-tier-builder' },
      { path: '/platform/subscriptions/:id', component: 'eog-tier-builder' },
      { path: '/platform/features', component: 'eog-feature-config' },
      { path: '/platform/billing', component: 'eog-billing' },
      { path: '/platform/services', component: 'eog-service-health' },
      { path: '/platform/audit', component: 'eog-audit-logs' },
      { path: '/platform/settings', component: 'eog-settings' },
      { path: '/platform/users', component: 'eog-users' },
      { path: '/platform/oauth', component: 'eog-oauth-config' },
      { path: '/platform/memory', component: 'eog-memory-overview' },
      { path: '/platform/memory/browse', component: 'eog-memory-browse' },
      { path: '/platform/memory/graph', component: 'eog-memory-graph' },
      { path: '(.*)', redirect: '/platform' },
    ]);

    // Listen for route changes
    window.addEventListener('vaadin-router-location-changed', (e) => {
      this.currentRoute = e.detail.location.pathname;
    });
  }

  render() {
    return html`
      <div class="app-container">
        <eog-sidebar 
          .currentRoute=${this.currentRoute}
          @navigate=${this._handleNavigate}
        ></eog-sidebar>
        
        <div class="main-content">
          <eog-header 
            .user=${this.user}
            .pageTitle=${this._getPageTitle()}
          ></eog-header>
          
          <div class="content-area">
            <div id="outlet"></div>
          </div>
        </div>
      </div>
    `;
  }

  _handleNavigate(e) {
    Router.go(e.detail.path);
  }

  _getPageTitle() {
    const titles = {
      '/platform': 'Dashboard',
      '/platform/tenants': 'Tenants',
      '/platform/tenants/new': 'Create Tenant',
      '/platform/memory': 'Memory Overview',
      '/platform/services': 'Services',
      '/platform/billing': 'Billing',
      '/platform/audit': 'Audit Log',
      '/platform/users': 'Users',
      '/platform/settings': 'Settings',
      '/platform/permissions': 'Permission Browser',
      '/platform/services': 'Service Health',
      '/platform/audit': 'Audit Logs',
    };

    // Handle dynamic routes like /platform/tenants/:id
    if (this.currentRoute.match(/\/platform\/tenants\/[^/]+$/)) {
      return 'Tenant Detail';
    }

    return titles[this.currentRoute] || 'Eye of God';
  }
}

customElements.define('eog-app', EogApp);
