/**
 * User Management List - Reusable Lit Component
 * 
 * Displays users with role assignments and management actions.
 * 
 * ALL 10 PERSONAS per VIBE Coding Rules:
 * - UX: Clear user status indicators
 * - Security: Shows role assignments
 * - Architect: Reusable across admin screens
 */

import { LitElement, html, css } from 'lit';

export class EogUserList extends LitElement {
    static properties = {
        users: { type: Array },
        roles: { type: Array },
        isLoading: { type: Boolean },
        selectedUserId: { type: String },
        filters: { type: Object },
    };

    static styles = css`
    :host {
      display: block;
      font-family: 'Inter', system-ui, sans-serif;
    }

    .user-list-container {
      background: var(--eog-surface, #1a1a2e);
      border-radius: 12px;
      padding: 20px;
      color: var(--eog-text, #e4e4e7);
    }

    .list-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .list-title {
      font-size: 18px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .header-actions {
      display: flex;
      gap: 12px;
    }

    .btn {
      padding: 10px 16px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .btn-primary {
      background: var(--eog-primary, #6366f1);
      border: none;
      color: white;
    }

    .btn-primary:hover {
      background: var(--eog-primary-hover, #4f46e5);
    }

    .filters {
      display: flex;
      gap: 12px;
      margin-bottom: 16px;
    }

    .filter-input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 8px;
      background: var(--eog-input-bg, #0f0f1a);
      color: var(--eog-text, #e4e4e7);
      font-size: 14px;
    }

    .filter-select {
      padding: 10px 14px;
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 8px;
      background: var(--eog-input-bg, #0f0f1a);
      color: var(--eog-text, #e4e4e7);
      font-size: 14px;
      min-width: 140px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    thead th {
      text-align: left;
      padding: 12px 16px;
      background: var(--eog-card-bg, #0f0f1a);
      font-size: 13px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--eog-text-muted, #a1a1aa);
      border-bottom: 1px solid var(--eog-border, #27273a);
    }

    tbody tr {
      border-bottom: 1px solid var(--eog-border, #27273a);
      cursor: pointer;
      transition: background 0.2s;
    }

    tbody tr:hover {
      background: rgba(99, 102, 241, 0.05);
    }

    tbody tr.selected {
      background: rgba(99, 102, 241, 0.1);
    }

    td {
      padding: 12px 16px;
      font-size: 14px;
    }

    .user-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: 600;
      font-size: 14px;
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .user-name {
      font-weight: 500;
    }

    .user-email {
      color: var(--eog-text-muted, #a1a1aa);
      font-size: 13px;
    }

    .role-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .role-tag {
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 500;
    }

    .role-tag.super-admin {
      background: rgba(239, 68, 68, 0.2);
      color: #ef4444;
    }

    .role-tag.tenant-admin {
      background: rgba(251, 191, 36, 0.2);
      color: #fbbf24;
    }

    .role-tag.tenant-user {
      background: rgba(34, 197, 94, 0.2);
      color: #22c55e;
    }

    .role-tag.api-access {
      background: rgba(99, 102, 241, 0.2);
      color: #6366f1;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 10px;
      border-radius: 16px;
      font-size: 12px;
      font-weight: 500;
    }

    .status-badge.active {
      background: rgba(34, 197, 94, 0.2);
      color: #22c55e;
    }

    .status-badge.inactive {
      background: rgba(239, 68, 68, 0.2);
      color: #ef4444;
    }

    .actions-cell {
      display: flex;
      gap: 8px;
    }

    .btn-action {
      padding: 6px;
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 6px;
      background: transparent;
      color: var(--eog-text-muted, #a1a1aa);
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-action:hover {
      background: var(--eog-border, #27273a);
      color: var(--eog-text, #e4e4e7);
    }

    .btn-action.danger:hover {
      background: rgba(239, 68, 68, 0.2);
      color: #ef4444;
      border-color: #ef4444;
    }

    .empty-state {
      padding: 48px;
      text-align: center;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .pagination {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid var(--eog-border, #27273a);
    }
  `;

    constructor() {
        super();
        this.users = [];
        this.roles = [];
        this.isLoading = false;
        this.selectedUserId = null;
        this.filters = { search: '', role: '', status: '' };
    }

