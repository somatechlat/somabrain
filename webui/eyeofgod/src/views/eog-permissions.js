/**
 * Permission Browser View (Screen 29)
 * Route: /saas/permissions
 * 
 * Master-detail view for inspecting and editing role-based permission matrices.
 * Integrates with SpiceDB/Django RBAC backend.
 * 
 * VIBE PERSONAS:
 * - Security: Clear distinction between system (immutable) and custom roles.
 * - UX: Split-pane layout for rapid browsing.
 */

import { LitElement, html, css } from 'lit';
import { rolesApi } from '../services/api.js';
import '../components/auth/eog-role-editor.js';

export class SaasPermissionBrowser extends LitElement {
    static properties = {
        roles: { type: Array },
        selectedRole: { type: Object },
        matrix: { type: Array },
        isLoading: { type: Boolean },
        isLoadingMatrix: { type: Boolean },
    };

    static styles = css`
    :host {
      display: block;
      height: 100%;
      font-family: 'Inter', system-ui, sans-serif;
    }

    .layout {
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: 24px;
      height: 100%;
    }

    .sidebar {
      background: var(--eog-surface, #1a1a2e);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      border: 1px solid var(--eog-border, #27273a);
      overflow: hidden;
    }

    .sidebar-header {
      padding: 16px;
      border-bottom: 1px solid var(--eog-border, #27273a);
    }

    .sidebar-header h3 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
      color: var(--eog-text-muted, #a1a1aa);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .role-list {
      flex: 1;
      overflow-y: auto;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .role-item {
      padding: 10px 12px;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: all 0.2s;
      color: var(--eog-text, #e4e4e7);
      font-size: 14px;
    }

    .role-item:hover {
      background: rgba(255, 255, 255, 0.05);
    }

    .role-item.selected {
      background: var(--eog-primary, #6366f1);
      color: white;
    }

    .role-item.selected .role-badge {
      background: rgba(255, 255, 255, 0.2);
      color: white;
    }

    .role-badge {
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 4px;
      background: var(--eog-border, #27273a);
      color: var(--eog-text-muted, #a1a1aa);
    }

    .detail-pane {
      overflow-y: auto;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: var(--eog-text-muted, #a1a1aa);
      background: var(--eog-surface, #1a1a2e);
      border-radius: 12px;
      border: 1px solid var(--eog-border, #27273a);
    }
  `;

    constructor() {
        super();
        this.roles = [];
        this.selectedRole = null;
        this.matrix = [];
        this.isLoading = false;
        this.isLoadingMatrix = false;
    }

    connectedCallback() {
        super.connectedCallback();
        this._loadRoles();
    }

    async _loadRoles() {
        this.isLoading = true;
        try {
            this.roles = await rolesApi.list();
            if (this.roles.length > 0 && !this.selectedRole) {
                this._selectRole(this.roles[0]);
            }
        } catch (err) {
            console.error('Failed to load roles:', err);
            // In a real app we'd dispatch a toast event here
        } finally {
            this.isLoading = false;
        }
    }

    async _selectRole(role) {
        if (this.selectedRole?.id === role.id) return;

        this.selectedRole = role;
        this.isLoadingMatrix = true;
        this.matrix = [];

        try {
            this.matrix = await rolesApi.getMatrix(role.id);
        } catch (err) {
            console.error(`Failed to load matrix for ${role.name}:`, err);
        } finally {
            this.isLoadingMatrix = false;
        }
    }

    async _handleSave(e) {
        const { roleId, matrix } = e.detail;
        try {
            await rolesApi.updateMatrix(roleId, matrix);
            // Refresh matrix to confirming state
            await this._selectRole(this.selectedRole); // Re-fetch to be sure

            // Dispatch success toast (simulated)
            console.log('Permissions updated successfully');
        } catch (err) {
            console.error('Failed to save permissions:', err);
        }
    }

    _handleCancel() {
        // Just refresh the matrix to reset any local state in the editor
        if (this.selectedRole) {
            const role = this.selectedRole;
            this.selectedRole = null; // Force re-render of sub-component sort of
            setTimeout(() => this._selectRole(role), 0);
        }
    }

    render() {
        return html`
      <div class="layout">
        <aside class="sidebar">
          <div class="sidebar-header">
            <h3>System Roles</h3>
          </div>
          <div class="role-list">
            ${this.isLoading ? html`<div style="padding:12px;color:var(--eog-text-muted);">Loading...</div>` : ''}
            
            ${this.roles.map(role => html`
              <div 
                class="role-item ${this.selectedRole?.id === role.id ? 'selected' : ''}"
                @click=${() => this._selectRole(role)}
              >
                <span>${role.name}</span>
                ${role.is_system ? html`<span class="role-badge">SYSTEM</span>` : ''}
              </div>
            `)}
          </div>
        </aside>

        <main class="detail-pane">
          ${this.selectedRole ? html`
            <eog-role-editor
              .role=${this.selectedRole}
              .matrix=${this.matrix}
              .isLoading=${this.isLoadingMatrix}
              .isEditable=${!this.selectedRole.is_system} 
              @save=${this._handleSave}
              @cancel=${this._handleCancel}
            ></eog-role-editor>
          ` : html`
            <div class="empty-state">
              <p>Select a role to view permissions</p>
            </div>
          `}
        </main>
      </div>
    `;
    }
}

customElements.define('saas-permission-browser', SaasPermissionBrowser);
