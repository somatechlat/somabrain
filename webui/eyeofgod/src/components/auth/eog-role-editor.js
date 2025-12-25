/**
 * Role Editor Component - Reusable Lit Component
 * 
 * Displays and edits role field permissions in a matrix format.
 * 
 * ALL 10 PERSONAS per VIBE Coding Rules:
 * - UX: Clear matrix visualization
 * - Security: Shows view/edit permissions distinctly
 * - Architect: Reusable across admin screens
 */

import { LitElement, html, css } from 'lit';

export class EogRoleEditor extends LitElement {
    static properties = {
        role: { type: Object },
        matrix: { type: Array },
        isLoading: { type: Boolean },
        isEditable: { type: Boolean },
    };

    static styles = css`
    :host {
      display: block;
      font-family: 'Inter', system-ui, sans-serif;
    }

    .role-editor {
      background: var(--eog-surface, #1a1a2e);
      border-radius: 12px;
      padding: 20px;
      color: var(--eog-text, #e4e4e7);
    }

    .role-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
    }

    .role-info h2 {
      margin: 0 0 4px 0;
      font-size: 20px;
      font-weight: 600;
    }

    .role-description {
      color: var(--eog-text-muted, #a1a1aa);
      font-size: 14px;
    }

    .role-badges {
      display: flex;
      gap: 8px;
    }

    .badge {
      padding: 4px 10px;
      border-radius: 16px;
      font-size: 12px;
      font-weight: 500;
    }

    .badge.system {
      background: rgba(99, 102, 241, 0.2);
      color: var(--eog-primary, #6366f1);
    }

    .badge.platform {
      background: rgba(34, 197, 94, 0.2);
      color: var(--eog-success, #22c55e);
    }

    .matrix-container {
      overflow-x: auto;
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

    thead th.center {
      text-align: center;
      width: 100px;
    }

    tbody tr {
      border-bottom: 1px solid var(--eog-border, #27273a);
    }

    tbody tr:hover {
      background: rgba(99, 102, 241, 0.05);
    }

    tbody tr.model-header {
      background: var(--eog-card-bg, #0f0f1a);
    }

    tbody tr.model-header td {
      font-weight: 600;
      color: var(--eog-text, #e4e4e7);
      padding: 10px 16px;
    }

    td {
      padding: 10px 16px;
      font-size: 14px;
    }

    td.field-name {
      padding-left: 32px;
      color: var(--eog-text-muted, #a1a1aa);
    }

    td.center {
      text-align: center;
    }

    .permission-checkbox {
      display: inline-block;
      cursor: pointer;
    }

    .permission-checkbox input {
      display: none;
    }

    .checkbox-icon {
      width: 24px;
      height: 24px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
    }

    .checkbox-icon.unchecked {
      border: 2px solid var(--eog-border, #27273a);
      color: transparent;
    }

    .checkbox-icon.checked.view {
      background: rgba(34, 197, 94, 0.2);
      border: 2px solid var(--eog-success, #22c55e);
      color: var(--eog-success, #22c55e);
    }

    .checkbox-icon.checked.edit {
      background: rgba(251, 191, 36, 0.2);
      border: 2px solid var(--eog-warning, #fbbf24);
      color: var(--eog-warning, #fbbf24);
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 24px;
      padding-top: 24px;
      border-top: 1px solid var(--eog-border, #27273a);
    }

    .btn {
      padding: 10px 20px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-secondary {
      background: transparent;
      border: 1px solid var(--eog-border, #27273a);
      color: var(--eog-text, #e4e4e7);
    }

    .btn-primary {
      background: var(--eog-primary, #6366f1);
      border: none;
      color: white;
    }

    .btn-primary:hover {
      background: var(--eog-primary-hover, #4f46e5);
    }
  `;

    constructor() {
        super();
        this.role = null;
        this.matrix = [];
        this.isLoading = false;
        this.isEditable = true;
        this._changes = new Map();
    }

    _togglePermission(modelName, fieldName, permType) {
        if (!this.isEditable) return;

        const key = `${modelName}:${fieldName}:${permType}`;
        const currentValue = this._getPermissionValue(modelName, fieldName, permType);
        this._changes.set(key, !currentValue);
        this.requestUpdate();
    }