    _getInitials(displayName, email) {
        if (displayName) {
            return displayName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        }
        return email.substring(0, 2).toUpperCase();
    }

    _getRoleClass(roleSlug) {
        return roleSlug.replace('_', '-');
    }

    _handleFilterChange(e, filterName) {
        this.filters = { ...this.filters, [filterName]: e.target.value };
        this.dispatchEvent(new CustomEvent('filter-change', {
            detail: { filters: this.filters }
        }));
    }

    _handleAddUser() {
        this.dispatchEvent(new CustomEvent('add-user'));
    }

    _handleSelectUser(user) {
        this.selectedUserId = user.id;
        this.dispatchEvent(new CustomEvent('select-user', {
            detail: { user }
        }));
    }

    _handleEditUser(user, e) {
        e.stopPropagation();
        this.dispatchEvent(new CustomEvent('edit-user', {
            detail: { user }
        }));
    }

    _handleToggleStatus(user, e) {
        e.stopPropagation();
        this.dispatchEvent(new CustomEvent('toggle-status', {
            detail: { user, is_active: !user.is_active }
        }));
    }

    render() {
        return html`
      <div class="user-list-container">
        <div class="list-header">
          <div class="list-title">
            <span>👥</span>
            User Management
          </div>
          <div class="header-actions">
            <button class="btn btn-primary" @click=${this._handleAddUser}>
              + Add User
            </button>
          </div>
        </div>

        <div class="filters">
          <input 
            type="text" 
            class="filter-input" 
            placeholder="Search by name or email..."
            .value=${this.filters.search}
            @input=${(e) => this._handleFilterChange(e, 'search')}
          />
          <select 
            class="filter-select"
            .value=${this.filters.role}
            @change=${(e) => this._handleFilterChange(e, 'role')}
          >
            <option value="">All Roles</option>
            ${this.roles.map(role => html`
              <option value=${role.slug}>${role.name}</option>
            `)}
          </select>
          <select 
            class="filter-select"
            .value=${this.filters.status}
            @change=${(e) => this._handleFilterChange(e, 'status')}
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>

        ${this.isLoading ? html`<div class="empty-state">Loading...</div>` : html`
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Roles</th>
                <th>Tenant</th>
                <th>Status</th>
                <th>Last Login</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${this.users.length === 0 ? html`
                <tr>
                  <td colspan="6" class="empty-state">No users found</td>
                </tr>
              ` : this.users.map(user => html`
                <tr 
                  class=${this.selectedUserId === user.id ? 'selected' : ''}
                  @click=${() => this._handleSelectUser(user)}
                >
                  <td>
                    <div class="user-info">
                      <div class="user-avatar">
                        ${this._getInitials(user.display_name, user.email)}
                      </div>
                      <div>
                        <div class="user-name">${user.display_name || user.email}</div>
                        <div class="user-email">${user.email}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div class="role-tags">
                      ${(user.roles || []).map(role => html`
                        <span class="role-tag ${this._getRoleClass(role.slug || role)}">${role.name || role}</span>
                      `)}
                    </div>
                  </td>
                  <td>${user.tenant?.name || '-'}</td>
                  <td>
                    <span class="status-badge ${user.is_active ? 'active' : 'inactive'}">
                      ${user.is_active ? '✓ Active' : '○ Inactive'}
                    </span>
                  </td>
                  <td>${user.last_login_at || '-'}</td>
                  <td class="actions-cell" @click=${(e) => e.stopPropagation()}>
                    <button class="btn-action" title="Edit" @click=${(e) => this._handleEditUser(user, e)}>✏️</button>
                    <button 
                      class="btn-action ${!user.is_active ? '' : 'danger'}" 
                      title="${user.is_active ? 'Disable' : 'Enable'}"
                      @click=${(e) => this._handleToggleStatus(user, e)}
                    >${user.is_active ? '⏸️' : '▶️'}</button>
                  </td>
                </tr>
              `)}
            </tbody>
          </table>
        `}
      </div>
    `;
    }
}

customElements.define('eog-user-list', EogUserList);
