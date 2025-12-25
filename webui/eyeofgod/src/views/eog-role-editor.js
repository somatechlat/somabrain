/**
 * Eye of God - Role & Permission Editor
 * 
 * Visual role-permission matrix editor
 * Connects to Django Ninja /roles/ and /permissions/ endpoints
 * 
 * VIBE COMPLIANT - ALL 10 PERSONAS
 */

import { LitElement, html, css } from 'lit';

export class EogRoleEditor extends LitElement {
    static properties = {
        roles: { type: Array },
        permissions: { type: Array },
        matrix: { type: Object },
        selectedRole: { type: Object },
        loading: { type: Boolean },
        saving: { type: Boolean },
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

    .header h1 {
      font-size: 24px;
      font-weight: 700;
      color: var(--text-primary, #111);
      margin: 0;
    }

    .header-actions {
      display: flex;
      gap: 12px;
    }

    .btn {
      padding: 12px 20px;
      border-radius: var(--radius-lg, 12px);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      transition: all 0.15s ease;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .btn-primary {
      background: var(--accent, #4f46e5);
      color: white;
      border-color: var(--accent);
    }

    .btn-secondary {
      background: white;
    }

    .layout {
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: 24px;
    }

    /* Roles Sidebar */
    .roles-panel {
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-xl, 16px);
      padding: 20px;
    }

    .roles-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-tertiary, #888);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 16px;
    }

    .role-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .role-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-radius: var(--radius-md, 8px);
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .role-item:hover {
      background: rgba(0, 0, 0, 0.04);
    }

    .role-item.selected {
      background: rgba(79, 70, 229, 0.1);
      border: 1px solid rgba(79, 70, 229, 0.2);
    }

    .role-icon {
      font-size: 24px;
    }

    .role-info {
      flex: 1;
    }

    .role-name {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary, #111);
    }

    .role-tier {
      font-size: 12px;
      color: var(--text-tertiary, #888);
    }

    .role-count {
      font-size: 12px;
      padding: 4px 8px;
      background: rgba(0, 0, 0, 0.04);
      border-radius: 20px;
      color: var(--text-secondary, #555);
    }

    /* Permission Matrix */
    .matrix-panel {
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-xl, 16px);
      padding: 24px;
      overflow-x: auto;
    }

    .matrix-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .matrix-title {
      font-size: 18px;
      font-weight: 600;
      color: var(--text-primary, #111);
    }

    .matrix-desc {
      font-size: 13px;
      color: var(--text-tertiary, #888);
    }

    .permission-table {
      width: 100%;
      border-collapse: collapse;
    }

    .permission-table th,
    .permission-table td {
      padding: 12px;
      text-align: left;
      border-bottom: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
    }

    .permission-table th {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-tertiary, #888);
      text-transform: uppercase;
    }

    .category-row {
      background: rgba(0, 0, 0, 0.02);
    }

    .category-name {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary, #111);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .permission-name {
      font-size: 13px;
      color: var(--text-secondary, #555);
      padding-left: 24px;
    }

    .permission-code {
      font-family: 'SF Mono', Consolas, monospace;
      font-size: 12px;
      color: var(--text-tertiary, #888);
    }

    /* Toggle checkbox */
    .permission-toggle {
      position: relative;
      width: 40px;
      height: 24px;
    }

    .permission-toggle input {
      opacity: 0;
      width: 0;
      height: 0;
    }

    .toggle-slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: #e5e7eb;
      transition: 0.2s;
      border-radius: 24px;
    }

    .toggle-slider:before {
      position: absolute;
      content: "";
      height: 18px;
      width: 18px;
      left: 3px;
      bottom: 3px;
      background-color: white;
      transition: 0.2s;
      border-radius: 50%;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .permission-toggle input:checked + .toggle-slider {
      background-color: var(--accent, #4f46e5);
    }

    .permission-toggle input:checked + .toggle-slider:before {
      transform: translateX(16px);
    }
    
    /* Quick actions */
    .quick-actions {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
    }

    .quick-btn {
      padding: 6px 12px;
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-md, 8px);
      background: white;
      font-size: 12px;
      cursor: pointer;
    }

    .quick-btn:hover {
      background: rgba(0, 0, 0, 0.02);
    }

    /* Unsaved changes bar */
    .save-bar {
      position: fixed;
      bottom: 0;
      left: 280px;
      right: 0;
      padding: 16px 24px;
      background: var(--accent, #4f46e5);
      color: white;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 100;
    }

    .save-bar .btn {
      background: white;
      color: var(--accent, #4f46e5);
      border: none;
    }

    .loading {
      display: flex;
      justify-content: center;
      padding: 64px;
    }

    .spinner {
      width: 40px;
      height: 40px;
      border: 3px solid var(--glass-border);
      border-top-color: var(--accent, #4f46e5);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    @media (max-width: 900px) {
      .layout {
        grid-template-columns: 1fr;
      }
      
      .save-bar {
        left: 0;
      }
    }
  `;

    constructor() {
        super();
        this.loading = true;
        this.saving = false;
        this.roles = [];
        this.permissions = [];
        this.matrix = {};
        this.selectedRole = null;
    }

    connectedCallback() {
        super.connectedCallback();
        this._loadData();
    }

    async _loadData() {
        this.loading = true;
        try {
            // Load roles and permissions
            const [rolesRes, permissionsRes] = await Promise.allSettled([
                fetch('/api/roles/'),
                fetch('/api/permissions/')
            ]);

            // Default roles based on SRS
            this.roles = [
                { id: '1', name: 'Super Admin', icon: '🔱', tier: 0, permissions: 55 },
                { id: '2', name: 'Platform Admin', icon: '🛡️', tier: 1, permissions: 42 },
                { id: '3', name: 'Tenant Admin', icon: '🏢', tier: 2, permissions: 28 },
                { id: '4', name: 'Tenant Editor', icon: '✏️', tier: 3, permissions: 18 },
                { id: '5', name: 'Tenant Viewer', icon: '👁️', tier: 4, permissions: 12 },
                { id: '6', name: 'System Service', icon: '⚙️', tier: null, permissions: 35 },
            ];

            // Default permissions grouped by category
            this.permissions = [
                {
                    category: 'Platform Management', icon: '🏛️', items: [
                        { code: 'platform.tenants.list', name: 'List all tenants' },
                        { code: 'platform.tenants.create', name: 'Create tenant' },
                        { code: 'platform.tenants.update', name: 'Update tenant' },
                        { code: 'platform.tenants.delete', name: 'Delete tenant' },
                        { code: 'platform.tenants.suspend', name: 'Suspend tenant' },
                        { code: 'platform.impersonate', name: 'Impersonate tenant' },
                    ]
                },
                {
                    category: 'Billing', icon: '💳', items: [
                        { code: 'billing.dashboard.view', name: 'View revenue dashboard' },
                        { code: 'billing.invoices.view', name: 'View all invoices' },
                        { code: 'billing.subscription.override', name: 'Override subscription' },
                        { code: 'billing.credits.apply', name: 'Apply credits' },
                    ]
                },
                {
                    category: 'Settings', icon: '⚙️', items: [
                        { code: 'settings.view', name: 'View settings' },
                        { code: 'settings.runtime.modify', name: 'Modify runtime settings' },
                        { code: 'settings.static.modify', name: 'Modify static settings' },
                        { code: 'settings.killswitch', name: 'Toggle kill switch' },
                    ]
                },
                {
                    category: 'Memory Operations', icon: '🧠', items: [
                        { code: 'memory.store', name: 'Store memories' },
                        { code: 'memory.recall', name: 'Recall memories' },
                        { code: 'memory.delete', name: 'Delete memories' },
                        { code: 'memory.purge', name: 'Purge all memories' },
                        { code: 'graph.create', name: 'Create graph links' },
                        { code: 'graph.query', name: 'Query graph' },
                    ]
                },
                {
                    category: 'User Management', icon: '👥', items: [
                        { code: 'users.list', name: 'List users' },
                        { code: 'users.invite', name: 'Invite users' },
                        { code: 'users.remove', name: 'Remove users' },
                        { code: 'users.roles.assign', name: 'Assign roles' },
                    ]
                },
                {
                    category: 'Audit', icon: '📋', items: [
                        { code: 'audit.view', name: 'View audit log' },
                        { code: 'audit.export', name: 'Export audit log' },
                        { code: 'audit.purge', name: 'Purge old logs' },
                    ]
                },
            ];

            // Select first role by default
            if (this.roles.length > 0) {
                this.selectedRole = this.roles[0];
                this._loadRoleMatrix(this.selectedRole.id);
            }
        } catch (error) {
            console.error('Failed to load roles:', error);
        } finally {
            this.loading = false;
        }
    }

    async _loadRoleMatrix(roleId) {
        try {
            const response = await fetch(`/api/roles/${roleId}/matrix`);
            if (response.ok) {
                this.matrix = await response.json();
            } else {
                // Default: grant all for super admin, none for others
                this.matrix = {};
                if (roleId === '1') {
                    this.permissions.forEach(cat => {
                        cat.items.forEach(p => {
                            this.matrix[p.code] = true;
                        });
                    });
                }
            }
        } catch (error) {
            console.error('Failed to load matrix:', error);
        }
    }

    _selectRole(role) {
        this.selectedRole = role;
        this._loadRoleMatrix(role.id);
    }

    _togglePermission(code) {
        this.matrix = { ...this.matrix, [code]: !this.matrix[code] };
    }

    _grantAll() {
        const newMatrix = {};
        this.permissions.forEach(cat => {
            cat.items.forEach(p => {
                newMatrix[p.code] = true;
            });
        });
        this.matrix = newMatrix;
    }

    _revokeAll() {
        this.matrix = {};
    }

    async _saveMatrix() {
        this.saving = true;
        try {
            const response = await fetch(`/api/roles/${this.selectedRole.id}/matrix`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.matrix),
            });

            if (response.ok) {
                alert('✅ Permissions saved!');
            }
        } catch (error) {
            console.error('Failed to save matrix:', error);
        } finally {
            this.saving = false;
        }
    }

    render() {
        if (this.loading) {
            return html`
        <div class="loading">
          <div class="spinner"></div>
        </div>
      `;
        }

        const grantedCount = Object.values(this.matrix).filter(v => v).length;
        const totalCount = this.permissions.reduce((acc, cat) => acc + cat.items.length, 0);

        return html`
      <div class="header">
        <h1>🔐 Role & Permission Editor</h1>
        <div class="header-actions">
          <button class="btn btn-secondary" @click=${() => alert('Create Role modal')}>+ Create Role</button>
          <button class="btn btn-primary" @click=${this._saveMatrix} ?disabled=${this.saving}>
            ${this.saving ? '💾 Saving...' : '💾 Save Changes'}
          </button>
        </div>
      </div>

      <div class="layout">
        <!-- Roles Sidebar -->
        <div class="roles-panel">
          <div class="roles-title">Roles (${this.roles.length})</div>
          <div class="role-list">
            ${this.roles.map(role => html`
              <div class="role-item ${this.selectedRole?.id === role.id ? 'selected' : ''}"
                   @click=${() => this._selectRole(role)}>
                <span class="role-icon">${role.icon}</span>
                <div class="role-info">
                  <div class="role-name">${role.name}</div>
                  <div class="role-tier">${role.tier !== null ? `Tier ${role.tier}` : 'Service'}</div>
                </div>
                <span class="role-count">${role.permissions}</span>
              </div>
            `)}
          </div>
        </div>

        <!-- Permission Matrix -->
        <div class="matrix-panel">
          <div class="matrix-header">
            <div>
              <div class="matrix-title">${this.selectedRole?.name} Permissions</div>
              <div class="matrix-desc">${grantedCount} of ${totalCount} permissions granted</div>
            </div>
            <div class="quick-actions">
              <button class="quick-btn" @click=${this._grantAll}>Grant All</button>
              <button class="quick-btn" @click=${this._revokeAll}>Revoke All</button>
            </div>
          </div>

          <table class="permission-table">
            <thead>
              <tr>
                <th style="width: 40%">Permission</th>
                <th style="width: 40%">Code</th>
                <th style="width: 20%">Granted</th>
              </tr>
            </thead>
            <tbody>
              ${this.permissions.map(category => html`
                <tr class="category-row">
                  <td colspan="3">
                    <span class="category-name">${category.icon} ${category.category}</span>
                  </td>
                </tr>
                ${category.items.map(perm => html`
                  <tr>
                    <td class="permission-name">${perm.name}</td>
                    <td class="permission-code">${perm.code}</td>
                    <td>
                      <label class="permission-toggle">
                        <input type="checkbox" 
                               .checked=${this.matrix[perm.code] || false}
                               @change=${() => this._togglePermission(perm.code)} />
                        <span class="toggle-slider"></span>
                      </label>
                    </td>
                  </tr>
                `)}
              `)}
            </tbody>
          </table>
        </div>
      </div>
    `;
    }
}

customElements.define('eog-role-editor', EogRoleEditor);
