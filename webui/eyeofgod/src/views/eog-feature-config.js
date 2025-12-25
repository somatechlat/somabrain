/**
 * Feature Configuration View (Screen 10)
 * Route: /platform/features
 * 
 * Manage system-wide feature flags and configuration parameters.
 */

import { LitElement, html, css } from 'lit';
import { tiersApi } from '../services/api.js'; // Assuming features might be part of tiers or a separate API
import '../components/billing/eog-feature-toggle.js';

export class EogFeatureConfig extends LitElement {
    static properties = {
        features: { type: Array },
        isLoading: { type: Boolean },
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
  `;

    constructor() {
        super();
        // MOCK DATA for now until API confirmed
        this.features = [
            {
                category: 'AI Models',
                items: [
                    { code: 'model_gpt4', name: 'GPT-4 Access', value: true, type: 'bool' },
                    { code: 'model_claude', name: 'Claude 3 Access', value: true, type: 'bool' },
                    { code: 'max_tokens', name: 'Max Context Window', value: 128000, type: 'int' },
                ]
            },
            {
                category: 'Storage',
                items: [
                    { code: 'vector_db_enabled', name: 'Vector Database', value: true, type: 'bool' },
                    { code: 'storage_quota_gb', name: 'Storage Quota (GB)', value: 10, type: 'int' },
                ]
            },
            {
                category: 'Integrations',
                items: [
                    { code: 'github_sync', name: 'GitHub Integration', value: true, type: 'bool' },
                    { code: 'slack_bot', name: 'Slack Bot', value: false, type: 'bool' },
                ]
            }
        ];
        this.isLoading = false;
    }

    render() {
        return html`
      <div class="view">
        <div class="header">
          <h1>Feature Configuration</h1>
          <div class="subtitle">Manage global feature flags and default limits</div>
        </div>

        <div class="search-bar">
          <span class="search-icon">🔍</span>
          <input class="search-input" type="text" placeholder="Search features...">
        </div>

        ${this.features.map(group => html`
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

    _handleFeatureChange(e) {
        console.log('Feature changed:', e.detail);
        // TODO: Implement API save
    }
}

customElements.define('eog-feature-config', EogFeatureConfig);
