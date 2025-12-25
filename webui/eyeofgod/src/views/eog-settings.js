/**
 * Platform Settings View (System Screen)
 * Route: /platform/settings
 * 
 * Global platform configuration management.
 * 
 * VIBE PERSONAS:
 * - Security: Sensitive settings protection
 * - Architect: Centralized configuration
 * - UX: Grouped settings with save confirmation
 */

import { LitElement, html, css } from 'lit';

export class EogSettings extends LitElement {
    static properties = {
        settings: { type: Object },
        isLoading: { type: Boolean },
        isSaving: { type: Boolean },
    };

    static styles = css`
    :host {
      display: block;
      max-width: 800px;
      margin: 0 auto;
    }

    h1 {
      margin: 0 0 24px 0;
      font-size: 24px;
      color: var(--eog-text, #e4e4e7);
    }

    .card {
      background: var(--eog-surface, #1a1a2e);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
    }

    .card-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--eog-text, #e4e4e7);
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .form-group {
      margin-bottom: 20px;
    }

    label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      color: var(--eog-text-secondary, #a1a1aa);
      margin-bottom: 8px;
    }

    input, select, textarea {
      width: 100%;
      padding: 10px 12px;
      background: var(--eog-bg, #09090b);
      border: 1px solid var(--eog-border, #27273a);
      border-radius: 8px;
      color: var(--eog-text, #e4e4e7);
      font-size: 14px;
      box-sizing: border-box;
    }

    input:focus, select:focus, textarea:focus {
      outline: none;
      border-color: var(--eog-primary, #6366f1);
    }

    .toggle-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid var(--eog-border, #27273a);
    }

    .toggle-row:last-child {
      border-bottom: none;
    }

    .toggle-info {
      flex: 1;
    }

    .toggle-label {
      font-size: 14px;
      color: var(--eog-text, #e4e4e7);
    }

    .toggle-desc {
      font-size: 12px;
      color: var(--eog-text-muted, #a1a1aa);
    }

    .switch {
      position: relative;
      width: 44px;
      height: 24px;
    }

    .switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }

    .slider {
      position: absolute;
      cursor: pointer;
      inset: 0;
      background: var(--eog-border, #27273a);
      border-radius: 24px;
      transition: 0.2s;
    }

    .slider:before {
      position: absolute;
      content: "";
      height: 18px;
      width: 18px;
      left: 3px;
      bottom: 3px;
      background: white;
      border-radius: 50%;
      transition: 0.2s;
    }

    input:checked + .slider {
      background: var(--eog-success, #22c55e);
    }

    input:checked + .slider:before {
      transform: translateX(20px);
    }

    .actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      padding-top: 24px;
      border-top: 1px solid var(--eog-border, #27273a);
    }

    .btn {
      padding: 10px 24px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      border: none;
    }

    .btn-secondary {
      background: transparent;
      border: 1px solid var(--eog-border, #27273a);
      color: var(--eog-text, #e4e4e7);
    }

    .btn-primary {
      background: var(--eog-primary, #6366f1);
      color: white;
    }
  `;

    constructor() {
        super();
        this.settings = {
            platformName: 'SomaBrain',
            supportEmail: 'support@somabrain.ai',
            maintenanceMode: false,
            allowSignups: true,
            requireEmailVerification: true,
            sessionTimeoutMinutes: 60,
            maxLoginAttempts: 5,
            auditRetentionDays: 90,
        };
        this.isLoading = false;
        this.isSaving = false;
    }

    _updateSetting(field, value) {
        this.settings = { ...this.settings, [field]: value };
    }

    async _handleSave() {
        this.isSaving = true;
        try {
            // TODO: Implement API save
            console.log('Saving settings:', this.settings);
            await new Promise(r => setTimeout(r, 500)); // Simulate
            alert('Settings saved successfully');
        } catch (err) {
            alert('Failed to save settings');
        } finally {
            this.isSaving = false;
        }
    }

    render() {
        return html`
      <h1>Platform Settings</h1>

      <div class="card">
        <div class="card-title">🏢 General</div>
        <div class="form-group">
          <label>Platform Name</label>
          <input type="text" .value=${this.settings.platformName} @input=${e => this._updateSetting('platformName', e.target.value)}>
        </div>
        <div class="form-group">
          <label>Support Email</label>
          <input type="email" .value=${this.settings.supportEmail} @input=${e => this._updateSetting('supportEmail', e.target.value)}>
        </div>
      </div>

      <div class="card">
        <div class="card-title">🔐 Security</div>
        <div class="form-group">
          <label>Session Timeout (minutes)</label>
          <input type="number" .value=${this.settings.sessionTimeoutMinutes} @input=${e => this._updateSetting('sessionTimeoutMinutes', parseInt(e.target.value))}>
        </div>
        <div class="form-group">
          <label>Max Login Attempts</label>
          <input type="number" .value=${this.settings.maxLoginAttempts} @input=${e => this._updateSetting('maxLoginAttempts', parseInt(e.target.value))}>
        </div>
      </div>

      <div class="card">
        <div class="card-title">⚙️ Features</div>
        
        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-label">Maintenance Mode</div>
            <div class="toggle-desc">Disable access for non-admins</div>
          </div>
          <label class="switch">
            <input type="checkbox" ?checked=${this.settings.maintenanceMode} @change=${e => this._updateSetting('maintenanceMode', e.target.checked)}>
            <span class="slider"></span>
          </label>
        </div>

        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-label">Allow New Signups</div>
            <div class="toggle-desc">Enable self-service registration</div>
          </div>
          <label class="switch">
            <input type="checkbox" ?checked=${this.settings.allowSignups} @change=${e => this._updateSetting('allowSignups', e.target.checked)}>
            <span class="slider"></span>
          </label>
        </div>

        <div class="toggle-row">
          <div class="toggle-info">
            <div class="toggle-label">Require Email Verification</div>
            <div class="toggle-desc">Users must verify email before access</div>
          </div>
          <label class="switch">
            <input type="checkbox" ?checked=${this.settings.requireEmailVerification} @change=${e => this._updateSetting('requireEmailVerification', e.target.checked)}>
            <span class="slider"></span>
          </label>
        </div>
      </div>

      <div class="card">
        <div class="card-title">📊 Data Retention</div>
        <div class="form-group">
          <label>Audit Log Retention (days)</label>
          <input type="number" .value=${this.settings.auditRetentionDays} @input=${e => this._updateSetting('auditRetentionDays', parseInt(e.target.value))}>
        </div>
      </div>

      <div class="actions">
        <button class="btn btn-secondary">Cancel</button>
        <button class="btn btn-primary" ?disabled=${this.isSaving} @click=${this._handleSave}>
          ${this.isSaving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    `;
    }
}

customElements.define('eog-settings', EogSettings);
