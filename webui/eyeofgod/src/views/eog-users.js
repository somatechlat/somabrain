/**
 * User Management View (System Screen)
 * Route: /platform/users
 * 
 * Manage platform and tenant users.
 * Consumes /api/admin/users endpoint.
 * 
 * VIBE PERSONAS:
 * - Security: Role-based access display
 * - UX: Filterable, sortable user list
 * - Architect: Multi-tenant user awareness
 */

import { LitElement, html, css } from 'lit';
import { usersApi } from '../services/api.js';

export class EogUsers extends LitElement {
  static properties = {
    users: { type: Array },
    isLoading: { type: Boolean },
    searchQuery: { type: String },
    roleFilter: { type: String },
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

    h1 {
      margin: 0;
      font-size: 24px;
      color: var(--eog-text, #e4e4e7);
    }

    .btn-create {
      background: var(--eog-primary, #6366f1);
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 8px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .filters {
      display: flex;
      gap: 12px;
      margin-bottom: 24px;
    }

    .filter-input {
      flex: 1;
      padding: 10px 14px;
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 8px;
      color: var(--eog-text, #e4e4e7);
      font-size: 14px;
    }

    .filter-input::placeholder {
      color: var(--eog-text-muted, #a1a1aa);
    }

    select.filter-input {
      width: 180px;
      flex: none;
    }

    .user-table {
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      overflow: hidden;
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    thead th {
      text-align: left;
      padding: 14px 16px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--eog-text-muted, #a1a1aa);
      background: rgba(0, 0, 0, 0.2);
      border-bottom: 1px solid var(--eog-border, #27273a);
    }

    tbody tr {
      border-bottom: 1px solid var(--eog-border, #27273a);
    }

    tbody tr:last-child {
      border-bottom: none;
    }

    tbody tr:hover {
      background: rgba(255, 255, 255, 0.02);
    }

    td {
      padding: 14px 16px;
      font-size: 14px;
      color: var(--eog-text, #e4e4e7);
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: var(--eog-primary, #6366f1);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      color: white;
      font-size: 14px;
    }

    .user-name {
      font-weight: 500;
    }

    .user-email {
      font-size: 12px;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .role-badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 500;
    }

    .role-badge.super-admin { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
    .role-badge.tenant-admin { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
    .role-badge.tenant-user { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
    .role-badge.api-access { background: rgba(34, 197, 94, 0.2); color: #22c55e; }

    .status-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-right: 6px;
    }

    .status-dot.active { background: var(--eog-success, #22c55e); }
    .status-dot.inactive { background: var(--eog-text-muted, #a1a1aa); }

    .actions {
      display: flex;
      gap: 8px;
    }

    .action-btn {
      padding: 6px 10px;
      border: 1px solid var(--eog-border, #27273a);
      background: transparent;
      color: var(--eog-text, #e4e4e7);
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
    }

    .action-btn:hover {
      background: rgba(255, 255, 255, 0.05);
    }
  `;

  constructor() {
    super();
    this.users = [];
    this.isLoading = false;
    this.searchQuery = '';
    this.roleFilter = '';
    this.error = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._loadUsers();
  }

  async _loadUsers() {
    this.isLoading = true;
    this.error = null;
    try {
      const params = {};
      if (this.roleFilter) params.role = this.roleFilter;
      const result = await usersApi.list(params);
      this.users = result.users || result || [];
    } catch (err) {
      console.error('Failed to load users:', err);
      this.error = err.message;
      this.users = [];
    } finally {
      this.isLoading = false;
    }
  }

  async _toggleUserStatus(user) {
    try {
      if (user.is_active) {
        await usersApi.disable(user.id);
      } else {
        await usersApi.enable(user.id);
      }
      this._loadUsers();
    } catch (err) {
      console.error('Failed to toggle user status:', err);
      alert(`Failed to ${user.is_active ? 'disable' : 'enable'} user`);
    }
  }

  get filteredUsers() {
    let users = this.users;
    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      users = users.filter(u => u.email.toLowerCase().includes(q) || u.display_name?.toLowerCase().includes(q));
    }
    if (this.roleFilter) {
      users = users.filter(u => u.role === this.roleFilter);
    }
    return users;
  }

  _getInitials(name) {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  }

  render() {
    return html`
      <div class="view">
        <div class="header">
          <h1>Users</h1>
          <button class="btn-create">
            <span>+</span> Add User
          </button>
        </div>

        <div class="filters">
          <input 
            class="filter-input" 
            type="text" 
            placeholder="Search by name or email..." 
            .value=${this.searchQuery}
            @input=${e => this.searchQuery = e.target.value}
          >
          <select class="filter-input" .value=${this.roleFilter} @change=${e => this.roleFilter = e.target.value}>
            <option value="">All Roles</option>
            <option value="super-admin">Super Admin</option>
            <option value="tenant-admin">Tenant Admin</option>
            <option value="tenant-user">Tenant User</option>
            <option value="api-access">API Access</option>
          </select>
        </div>

        <div class="user-table">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Tenant</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${this.filteredUsers.map(user => html`
                <tr>
                  <td>
                    <div class="user-info">
                      <div class="avatar">${this._getInitials(user.display_name)}</div>
                      <div>
                        <div class="user-name">${user.display_name || user.email}</div>
                        <div class="user-email">${user.email}</div>
                      </div>
                    </div>
                  </td>
                  <td><span class="role-badge ${user.role}">${user.role}</span></td>
                  <td>${user.tenant?.slug || 'Platform'}</td>
                  <td>
                    <span class="status-dot ${user.is_active ? 'active' : 'inactive'}"></span>
                    ${user.is_active ? 'Active' : 'Inactive'}
                  </td>
                  <td>
                    <div class="actions">
                      <button class="action-btn">Edit</button>
                      <button class="action-btn" @click=${() => this._toggleUserStatus(user)}>${user.is_active ? 'Disable' : 'Enable'}</button>
                    </div>
                  </td>
                </tr>
              `)}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }
}

customElements.define('eog-users', EogUsers);
