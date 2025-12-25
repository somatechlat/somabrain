/**
 * Memory Graph Explorer View
 * Route: /platform/memory/graph
 * 
 * Visual graph exploration of memory nodes and relationships.
 * 
 * VIBE PERSONAS:
 * - UX: Interactive graph visualization
 * - Architect: Relationship mapping
 * - Performance: Lazy loading for large graphs
 */

import { LitElement, html, css } from 'lit';

export class EogMemoryGraph extends LitElement {
    static properties = {
        isLoading: { type: Boolean },
        selectedNode: { type: Object },
        viewMode: { type: String },
    };

    static styles = css`
    :host {
      display: block;
      height: calc(100vh - 200px);
    }

    .container {
      display: flex;
      height: 100%;
      gap: 20px;
    }

    .graph-area {
      flex: 1;
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      position: relative;
      overflow: hidden;
    }

    .graph-canvas {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .graph-placeholder {
      text-align: center;
    }

    .graph-placeholder-icon {
      font-size: 64px;
      margin-bottom: 16px;
    }

    .toolbar {
      position: absolute;
      top: 12px;
      left: 12px;
      display: flex;
      gap: 8px;
    }

    .tool-btn {
      padding: 8px 12px;
      background: rgba(0, 0, 0, 0.5);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 6px;
      color: var(--eog-text, #e4e4e7);
      cursor: pointer;
      font-size: 13px;
      backdrop-filter: blur(10px);
    }

    .tool-btn.active {
      background: var(--eog-primary, #6366f1);
      border-color: var(--eog-primary, #6366f1);
    }

    .sidebar {
      width: 320px;
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      padding: 20px;
      overflow-y: auto;
    }

    .sidebar-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--eog-text-muted, #a1a1aa);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 16px;
    }

    .node-card {
      background: var(--eog-bg, #09090b);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 12px;
    }

    .node-label {
      font-weight: 600;
      color: var(--eog-text, #e4e4e7);
      margin-bottom: 4px;
    }

    .node-type {
      font-size: 12px;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .node-meta {
      font-size: 12px;
      color: var(--eog-text-muted, #a1a1aa);
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid var(--eog-border, #27273a);
    }

    .empty-state {
      text-align: center;
      color: var(--eog-text-muted, #a1a1aa);
      padding: 32px;
    }
  `;

    constructor() {
        super();
        this.isLoading = false;
        this.viewMode = 'force';
        this.selectedNode = null;
    }

    render() {
        return html`
      <div class="container">
        <div class="graph-area">
          <div class="toolbar">
            <button class="tool-btn ${this.viewMode === 'force' ? 'active' : ''}" @click=${() => this.viewMode = 'force'}>Force Layout</button>
            <button class="tool-btn ${this.viewMode === 'radial' ? 'active' : ''}" @click=${() => this.viewMode = 'radial'}>Radial</button>
            <button class="tool-btn ${this.viewMode === 'tree' ? 'active' : ''}" @click=${() => this.viewMode = 'tree'}>Tree</button>
          </div>
          
          <div class="graph-canvas">
            <div class="graph-placeholder">
              <div class="graph-placeholder-icon">🕸️</div>
              <div>Graph visualization requires D3.js or similar library</div>
              <div style="font-size:12px;margin-top:8px;">Connect to a memory service to visualize relationships</div>
            </div>
          </div>
        </div>

        <div class="sidebar">
          <div class="sidebar-title">Selected Node</div>
          
          ${this.selectedNode ? html`
            <div class="node-card">
              <div class="node-label">${this.selectedNode.label}</div>
              <div class="node-type">${this.selectedNode.type} • ${this.selectedNode.id}</div>
              <div class="node-meta">
                <div>Edges: ${this.selectedNode.edges || 0}</div>
                <div>Tenant: ${this.selectedNode.tenant}</div>
              </div>
            </div>
          ` : html`
            <div class="empty-state">
              Click a node in the graph to view details
            </div>
          `}

          <div class="sidebar-title" style="margin-top:24px;">Quick Stats</div>
          <div class="node-card">
            <div style="display:flex;justify-content:space-between;">
              <span style="color:var(--eog-text-muted);">Nodes visible</span>
              <span style="color:var(--eog-text);">0</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:8px;">
              <span style="color:var(--eog-text-muted);">Edges visible</span>
              <span style="color:var(--eog-text);">0</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:8px;">
              <span style="color:var(--eog-text-muted);">Depth</span>
              <span style="color:var(--eog-text);">-</span>
            </div>
          </div>
        </div>
      </div>
    `;
    }
}

customElements.define('eog-memory-graph', EogMemoryGraph);
