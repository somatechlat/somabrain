/**
 * Eye of God - Reusable Settings Panel Component
 * 
 * Generic settings form that handles ALL settings screens:
 * - Platform settings, Tenant settings, Service config, Feature flags, etc.
 * 
 * ABSTRACTION PATTERN: One component, many settings screens
 * 
 * VIBE COMPLIANT - ALL 10 PERSONAS
 */

import { LitElement, html, css } from 'lit';

export class EogSettingsPanel extends LitElement {
    static properties = {
        // Configuration
        title: { type: String },
        icon: { type: String },
        endpoint: { type: String },
        sections: { type: Array },

        // State
        settings: { type: Object },
        original: { type: Object },
        loading: { type: Boolean },
        saving: { type: Boolean },
        hasChanges: { type: Boolean },
        error: { type: String },
        success: { type: String },
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

    .header h1 {
      font-size: 24px;
      font-weight: 700;
      color: var(--text-primary, #111);
      margin: 0;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .header-actions {
      display: flex;
      gap: 12px;
    }

    .btn {
      padding: 12px 20px;
      border-radius: var(--radius-lg, 12px);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      transition: all 0.15s ease;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .btn-primary {
      background: var(--accent, #4f46e5);
      color: white;
      border-color: var(--accent);
    }

    .btn-primary:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 8px 20px -4px rgba(79, 70, 229, 0.3);
    }

    .btn-secondary {
      background: white;
    }

    .btn-secondary:hover {
      background: rgba(0, 0, 0, 0.02);
    }

    .settings-grid {
      display: grid;
      gap: 24px;
    }

    .section-card {
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-xl, 16px);
      overflow: hidden;
    }

    .section-header {
      padding: 20px 24px;
      border-bottom: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .section-icon {
      font-size: 24px;
    }

    .section-info {
      flex: 1;
    }

    .section-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary, #111);
      margin: 0 0 4px 0;
    }

    .section-desc {
      font-size: 13px;
      color: var(--text-tertiary, #888);
      margin: 0;
    }

    .section-body {
      padding: 24px;
    }

    .field-group {
      margin-bottom: 24px;
    }

    .field-group:last-child {
      margin-bottom: 0;
    }

    .field-row {
      display: flex;
      align-items: flex-start;
      gap: 24px;
    }

    .field-label-area {
      flex: 0 0 200px;
    }

    .field-input-area {
      flex: 1;
    }

    .field-label {
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary, #111);
      margin-bottom: 4px;
    }

    .field-desc {
      font-size: 12px;
      color: var(--text-tertiary, #888);
    }

    .field-hint {
      font-size: 12px;
      color: var(--text-tertiary, #888);
      margin-top: 6px;
    }

    /* Input styles */
    input[type="text"],
    input[type="email"],
    input[type="url"],
    input[type="number"],
    input[type="password"],
    textarea,
    select {
      width: 100%;
      padding: 12px 14px;
      border: 1px solid #e5e7eb;
      border-radius: var(--radius-md, 8px);
      font-size: 14px;
      transition: all 0.15s ease;
      box-sizing: border-box;
    }

    input:focus,
    textarea:focus,
    select:focus {
      outline: none;
      border-color: var(--accent, #4f46e5);
      box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1);
    }

    textarea {
      min-height: 100px;
      resize: vertical;
    }

    /* Toggle switch */
    .toggle {
      position: relative;
      display: inline-block;
      width: 48px;
      height: 28px;
    }

    .toggle input {
      opacity: 0;
      width: 0;
      height: 0;
    }

    .toggle-slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: #e5e7eb;
      transition: 0.2s;
      border-radius: 28px;
    }

    .toggle-slider:before {
      position: absolute;
      content: "";
      height: 22px;
      width: 22px;
      left: 3px;
      bottom: 3px;
      background-color: white;
      transition: 0.2s;
      border-radius: 50%;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .toggle input:checked + .toggle-slider {
      background-color: var(--accent, #4f46e5);
    }

    .toggle input:checked + .toggle-slider:before {
      transform: translateX(20px);
    }

    /* Range slider */
    input[type="range"] {
      width: 100%;
      height: 8px;
      border-radius: 4px;
      background: #e5e7eb;
      outline: none;
      -webkit-appearance: none;
    }

    input[type="range"]::-webkit-slider-thumb {
      -webkit-appearance: none;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: var(--accent, #4f46e5);
      cursor: pointer;
      box-shadow: 0 2px 6px rgba(79, 70, 229, 0.3);
    }

    .range-value {
      display: inline-block;
      min-width: 50px;
      text-align: center;
      font-size: 14px;
      font-weight: 600;
      color: var(--accent, #4f46e5);
    }

    /* Color picker */
    input[type="color"] {
      width: 48px;
      height: 48px;
      padding: 0;
      border: 2px solid #e5e7eb;
      border-radius: var(--radius-md, 8px);
      cursor: pointer;
    }

    /* Tags input */
    .tags-input {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 8px;
      border: 1px solid #e5e7eb;
      border-radius: var(--radius-md, 8px);
      min-height: 44px;
    }

    .tag {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      background: rgba(79, 70, 229, 0.1);
      color: var(--accent, #4f46e5);
      border-radius: 20px;
      font-size: 13px;
    }

    .tag-remove {
      cursor: pointer;
      opacity: 0.7;
    }

    .tag-remove:hover {
      opacity: 1;
    }

    .tags-input input {
      flex: 1;
      min-width: 100px;
      border: none;
      padding: 4px;
      font-size: 14px;
    }

    .tags-input input:focus {
      outline: none;
      box-shadow: none;
    }

    /* Runtime indicator */
    .runtime-badge {
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .runtime-badge.dynamic {
      background: rgba(34, 197, 94, 0.1);
      color: #16a34a;
    }

    .runtime-badge.static {
      background: rgba(239, 68, 68, 0.1);
      color: #dc2626;
    }

    /* Alerts */
    .alert {
      padding: 14px 18px;
      border-radius: var(--radius-lg, 12px);
      font-size: 14px;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .alert-success {
      background: rgba(34, 197, 94, 0.1);
      color: #16a34a;
      border: 1px solid rgba(34, 197, 94, 0.2);
    }

    .alert-error {
      background: rgba(239, 68, 68, 0.1);
      color: #dc2626;
      border: 1px solid rgba(239, 68, 68, 0.2);
    }

    .alert-warning {
      background: rgba(251, 191, 36, 0.1);
      color: #d97706;
      border: 1px solid rgba(251, 191, 36, 0.2);
    }

    /* Loading */
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

    /* Unsaved changes bar */
    .unsaved-bar {
      position: fixed;
      bottom: 0;
      left: 280px;
      right: 0;
      padding: 16px 24px;
      background: var(--accent, #4f46e5);
      color: white;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 100;
      box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.15);
    }

    .unsaved-bar .btn {
      background: rgba(255, 255, 255, 0.2);
      border-color: transparent;
      color: white;
    }

    .unsaved-bar .btn-primary {
      background: white;
      color: var(--accent, #4f46e5);
    }

    @media (max-width: 900px) {
      .field-row {
        flex-direction: column;
        gap: 8px;
      }

      .field-label-area {
        flex: none;
      }

      .unsaved-bar {
        left: 0;
      }
    }
  `;

    constructor() {
        super();
        this.title = 'Settings';
        this.icon = '⚙️';
        this.endpoint = '';
        this.sections = [];
        this.settings = {};
        this.original = {};
        this.loading = true;
        this.saving = false;
        this.hasChanges = false;
        this.error = '';
        this.success = '';
    }

    connectedCallback() {
        super.connectedCallback();
        if (this.endpoint) {
            this._loadSettings();
        }
    }

    async _loadSettings() {
        this.loading = true;
        try {
            const response = await fetch(this.endpoint);
            if (!response.ok) throw new Error('Failed to load settings');

            const data = await response.json();
            this.settings = { ...data };
            this.original = { ...data };
        } catch (error) {
            this.error = error.message;
        } finally {
            this.loading = false;
        }
    }

    _updateSetting(key, value) {
        this.settings = { ...this.settings, [key]: value };
        this.hasChanges = JSON.stringify(this.settings) !== JSON.stringify(this.original);
        this.requestUpdate();
    }

    async _saveSettings() {
        this.saving = true;
        this.error = '';
        this.success = '';

        try {
            const response = await fetch(this.endpoint, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.settings),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to save settings');
            }

            this.original = { ...this.settings };
            this.hasChanges = false;
            this.success = 'Settings saved successfully!';

            setTimeout(() => this.success = '', 3000);
        } catch (error) {
            this.error = error.message;
        } finally {
            this.saving = false;
        }
    }

    _resetSettings() {
        this.settings = { ...this.original };
        this.hasChanges = false;
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
        <h1>${this.icon} ${this.title}</h1>
        <div class="header-actions">
          <button class="btn btn-secondary" @click=${this._resetSettings} ?disabled=${!this.hasChanges}>
            ↩️ Reset
          </button>
          <button class="btn btn-primary" @click=${this._saveSettings} ?disabled=${!this.hasChanges || this.saving}>
            ${this.saving ? '💾 Saving...' : '💾 Save Changes'}
          </button>
        </div>
      </div>

      ${this.success ? html`<div class="alert alert-success">✅ ${this.success}</div>` : ''}
      ${this.error ? html`<div class="alert alert-error">❌ ${this.error}</div>` : ''}

      <div class="settings-grid">
        ${this.sections.map(section => this._renderSection(section))}
      </div>

      ${this.hasChanges ? html`
        <div class="unsaved-bar">
          <span>⚠️ You have unsaved changes</span>
          <div style="display: flex; gap: 12px;">
            <button class="btn" @click=${this._resetSettings}>Discard</button>
            <button class="btn btn-primary" @click=${this._saveSettings}>Save Changes</button>
          </div>
        </div>
      ` : ''}
    `;
    }

    _renderSection(section) {
        return html`
      <div class="section-card">
        <div class="section-header">
          <span class="section-icon">${section.icon}</span>
          <div class="section-info">
            <h3 class="section-title">${section.title}</h3>
            ${section.description ? html`<p class="section-desc">${section.description}</p>` : ''}
          </div>
        </div>
        <div class="section-body">
          ${section.fields.map(field => this._renderField(field))}
        </div>
      </div>
    `;
    }

    _renderField(field) {
        const value = this.settings[field.key] ?? field.default;

        return html`
      <div class="field-group">
        <div class="field-row">
          <div class="field-label-area">
            <div class="field-label">
              ${field.label}
              ${field.runtime ? html`<span class="runtime-badge ${field.runtime}">⚡ ${field.runtime}</span>` : ''}
            </div>
            ${field.description ? html`<div class="field-desc">${field.description}</div>` : ''}
          </div>
          <div class="field-input-area">
            ${this._renderInput(field, value)}
            ${field.hint ? html`<div class="field-hint">${field.hint}</div>` : ''}
          </div>
        </div>
      </div>
    `;
    }

    _renderInput(field, value) {
        switch (field.type) {
            case 'toggle':
                return html`
          <label class="toggle">
            <input type="checkbox" 
                   .checked=${value}
                   @change=${e => this._updateSetting(field.key, e.target.checked)} />
            <span class="toggle-slider"></span>
          </label>
        `;

            case 'select':
                return html`
          <select @change=${e => this._updateSetting(field.key, e.target.value)}>
            ${field.options.map(opt => html`
              <option value="${opt.value}" ?selected=${value === opt.value}>${opt.label}</option>
            `)}
          </select>
        `;

            case 'range':
                return html`
          <div style="display: flex; align-items: center; gap: 16px;">
            <input type="range" 
                   min="${field.min || 0}" 
                   max="${field.max || 100}" 
                   step="${field.step || 1}"
                   .value=${value}
                   @input=${e => this._updateSetting(field.key, parseFloat(e.target.value))} />
            <span class="range-value">${value}${field.unit || ''}</span>
          </div>
        `;

            case 'number':
                return html`
          <input type="number" 
                 min="${field.min}" 
                 max="${field.max}"
                 .value=${value}
                 @input=${e => this._updateSetting(field.key, parseFloat(e.target.value) || 0)} />
        `;

            case 'textarea':
                return html`
          <textarea 
            .value=${value || ''}
            @input=${e => this._updateSetting(field.key, e.target.value)}
            placeholder="${field.placeholder || ''}"
          ></textarea>
        `;

            case 'color':
                return html`
          <input type="color" 
                 .value=${value || '#4f46e5'}
                 @input=${e => this._updateSetting(field.key, e.target.value)} />
        `;

            case 'password':
                return html`
          <input type="password" 
                 .value=${value || ''}
                 @input=${e => this._updateSetting(field.key, e.target.value)}
                 placeholder="${field.placeholder || '••••••••'}" />
        `;

            default:
                return html`
          <input type="${field.type || 'text'}" 
                 .value=${value || ''}
                 @input=${e => this._updateSetting(field.key, e.target.value)}
                 placeholder="${field.placeholder || ''}" />
        `;
        }
    }
}

customElements.define('eog-settings-panel', EogSettingsPanel);
