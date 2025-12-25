/**
 * Feature Configuration View (Screen 10)
 * Route: /platform/features
 * 
 * Manage system-wide feature flags and configuration parameters.
 * 
 * VIBE PERSONAS:
 * - 🔒 Security: Feature flag access control
 * - 🏛️ Architect: Clean flag patterns
 * - 🎨 UX: Grouped, searchable interface
 * - 🚨 SRE: Feature observability
 */

import { LitElement, html, css } from 'lit';
import { featuresApi } from '../services/api.js';
import '../components/billing/eog-feature-toggle.js';

export class EogFeatureConfig extends LitElement {
  static properties = {
    features: { type: Array },
    isLoading: { type: Boolean },
    searchQuery: { type: String },
    error: { type: String },
  };

  static styles = css`
    :host {
      display: block;
      max-width: 900px;
      margin: 0 auto;
    }

    .header {
      margin-bottom: 32px;
    }

    h1 {
      margin: 0;
      font-size: 24px;
      color: var(--eog-text, #e4e4e7);
    }

    .subtitle {
      color: var(--eog-text-muted, #a1a1aa);
      font-size: 14px;
      margin-top: 4px;
    }

    .card {
      background: var(--eog-surface, #1a1a2e);
      border-radius: 12px;
      border: 1px solid var(--eog-border, #27273a);
      overflow: hidden;
    }

    .group-header {
      background: rgba(255, 255, 255, 0.03);
      padding: 12px 20px;
      border-bottom: 1px solid var(--eog-border, #27273a);
      font-weight: 600;
      color: var(--eog-text, #e4e4e7);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .group-content {
      padding: 16px;
    }

    .search-bar {
      margin-bottom: 24px;
      position: relative;
    }

    .search-input {
      width: 100%;
      padding: 12px 16px;
      padding-left: 40px;
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 8px;
      color: var(--eog-text, #e4e4e7);
      font-size: 14px;
      box-sizing: border-box;
    }

    .search-icon {
      position: absolute;
      left: 12px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--eog-text-muted, #a1a1aa);
    }

    .loading {
      text-align: center;
      padding: 40px;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .error {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      border-radius: 8px;
      padding: 16px;
      color: #ef4444;
      margin-bottom: 24px;
    }
  `;

  constructor() {
    super();
    this.features = [];
    this.isLoading = false;
    this.searchQuery = '';
    this.error = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this._loadFeatures();
  }

  async _loadFeatures() {
    this.isLoading = true;
    this.error = null;
    try {
      const result = await featuresApi.list();
      // Group features by category if backend returns flat list
      const flags = result.flags || result || [];
      this.features = this._groupByCategory(flags);
    } catch (err) {
      console.error('Failed to load features:', err);
      this.error = err.message;
      this.features = [];
    } finally {
      this.isLoading = false;
    }
  }

  _groupByCategory(flags) {
    const groups = {};
    flags.forEach(flag => {
      const category = flag.category || 'General';
      if (!groups[category]) {
        groups[category] = { category, items: [] };
      }
      groups[category].items.push({
        code: flag.key,
        name: flag.name,
        value: flag.enabled,
        type: 'bool',
        description: flag.description,
      });
    });
    return Object.values(groups);
  }

  async _handleFeatureChange(e) {
    const { code, value } = e.detail;
    try {
      await featuresApi.update(code, { enabled: value });
    } catch (err) {
      console.error('Failed to update feature:', err);
      alert(`Failed to update feature: ${err.message}`);
      this._loadFeatures(); // Reload to reset UI
    }
  }

  get filteredFeatures() {
    if (!this.searchQuery) return this.features;
    const q = this.searchQuery.toLowerCase();
    return this.features.map(group => ({
      ...group,
      items: group.items.filter(f =>
        f.name.toLowerCase().includes(q) ||
        f.code.toLowerCase().includes(q)
      )
    })).filter(g => g.items.length > 0);
  }

  render() {
    if (this.isLoading) {
      return html`<div class="loading">Loading features...</div>`;
    }

    return html`
      <div class="view">
        <div class="header">
          <h1>Feature Configuration</h1>
          <div class="subtitle">Manage global feature flags and default limits</div>
        </div>

        ${this.error ? html`<div class="error">${this.error}</div>` : ''}

        <div class="search-bar">
          <span class="search-icon">🔍</span>
          <input 
            class="search-input" 
            type="text" 
            placeholder="Search features..."
            .value=${this.searchQuery}
            @input=${e => this.searchQuery = e.target.value}
          >
        </div>

        ${this.filteredFeatures.length === 0 ? html`
          <div class="loading">No features found</div>
        ` : this.filteredFeatures.map(group => html`
          <div class="card" style="margin-bottom: 24px;">
            <div class="group-header">
              📁 ${group.category}
            </div>
            <div class="group-content">
              ${group.items.map(feature => html`
                <eog-feature-toggle 
                  .feature=${feature}
                  @change=${this._handleFeatureChange}
                ></eog-feature-toggle>
              `)}
            </div>
          </div>
        `)}
      </div>
    `;
  }
}

customElements.define('eog-feature-config', EogFeatureConfig);
