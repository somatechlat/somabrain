/**
 * Feature Toggle Component
 * 
 * Granular control for a feature (boolean or value).
 */

import { LitElement, html, css } from 'lit';

export class EogFeatureToggle extends LitElement {
    static properties = {
        feature: { type: Object }, // { code, name, value, type: 'bool'|'int'|'select' }
        readonly: { type: Boolean },
    };

    static styles = css`
    :host {
      display: block;
      margin-bottom: 8px;
    }

    .wrapper {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      background: rgba(255, 255, 255, 0.03);
      border-radius: 8px;
      border: 1px solid transparent;
      transition: all 0.2s;
    }

    .wrapper:hover {
      background: rgba(255, 255, 255, 0.05);
      border-color: var(--eog-border, #27273a);
    }

    .info {
      flex: 1;
    }

    .name {
      font-size: 14px;
      font-weight: 500;
      color: var(--eog-text, #e4e4e7);
    }

    .code {
      font-size: 11px;
      color: var(--eog-text-muted, #a1a1aa);
      font-family: monospace;
    }

    .control {
      margin-left: 16px;
    }

    /* Switch */
    .switch {
      position: relative;
      display: inline-block;
      width: 40px;
      height: 22px;
    }

    .switch input { 
      opacity: 0;
      width: 0;
      height: 0;
    }

    .slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: var(--eog-border, #27273a);
      transition: .2s;
      border-radius: 22px;
    }

    .slider:before {
      position: absolute;
      content: "";
      height: 18px;
      width: 18px;
      left: 2px;
      bottom: 2px;
      background-color: white;
      transition: .2s;
      border-radius: 50%;
    }

    input:checked + .slider {
      background-color: var(--eog-success, #22c55e);
    }

    input:checked + .slider:before {
      transform: translateX(18px);
    }

    /* Input */
    .input-val {
      background: var(--eog-bg, #09090b);
      border: 1px solid var(--eog-border, #27273a);
      color: white;
      padding: 4px 8px;
      border-radius: 4px;
      width: 80px;
      text-align: right;
    }
  `;

    render() {
        if (!this.feature) return html``;

        return html`
      <div class="wrapper">
        <div class="info">
          <div class="name">${this.feature.name}</div>
          <div class="code">${this.feature.code}</div>
        </div>
        <div class="control">
          ${this._renderControl()}
        </div>
      </div>
    `;
    }

    _renderControl() {
        if (this.readonly) {
            return html`<span style="color:var(--eog-text-muted)">${this.feature.value}</span>`;
        }

        if (this.feature.type === 'bool' || typeof this.feature.value === 'boolean') {
            return html`
        <label class="switch">
          <input type="checkbox" ?checked=${this.feature.value} @change=${this._handleBoolChange}>
          <span class="slider"></span>
        </label>
      `;
        }

        return html`
      <input 
        class="input-val" 
        type="${this.feature.type === 'int' ? 'number' : 'text'}" 
        .value=${this.feature.value}
        @change=${this._handleValChange}
      >
    `;
    }

    _handleBoolChange(e) {
        this._dispatchChange(e.target.checked);
    }

    _handleValChange(e) {
        const val = this.feature.type === 'int' ? parseInt(e.target.value) : e.target.value;
        this._dispatchChange(val);
    }

    _dispatchChange(newValue) {
        this.dispatchEvent(new CustomEvent('change', {
            detail: { code: this.feature.code, value: newValue },
            bubbles: true
        }));
    }
}

customElements.define('eog-feature-toggle', EogFeatureToggle);
