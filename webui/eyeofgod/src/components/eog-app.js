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
        };

        // Handle dynamic routes like /platform/tenants/:id
        if (this.currentRoute.match(/\/platform\/tenants\/[^/]+$/)) {
            return 'Tenant Detail';
        }

        return titles[this.currentRoute] || 'Eye of God';
    }
}

customElements.define('eog-app', EogApp);
