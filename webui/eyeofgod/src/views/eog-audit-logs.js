/**
 * Audit Logs View (System Screen)
 * Route: /platform/audit
 * 
 * Displays system audit trail with filtering capabilities.
 * Consumes /api/audit/ endpoint.
 * 
 * VIBE PERSONAS:
 * - Security: Complete action visibility
 * - Compliance: Immutable log display
 * - UX: Filterable, searchable logs
 */

import { LitElement, html, css } from 'lit';
import { auditApi } from '../services/api.js';

export class EogAuditLogs extends LitElement {
    static properties = {
        logs: { type: Array },
        isLoading: { type: Boolean },
        filters: { type: Object },
        page: { type: Number },
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

    .filters {
      display: flex;
      gap: 12px;
      margin-bottom: 24px;
    }

    .filter-input {
      padding: 8px 12px;
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 8px;
      color: var(--eog-text, #e4e4e7);
      font-size: 14px;
    }

    .filter-input::placeholder {
      color: var(--eog-text-muted, #a1a1aa);
    }

    .log-table {
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
      padding: 12px 16px;
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
      padding: 12px 16px;
      font-size: 14px;
      color: var(--eog-text, #e4e4e7);
    }

    .action-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
      background: var(--eog-border, #27273a);
    }

    .action-badge.create { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
    .action-badge.update { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
    .action-badge.delete { background: rgba(239, 68, 68, 0.2); color: #ef4444; }

    .timestamp {
      color: var(--eog-text-muted, #a1a1aa);
      font-size: 12px;
    }

    .pagination {
      display: flex;
      justify-content: center;
      gap: 8px;
      margin-top: 24px;
    }

    .page-btn {
      padding: 8px 12px;
      border: 1px solid var(--eog-border, #27273a);
      background: transparent;
      color: var(--eog-text, #e4e4e7);
      border-radius: 6px;
      cursor: pointer;
    }

    .page-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  `;

    constructor() {
        super();
        this.logs = [];
        this.isLoading = false;
        this.filters = { action: '', actor: '' };
        this.page = 1;
    }

    connectedCallback() {
        super.connectedCallback();
        this._loadLogs();
    }

    async _loadLogs() {
        this.isLoading = true;
        try {
            const params = { page: this.page };
            if (this.filters.action) params.action = this.filters.action;
            if (this.filters.actor) params.actor = this.filters.actor;

            const result = await auditApi.list(params);
            this.logs = result.logs || result;
        } catch (err) {
            console.error('Failed to load audit logs:', err);
        } finally {
            this.isLoading = false;
        }
    }

    _handleFilterChange(e) {
        const field = e.target.dataset.field;
        this.filters = { ...this.filters, [field]: e.target.value };
    }

    _applyFilters() {
        this.page = 1;
        this._loadLogs();
    }

    _getActionType(action) {
        if (action.includes('created') || action.includes('create')) return 'create';
        if (action.includes('updated') || action.includes('update')) return 'update';
        if (action.includes('deleted') || action.includes('delete')) return 'delete';
        return '';
    }

    render() {
        return html`
      <div class="view">
        <div class="header">
          <h1>Audit Logs</h1>
        </div>

        <div class="filters">
          <input 
            class="filter-input" 
            type="text" 
            placeholder="Filter by action..." 
            data-field="action"
            .value=${this.filters.action}
            @input=${this._handleFilterChange}
          >
          <input 
            class="filter-input" 
            type="text" 
            placeholder="Filter by actor..." 
            data-field="actor"
            .value=${this.filters.actor}
            @input=${this._handleFilterChange}
          >
          <button class="page-btn" @click=${this._applyFilters}>Apply</button>
        </div>

        <div class="log-table">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Actor</th>
                <th>IP Address</th>
              </tr>
            </thead>
            <tbody>
              ${this.logs.map(log => html`
                <tr>
                  <td class="timestamp">${new Date(log.timestamp).toLocaleString()}</td>
                  <td><span class="action-badge ${this._getActionType(log.action)}">${log.action}</span></td>
                  <td>${log.resource_type}/${log.resource_id?.slice(0, 8) || '-'}</td>
                  <td>${log.actor_email || log.actor_id?.slice(0, 8) || 'System'}</td>
                  <td>${log.ip_address || '-'}</td>
                </tr>
              `)}
              ${this.logs.length === 0 ? html`
                <tr><td colspan="5" style="text-align:center;color:var(--eog-text-muted);">No logs found</td></tr>
              ` : ''}
            </tbody>
          </table>
        </div>

        <div class="pagination">
          <button class="page-btn" ?disabled=${this.page <= 1} @click=${() => { this.page--; this._loadLogs(); }}>← Previous</button>
          <span style="color:var(--eog-text-muted);padding:8px;">Page ${this.page}</span>
          <button class="page-btn" @click=${() => { this.page++; this._loadLogs(); }}>Next →</button>
        </div>
      </div>
    `;
    }
}

customElements.define('eog-audit-logs', EogAuditLogs);
