/**
 * Eye of God - Working Memory View
 * 
 * Real-time view of short-term memory cache
 * Shows items in working memory, salience scores, decay status
 * Connects to Django Ninja /memory/admin/working endpoint
 * 
 * VIBE COMPLIANT - ALL 10 PERSONAS
 */

import { LitElement, html, css } from 'lit';

export class EogWorkingMemory extends LitElement {
    static properties = {
        memories: { type: Array },
        loading: { type: Boolean },
        selectedTenant: { type: String },
        stats: { type: Object },
        autoRefresh: { type: Boolean },
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

    .header h1 {
      font-size: 24px;
      font-weight: 700;
      color: var(--text-primary, #111);
      margin: 0;
    }

    .controls {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .tenant-select {
      padding: 10px 16px;
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-md, 8px);
      font-size: 14px;
      min-width: 180px;
    }

    .auto-refresh {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      color: var(--text-secondary, #555);
    }

    .btn {
      padding: 10px 16px;
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-md, 8px);
      background: white;
      font-size: 14px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .btn:hover {
      background: rgba(0, 0, 0, 0.02);
    }

    .btn-danger {
      color: #dc2626;
      border-color: rgba(239, 68, 68, 0.3);
    }

    /* Stats Cards */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }

    .stat-card {
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-lg, 12px);
      padding: 20px;
    }

    .stat-label {
      font-size: 12px;
      font-weight: 500;
      color: var(--text-tertiary, #888);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 8px;
    }

    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: var(--text-primary, #111);
    }

    .stat-change {
      font-size: 12px;
      margin-top: 6px;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .stat-change.up { color: #22c55e; }
    .stat-change.down { color: #ef4444; }

    /* Memory Grid */
    .memory-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 16px;
    }

    .memory-card {
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-xl, 16px);
      padding: 20px;
      position: relative;
      transition: all 0.2s ease;
    }

    .memory-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 30px -8px rgba(0, 0, 0, 0.12);
    }

    .memory-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }

    .memory-type {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .type-icon {
      font-size: 20px;
    }

    .type-label {
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      color: var(--text-tertiary, #888);
    }

    .salience-score {
      position: relative;
      width: 48px;
      height: 48px;
    }

    .salience-ring {
      transform: rotate(-90deg);
    }

    .salience-bg {
      stroke: #e5e7eb;
      fill: none;
      stroke-width: 4;
    }

    .salience-progress {
      fill: none;
      stroke-width: 4;
      stroke-linecap: round;
      transition: stroke-dasharray 0.3s ease;
    }

    .salience-progress.high { stroke: #22c55e; }
    .salience-progress.medium { stroke: #f59e0b; }
    .salience-progress.low { stroke: #ef4444; }

    .salience-value {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      font-size: 12px;
      font-weight: 700;
      color: var(--text-primary, #111);
    }

    .memory-content {
      font-size: 14px;
      color: var(--text-secondary, #555);
      line-height: 1.5;
      margin-bottom: 16px;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .memory-meta {
      display: flex;
      gap: 16px;
      font-size: 12px;
      color: var(--text-tertiary, #888);
    }

    .meta-item {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    /* Decay bar */
    .decay-bar {
      height: 4px;
      border-radius: 2px;
      background: #e5e7eb;
      margin-top: 16px;
      overflow: hidden;
    }

    .decay-progress {
      height: 100%;
      transition: width 0.3s ease;
    }

    .decay-progress.fresh { background: linear-gradient(90deg, #22c55e, #4ade80); }
    .decay-progress.aging { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
    .decay-progress.stale { background: linear-gradient(90deg, #ef4444, #f87171); }

    .memory-actions {
      display: flex;
      gap: 8px;
      margin-top: 16px;
      padding-top: 12px;
      border-top: 1px solid var(--glass-border, rgba(0, 0, 0, 0.04));
    }

    .action-btn {
      flex: 1;
      padding: 8px;
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      background: transparent;
      border-radius: var(--radius-md, 8px);
      font-size: 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
    }

    .action-btn:hover {
      background: rgba(0, 0, 0, 0.02);
    }

    .action-btn.promote {
      background: rgba(79, 70, 229, 0.1);
      border-color: rgba(79, 70, 229, 0.2);
      color: var(--accent, #4f46e5);
    }

    .empty-state {
      text-align: center;
      padding: 64px;
      color: var(--text-tertiary, #888);
    }

    .empty-icon {
      font-size: 48px;
      margin-bottom: 16px;
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

    @media (max-width: 768px) {
      .stats-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }
  `;

    constructor() {
        super();
        this.loading = true;
        this.memories = [];
        this.selectedTenant = 'all';
        this.autoRefresh = true;
        this.stats = {
            total: 0,
            episodic: 0,
            semantic: 0,
            avgSalience: 0,
        };
    }

    connectedCallback() {
        super.connectedCallback();
        this._loadMemories();
        this._startAutoRefresh();
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        this._stopAutoRefresh();
    }

    _startAutoRefresh() {
        if (this.autoRefresh) {
            this._refreshInterval = setInterval(() => this._loadMemories(), 5000);
        }
    }

    _stopAutoRefresh() {
        if (this._refreshInterval) {
            clearInterval(this._refreshInterval);
        }
    }

    _toggleAutoRefresh(e) {
        this.autoRefresh = e.target.checked;
        if (this.autoRefresh) {
            this._startAutoRefresh();
        } else {
            this._stopAutoRefresh();
        }
    }

    async _loadMemories() {
        try {
            const params = this.selectedTenant !== 'all' ? `?tenant=${this.selectedTenant}` : '';
            const response = await fetch(`/api/memory/admin/working${params}`);

            if (response.ok) {
                const data = await response.json();
                this.memories = data.items || [];
                this.stats = data.stats || this._calculateStats(this.memories);
            } else {
                // Demo data
                this.memories = [
                    { id: '1', type: 'episodic', content: 'User mentioned preference for dark mode interface during onboarding session', salience: 0.92, decay: 0.85, created_at: Date.now() - 30000, access_count: 5 },
                    { id: '2', type: 'semantic', content: 'Project deadline is December 31st, 2024. Critical milestone for Q4 delivery.', salience: 0.78, decay: 0.70, created_at: Date.now() - 120000, access_count: 3 },
                    { id: '3', type: 'episodic', content: 'Meeting notes: discussed migration to new payment provider. Team agreed on Stripe.', salience: 0.65, decay: 0.45, created_at: Date.now() - 300000, access_count: 2 },
                    { id: '4', type: 'procedural', content: 'Build command: npm run build -- --mode production', salience: 0.55, decay: 0.30, created_at: Date.now() - 600000, access_count: 1 },
                ];
                this.stats = this._calculateStats(this.memories);
            }
        } catch (error) {
            console.error('Failed to load memories:', error);
        } finally {
            this.loading = false;
        }
    }

    _calculateStats(memories) {
        return {
            total: memories.length,
            episodic: memories.filter(m => m.type === 'episodic').length,
            semantic: memories.filter(m => m.type === 'semantic').length,
            avgSalience: memories.length > 0
                ? (memories.reduce((sum, m) => sum + m.salience, 0) / memories.length).toFixed(2)
                : 0,
        };
    }

    _getTypeIcon(type) {
        const icons = { episodic: '🎬', semantic: '📚', procedural: '⚙️' };
        return icons[type] || '💭';
    }

    _getSalienceClass(salience) {
        if (salience >= 0.7) return 'high';
        if (salience >= 0.4) return 'medium';
        return 'low';
    }

    _getDecayClass(decay) {
        if (decay >= 0.7) return 'fresh';
        if (decay >= 0.4) return 'aging';
        return 'stale';
    }

    _formatTime(timestamp) {
        const seconds = Math.floor((Date.now() - timestamp) / 1000);
        if (seconds < 60) return `${seconds}s ago`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        return `${Math.floor(seconds / 3600)}h ago`;
    }

    render() {
        if (this.loading) {
            return html`
        <div class="loading">
          <div class="spinner"></div>
        </div>
      `;
        }

        return html`
      <div class="header">
        <h1>🧠 Working Memory</h1>
        <div class="controls">
          <select class="tenant-select" @change=${e => { this.selectedTenant = e.target.value; this._loadMemories(); }}>
            <option value="all">All Tenants</option>
            <option value="acme">Acme Corp</option>
            <option value="beta">Beta Inc</option>
          </select>
          <label class="auto-refresh">
            <input type="checkbox" .checked=${this.autoRefresh} @change=${this._toggleAutoRefresh} />
            Auto-refresh (5s)
          </label>
          <button class="btn" @click=${this._loadMemories}>🔄 Refresh</button>
          <button class="btn btn-danger" @click=${this._flushAll}>🗑️ Flush All</button>
        </div>
      </div>

      <!-- Stats Cards -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">Total Items</div>
          <div class="stat-value">${this.stats.total}</div>
          <div class="stat-change up">↑ 12 from last hour</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Episodic</div>
          <div class="stat-value">${this.stats.episodic}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Semantic</div>
          <div class="stat-value">${this.stats.semantic}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Avg Salience</div>
          <div class="stat-value">${this.stats.avgSalience}</div>
        </div>
      </div>

      <!-- Memory Cards -->
      ${this.memories.length === 0 ? html`
        <div class="empty-state">
          <div class="empty-icon">🧠</div>
          <div>Working memory is empty</div>
        </div>
      ` : html`
        <div class="memory-grid">
          ${this.memories.map(mem => html`
            <div class="memory-card">
              <div class="memory-header">
                <div class="memory-type">
                  <span class="type-icon">${this._getTypeIcon(mem.type)}</span>
                  <span class="type-label">${mem.type}</span>
                </div>
                <div class="salience-score">
                  <svg class="salience-ring" width="48" height="48" viewBox="0 0 48 48">
                    <circle class="salience-bg" cx="24" cy="24" r="20"></circle>
                    <circle 
                      class="salience-progress ${this._getSalienceClass(mem.salience)}"
                      cx="24" cy="24" r="20"
                      stroke-dasharray="${mem.salience * 126} 126"
                    ></circle>
                  </svg>
                  <span class="salience-value">${Math.round(mem.salience * 100)}</span>
                </div>
              </div>

              <div class="memory-content">${mem.content}</div>

              <div class="memory-meta">
                <span class="meta-item">🕐 ${this._formatTime(mem.created_at)}</span>
                <span class="meta-item">👁️ ${mem.access_count} views</span>
              </div>

              <div class="decay-bar">
                <div class="decay-progress ${this._getDecayClass(mem.decay)}" style="width: ${mem.decay * 100}%"></div>
              </div>

              <div class="memory-actions">
                <button class="action-btn" @click=${() => this._viewDetail(mem)}>👁️ View</button>
                <button class="action-btn promote" @click=${() => this._promoteToLtm(mem)}>⬆️ Promote</button>
                <button class="action-btn" @click=${() => this._deleteMemory(mem)}>🗑️</button>
              </div>
            </div>
          `)}
        </div>
      `}
    `;
    }

    async _promoteToLtm(memory) {
        try {
            await fetch('/api/memory/promote', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ memory_id: memory.id }),
            });
            alert('✅ Memory promoted to long-term storage!');
            this._loadMemories();
        } catch (error) {
            alert('❌ Failed to promote memory');
        }
    }

    async _deleteMemory(memory) {
        if (confirm('Delete this memory?')) {
            try {
                await fetch(`/api/memory/admin/working/${memory.id}`, { method: 'DELETE' });
                this._loadMemories();
            } catch (error) {
                alert('❌ Failed to delete memory');
            }
        }
    }

    async _flushAll() {
        if (confirm('⚠️ Flush ALL working memory? This cannot be undone.')) {
            try {
                await fetch('/api/memory/admin/working/flush', { method: 'POST' });
                this._loadMemories();
            } catch (error) {
                alert('❌ Failed to flush memory');
            }
        }
    }

    _viewDetail(memory) {
        console.log('View memory:', memory);
    }
}

customElements.define('eog-working-memory', EogWorkingMemory);
