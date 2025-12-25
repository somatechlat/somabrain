/**
 * Memory Browser View
 * Route: /platform/memory/browse
 * 
 * Browse and search memory nodes across tenants.
 * 
 * VIBE PERSONAS:
 * - DBA: Efficient pagination, search
 * - Security: Tenant isolation visibility
 * - UX: Filterable, expandable node view
 */

import { LitElement, html, css } from 'lit';

export class EogMemoryBrowse extends LitElement {
    static properties = {
        nodes: { type: Array },
        isLoading: { type: Boolean },
        searchQuery: { type: String },
        selectedTenant: { type: String },
        expandedNode: { type: String },
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
      flex: 1;
      padding: 10px 14px;
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 8px;
      color: var(--eog-text, #e4e4e7);
      font-size: 14px;
    }

    select.filter-input {
      width: 200px;
      flex: none;
    }

    .nodes-table {
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
      color: var(--eog-text-muted, #a1a1aa);
      background: rgba(0, 0, 0, 0.2);
      border-bottom: 1px solid var(--eog-border, #27273a);
    }

    tbody tr {
      border-bottom: 1px solid var(--eog-border, #27273a);
      cursor: pointer;
    }

    tbody tr:hover {
      background: rgba(255, 255, 255, 0.02);
    }

    td {
      padding: 14px 16px;
      font-size: 14px;
      color: var(--eog-text, #e4e4e7);
    }

    .node-id {
      font-family: monospace;
      font-size: 12px;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .node-type {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      background: rgba(99, 102, 241, 0.2);
      color: #6366f1;
    }

    .node-expanded {
      background: rgba(0, 0, 0, 0.2);
      padding: 16px;
      border-top: 1px solid var(--eog-border, #27273a);
    }

    .node-expanded pre {
      margin: 0;
      font-size: 12px;
      color: var(--eog-text-muted, #a1a1aa);
      white-space: pre-wrap;
    }
  `;

    constructor() {
        super();
        // Mock data
        this.nodes = [
            { id: 'n_a1b2c3', type: 'concept', label: 'Machine Learning', tenant: 'acme', created_at: '2024-12-20', edges: 45 },
            { id: 'n_d4e5f6', type: 'entity', label: 'TensorFlow', tenant: 'acme', created_at: '2024-12-19', edges: 32 },
            { id: 'n_g7h8i9', type: 'action', label: 'Train Model', tenant: 'techstart', created_at: '2024-12-18', edges: 12 },
            { id: 'n_j0k1l2', type: 'concept', label: 'Neural Networks', tenant: 'dataflow', created_at: '2024-12-17', edges: 67 },
        ];
        this.isLoading = false;
        this.searchQuery = '';
        this.selectedTenant = '';
        this.expandedNode = null;
    }

    get filteredNodes() {
        let nodes = this.nodes;
        if (this.searchQuery) {
            const q = this.searchQuery.toLowerCase();
            nodes = nodes.filter(n => n.label.toLowerCase().includes(q) || n.id.includes(q));
        }
        if (this.selectedTenant) {
            nodes = nodes.filter(n => n.tenant === this.selectedTenant);
        }
        return nodes;
    }

    _toggleExpand(nodeId) {
        this.expandedNode = this.expandedNode === nodeId ? null : nodeId;
    }

    render() {
        return html`
      <div class="header">
        <h1>Memory Browser</h1>
      </div>

      <div class="filters">
        <input 
          class="filter-input" 
          type="text" 
          placeholder="Search nodes..." 
          .value=${this.searchQuery}
          @input=${e => this.searchQuery = e.target.value}
        >
        <select class="filter-input" .value=${this.selectedTenant} @change=${e => this.selectedTenant = e.target.value}>
          <option value="">All Tenants</option>
          <option value="acme">Acme Corp</option>
          <option value="techstart">TechStart</option>
          <option value="dataflow">DataFlow</option>
        </select>
      </div>

      <div class="nodes-table">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Label</th>
              <th>Type</th>
              <th>Tenant</th>
              <th>Edges</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            ${this.filteredNodes.map(node => html`
              <tr @click=${() => this._toggleExpand(node.id)}>
                <td class="node-id">${node.id}</td>
                <td>${node.label}</td>
                <td><span class="node-type">${node.type}</span></td>
                <td>${node.tenant}</td>
                <td>${node.edges}</td>
                <td>${node.created_at}</td>
              </tr>
              ${this.expandedNode === node.id ? html`
                <tr>
                  <td colspan="6" class="node-expanded">
                    <pre>${JSON.stringify({ ...node, embedding: '[256 floats...]', metadata: { source: 'api', version: '1.0' } }, null, 2)}</pre>
                  </td>
                </tr>
              ` : ''}
            `)}
          </tbody>
        </table>
      </div>
    `;
    }
}

customElements.define('eog-memory-browse', EogMemoryBrowse);