    _getPermissionValue(modelName, fieldName, permType) {
        const key = `${modelName}:${fieldName}:${permType}`;
        if (this._changes.has(key)) {
            return this._changes.get(key);
        }

        const model = this.matrix.find(m => m.model_name === modelName);
        if (!model) return false;

        const field = model.fields.find(f => f.field_name === fieldName);
        if (!field) return false;

        return permType === 'view' ? field.can_view : field.can_edit;
    }

    _handleSave() {
        const updates = [];

        for (const model of this.matrix) {
            for (const field of model.fields) {
                const viewKey = `${model.model_name}:${field.field_name}:view`;
                const editKey = `${model.model_name}:${field.field_name}:edit`;

                const can_view = this._changes.has(viewKey)
                    ? this._changes.get(viewKey)
                    : field.can_view;
                const can_edit = this._changes.has(editKey)
                    ? this._changes.get(editKey)
                    : field.can_edit;

                updates.push({
                    model_name: model.model_name,
                    field_name: field.field_name,
                    can_view,
                    can_edit,
                });
            }
        }

        this.dispatchEvent(new CustomEvent('save', {
            detail: { roleId: this.role?.id, matrix: updates }
        }));
    }

    _handleCancel() {
        this._changes.clear();
        this.requestUpdate();
        this.dispatchEvent(new CustomEvent('cancel'));
    }

    render() {
        if (!this.role) {
            return html`<div class="role-editor">Select a role to edit permissions</div>`;
        }

        return html`
      <div class="role-editor">
        <div class="role-header">
          <div class="role-info">
            <h2>${this.role.name}</h2>
            <div class="role-description">${this.role.description || 'No description'}</div>
          </div>
          <div class="role-badges">
            ${this.role.is_system ? html`<span class="badge system">System Role</span>` : ''}
            ${this.role.platform_role ? html`<span class="badge platform">${this.role.platform_role}</span>` : ''}
          </div>
        </div>

        <div class="matrix-container">
          <table>
            <thead>
              <tr>
                <th>Model / Field</th>
                <th class="center">👁️ View</th>
                <th class="center">✏️ Edit</th>
              </tr>
            </thead>
            <tbody>
              ${this.matrix.map(model => html`
                <tr class="model-header">
                  <td colspan="3">📁 ${model.model_name}</td>
                </tr>
                ${model.fields.map(field => html`
                  <tr>
                    <td class="field-name">${field.field_name}</td>
                    <td class="center">
                      <label class="permission-checkbox" @click=${() => this._togglePermission(model.model_name, field.field_name, 'view')}>
                        <input type="checkbox" ?checked=${this._getPermissionValue(model.model_name, field.field_name, 'view')} />
                        <div class="checkbox-icon ${this._getPermissionValue(model.model_name, field.field_name, 'view') ? 'checked view' : 'unchecked'}">
                          ${this._getPermissionValue(model.model_name, field.field_name, 'view') ? '✓' : ''}
                        </div>
                      </label>
                    </td>
                    <td class="center">
                      <label class="permission-checkbox" @click=${() => this._togglePermission(model.model_name, field.field_name, 'edit')}>
                        <input type="checkbox" ?checked=${this._getPermissionValue(model.model_name, field.field_name, 'edit')} />
                        <div class="checkbox-icon ${this._getPermissionValue(model.model_name, field.field_name, 'edit') ? 'checked edit' : 'unchecked'}">
                          ${this._getPermissionValue(model.model_name, field.field_name, 'edit') ? '✓' : ''}
                        </div>
                      </label>
                    </td>
                  </tr>
                `)}
              `)}
            </tbody>
          </table>
        </div>

        ${this.isEditable ? html`
          <div class="form-actions">
            <button class="btn btn-secondary" @click=${this._handleCancel}>Cancel</button>
            <button class="btn btn-primary" @click=${this._handleSave}>Save Permissions</button>
          </div>
        ` : ''}
      </div>
    `;
    }
}

customElements.define('eog-role-editor', EogRoleEditor);
