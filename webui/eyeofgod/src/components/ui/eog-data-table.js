/**
 * Eye of God - Reusable Data Table Component
 * 
 * Generic CRUD table that handles 90% of admin screens:
 * - Tenants list, Users list, Invoices, Audit logs, API keys, etc.
 * 
 * ABSTRACTION PATTERN: One component, many screens
 * 
 * VIBE COMPLIANT - ALL 10 PERSONAS
 */

import { LitElement, html, css } from 'lit';

export class EogDataTable extends LitElement {
    static properties = {
        // Configuration
        title: { type: String },
        icon: { type: String },
        endpoint: { type: String },
        columns: { type: Array },
        actions: { type: Array },

        // State
        data: { type: Array },
        loading: { type: Boolean },
        error: { type: String },
        searchQuery: { type: String },
        currentPage: { type: Number },
        totalPages: { type: Number },
        selectedItems: { type: Array },
        sortColumn: { type: String },
        sortDirection: { type: String },
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
      flex-wrap: wrap;
      gap: 16px;
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
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
      padding: 10px 18px;
      border-radius: var(--radius-lg, 12px);
      font-size: 14px;
      font-weight: 500;
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

    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 20px -4px rgba(79, 70, 229, 0.3);
    }

    .btn-secondary {
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
    }

    .btn-secondary:hover {
      background: rgba(0, 0, 0, 0.04);
    }

    .toolbar {
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
      flex-wrap: wrap;
      align-items: center;
    }

    .search-box {
      flex: 1;
      min-width: 200px;
      position: relative;
    }

    .search-box input {
      width: 100%;
      padding: 12px 16px 12px 44px;
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-lg, 12px);
      font-size: 14px;
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      box-sizing: border-box;
    }

    .search-box input:focus {
      outline: none;
      border-color: var(--accent, #4f46e5);
      box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1);
    }

    .search-icon {
      position: absolute;
      left: 16px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-tertiary, #888);
    }

    .filter-group {
      display: flex;
      gap: 8px;
    }

    .filter-btn {
      padding: 8px 14px;
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      border-radius: var(--radius-md, 8px);
      font-size: 13px;
      cursor: pointer;
      color: var(--text-secondary, #555);
    }

    .filter-btn.active {
      background: var(--accent, #4f46e5);
      color: white;
      border-color: var(--accent);
    }

    .table-card {
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-xl, 16px);
      overflow: hidden;
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    thead {
      background: rgba(0, 0, 0, 0.02);
    }

    th {
      padding: 14px 16px;
      text-align: left;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-tertiary, #888);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-bottom: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      cursor: pointer;
      user-select: none;
    }

    th:hover {
      background: rgba(0, 0, 0, 0.03);
    }

    th .sort-icon {
      margin-left: 4px;
      opacity: 0.5;
    }

    th.sorted .sort-icon {
      opacity: 1;
    }

    td {
      padding: 16px;
      font-size: 14px;
      color: var(--text-secondary, #555);
      border-bottom: 1px solid var(--glass-border, rgba(0, 0, 0, 0.04));
    }

    tr:hover {
      background: rgba(0, 0, 0, 0.02);
    }

    tr:last-child td {
      border-bottom: none;
    }

    .cell-checkbox {
      width: 48px;
    }

    .cell-actions {
      width: 120px;
      text-align: right;
    }

    .row-actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }

    .row-action {
      padding: 6px 10px;
      border: none;
      background: transparent;
      cursor: pointer;
      font-size: 13px;
      color: var(--text-secondary, #555);
      border-radius: var(--radius-sm, 6px);
      transition: all 0.15s ease;
    }

    .row-action:hover {
      background: rgba(0, 0, 0, 0.06);
    }

    .row-action.danger:hover {
      background: rgba(239, 68, 68, 0.1);
      color: #dc2626;
    }

    /* Status badges */
    .badge {
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .badge.active, .badge.success, .badge.healthy {
      background: rgba(34, 197, 94, 0.1);
      color: #16a34a;
    }

    .badge.inactive, .badge.error, .badge.unhealthy {
      background: rgba(239, 68, 68, 0.1);
      color: #dc2626;
    }

    .badge.pending, .badge.warning, .badge.trial {
      background: rgba(251, 191, 36, 0.1);
      color: #d97706;
    }

    .badge.info {
      background: rgba(59, 130, 246, 0.1);
      color: #2563eb;
    }

    /* Pagination */
    .pagination {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      border-top: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
    }

    .pagination-info {
      font-size: 14px;
      color: var(--text-tertiary, #888);
    }

    .pagination-buttons {
      display: flex;
      gap: 8px;
    }

    .page-btn {
      padding: 8px 14px;
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      background: white;
      border-radius: var(--radius-md, 8px);
      font-size: 13px;
      cursor: pointer;
    }

    .page-btn:hover {
      background: rgba(0, 0, 0, 0.02);
    }

    .page-btn.active {
      background: var(--accent, #4f46e5);
      color: white;
      border-color: var(--accent);
    }

    .page-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    /* Loading & Empty states */
    .loading, .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 64px 20px;
      text-align: center;
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

    .empty-icon {
      font-size: 48px;
      margin-bottom: 16px;
    }

    .empty-title {
      font-size: 18px;
      font-weight: 600;
      color: var(--text-primary, #111);
      margin-bottom: 8px;
    }

    .empty-desc {
      font-size: 14px;
      color: var(--text-tertiary, #888);
      margin-bottom: 20px;
    }

    /* Bulk actions bar */
    .bulk-actions {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 12px 16px;
      background: var(--accent, #4f46e5);
      color: white;
      border-radius: var(--radius-lg, 12px) var(--radius-lg, 12px) 0 0;
      margin-bottom: -1px;
    }

    .bulk-count {
      font-weight: 600;
    }

    .bulk-btn {
      padding: 6px 12px;
      background: rgba(255, 255, 255, 0.2);
      border: none;
      border-radius: var(--radius-md, 8px);
      color: white;
      font-size: 13px;
      cursor: pointer;
    }

    .bulk-btn:hover {
      background: rgba(255, 255, 255, 0.3);
    }

    @media (max-width: 768px) {
      .toolbar {
        flex-direction: column;
      }
      
      .search-box {
        width: 100%;
      }

      .table-card {
        overflow-x: auto;
      }

      table {
        min-width: 600px;
      }
    }
  `;

    constructor() {
        super();
        this.title = 'Data Table';
        this.icon = '📋';
        this.endpoint = '';
        this.columns = [];
        this.actions = [];
        this.data = [];
        this.loading = true;
        this.error = '';
        this.searchQuery = '';
        this.currentPage = 1;
        this.totalPages = 1;
        this.selectedItems = [];
        this.sortColumn = '';
        this.sortDirection = 'asc';
    }

    connectedCallback() {
        super.connectedCallback();
        if (this.endpoint) {
            this._loadData();
        }
    }

    async _loadData() {
        this.loading = true;
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                search: this.searchQuery,
                sort: this.sortColumn,
                direction: this.sortDirection,
            });

            const response = await fetch(`${this.endpoint}?${params}`);
            if (!response.ok) throw new Error('Failed to load data');

            const result = await response.json();
            this.data = result.items || result.data || result || [];
            this.totalPages = result.total_pages || Math.ceil((result.total || this.data.length) / 20) || 1;
        } catch (error) {
            this.error = error.message;
        } finally {
            this.loading = false;
        }
    }

    render() {
        return html`
      <div class="header">
        <div class="header-left">
          <h1>${this.icon} ${this.title}</h1>
        </div>
        <div class="header-actions">
          ${this.actions.filter(a => a.position === 'header').map(action => html`
            <button class="btn ${action.primary ? 'btn-primary' : 'btn-secondary'}" 
                    @click=${() => this._handleAction(action)}>
              ${action.icon} ${action.label}
            </button>
          `)}
        </div>
      </div>

      <div class="toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input 
            type="text" 
            placeholder="Search..." 
            .value=${this.searchQuery}
            @input=${e => this._handleSearch(e.target.value)}
          />
        </div>
        <div class="filter-group">
          <button class="filter-btn active">All</button>
          <button class="filter-btn">Active</button>
          <button class="filter-btn">Inactive</button>
        </div>
        <button class="btn btn-secondary" @click=${this._loadData}>🔄 Refresh</button>
      </div>

      ${this.selectedItems.length > 0 ? html`
        <div class="bulk-actions">
          <span class="bulk-count">${this.selectedItems.length} selected</span>
          <button class="bulk-btn">Export</button>
          <button class="bulk-btn">Delete</button>
          <button class="bulk-btn" @click=${() => this.selectedItems = []}>Cancel</button>
        </div>
      ` : ''}

      <div class="table-card">
        ${this.loading ? html`
          <div class="loading">
            <div class="spinner"></div>
          </div>
        ` : this.data.length === 0 ? html`
          <div class="empty-state">
            <div class="empty-icon">📭</div>
            <div class="empty-title">No ${this.title.toLowerCase()} found</div>
            <div class="empty-desc">Try adjusting your search or filters</div>
            ${this.actions.find(a => a.primary) ? html`
              <button class="btn btn-primary" @click=${() => this._handleAction(this.actions.find(a => a.primary))}>
                ${this.actions.find(a => a.primary).icon} ${this.actions.find(a => a.primary).label}
              </button>
            ` : ''}
          </div>
        ` : html`
          <table>
            <thead>
              <tr>
                <th class="cell-checkbox">
                  <input type="checkbox" @change=${this._toggleSelectAll} />
                </th>
                ${this.columns.map(col => html`
                  <th class="${this.sortColumn === col.key ? 'sorted' : ''}" 
                      @click=${() => this._handleSort(col.key)}>
                    ${col.label}
                    <span class="sort-icon">${this.sortColumn === col.key ? (this.sortDirection === 'asc' ? '↑' : '↓') : '↕'}</span>
                  </th>
                `)}
                <th class="cell-actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${this.data.map(row => html`
                <tr>
                  <td class="cell-checkbox">
                    <input type="checkbox" 
                           .checked=${this.selectedItems.includes(row.id)}
                           @change=${() => this._toggleSelect(row.id)} />
                  </td>
                  ${this.columns.map(col => html`
                    <td>${this._renderCell(row, col)}</td>
                  `)}
                  <td class="cell-actions">
                    <div class="row-actions">
                      ${this.actions.filter(a => a.position === 'row').map(action => html`
                        <button class="row-action ${action.danger ? 'danger' : ''}" 
                                @click=${() => this._handleRowAction(action, row)}>
                          ${action.icon}
                        </button>
                      `)}
                    </div>
                  </td>
                </tr>
              `)}
            </tbody>
          </table>

          <div class="pagination">
            <div class="pagination-info">
              Showing ${(this.currentPage - 1) * 20 + 1}-${Math.min(this.currentPage * 20, this.data.length)} of ${this.data.length}
            </div>
            <div class="pagination-buttons">
              <button class="page-btn" ?disabled=${this.currentPage === 1} @click=${() => this._goToPage(this.currentPage - 1)}>← Prev</button>
              ${[...Array(Math.min(5, this.totalPages))].map((_, i) => html`
                <button class="page-btn ${this.currentPage === i + 1 ? 'active' : ''}" 
                        @click=${() => this._goToPage(i + 1)}>
                  ${i + 1}
                </button>
              `)}
              <button class="page-btn" ?disabled=${this.currentPage === this.totalPages} @click=${() => this._goToPage(this.currentPage + 1)}>Next →</button>
            </div>
          </div>
        `}
      </div>
    `;
    }

    _renderCell(row, col) {
        const value = row[col.key];

        // Handle special column types
        switch (col.type) {
            case 'badge':
                const badgeClass = col.badgeMap?.[value] || value?.toLowerCase() || 'info';
                return html`<span class="badge ${badgeClass}">${value}</span>`;

            case 'date':
                return new Date(value).toLocaleDateString();

            case 'datetime':
                return new Date(value).toLocaleString();

            case 'currency':
                return `$${parseFloat(value).toLocaleString()}`;

            case 'link':
                return html`<a href="${col.href?.(row) || '#'}">${value}</a>`;

            default:
                return value ?? '—';
        }
    }

    _handleSearch(query) {
        this.searchQuery = query;
        clearTimeout(this._searchTimeout);
        this._searchTimeout = setTimeout(() => {
            this.currentPage = 1;
            this._loadData();
        }, 300);
    }

    _handleSort(column) {
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }
        this._loadData();
    }

    _toggleSelect(id) {
        if (this.selectedItems.includes(id)) {
            this.selectedItems = this.selectedItems.filter(i => i !== id);
        } else {
            this.selectedItems = [...this.selectedItems, id];
        }
    }

    _toggleSelectAll(e) {
        this.selectedItems = e.target.checked ? this.data.map(d => d.id) : [];
    }

    _goToPage(page) {
        this.currentPage = page;
        this._loadData();
    }

    _handleAction(action) {
        this.dispatchEvent(new CustomEvent('action', { detail: { action } }));
    }

    _handleRowAction(action, row) {
        this.dispatchEvent(new CustomEvent('row-action', { detail: { action, row } }));
    }
}

customElements.define('eog-data-table', EogDataTable);
