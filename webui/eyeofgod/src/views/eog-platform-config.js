/**
 * Eye of God - Platform Configuration Screen
 * 
 * Uses the reusable eog-settings-panel component
 * Connects to Django Ninja /admin/settings endpoint
 * 
 * VIBE COMPLIANT - ALL 10 PERSONAS
 */

import { LitElement, html, css } from 'lit';
import '../components/ui/eog-settings-panel.js';

export class EogPlatformConfig extends LitElement {
    static styles = css`
    :host {
      display: block;
    }
  `;

    constructor() {
        super();

        // Settings configuration - fully declarative
        this.sections = [
            {
                icon: '🔧',
                title: 'Core Settings',
                description: 'Fundamental platform configuration',
                fields: [
                    {
                        key: 'platform_name',
                        label: 'Platform Name',
                        type: 'text',
                        placeholder: 'SomaBrain',
                        description: 'Display name for the platform',
                        runtime: 'dynamic',
                    },
                    {
                        key: 'log_level',
                        label: 'Log Level',
                        type: 'select',
                        options: [
                            { value: 'DEBUG', label: 'Debug' },
                            { value: 'INFO', label: 'Info' },
                            { value: 'WARNING', label: 'Warning' },
                            { value: 'ERROR', label: 'Error' },
                        ],
                        default: 'INFO',
                        runtime: 'dynamic',
                    },
                    {
                        key: 'kill_switch',
                        label: 'Emergency Kill Switch',
                        type: 'toggle',
                        description: 'Disable all API access immediately',
                        default: false,
                        runtime: 'dynamic',
                    },
                    {
                        key: 'maintenance_mode',
                        label: 'Maintenance Mode',
                        type: 'toggle',
                        description: 'Show maintenance message to users',
                        default: false,
                        runtime: 'dynamic',
                    },
                ],
            },
            {
                icon: '🧠',
                title: 'Memory Configuration',
                description: 'Working memory and cache settings',
                fields: [
                    {
                        key: 'working_memory_capacity',
                        label: 'Working Memory Capacity',
                        type: 'number',
                        min: 10,
                        max: 1000,
                        default: 100,
                        description: 'Max items in short-term cache per tenant',
                        runtime: 'dynamic',
                    },
                    {
                        key: 'salience_threshold',
                        label: 'Salience Threshold',
                        type: 'range',
                        min: 0,
                        max: 1,
                        step: 0.05,
                        default: 0.5,
                        description: 'Minimum salience for memory promotion',
                        runtime: 'dynamic',
                    },
                    {
                        key: 'decay_rate',
                        label: 'Decay Rate',
                        type: 'range',
                        min: 0,
                        max: 1,
                        step: 0.01,
                        default: 0.1,
                        description: 'Memory importance decay per cycle',
                        runtime: 'dynamic',
                    },
                    {
                        key: 'auto_promote',
                        label: 'Auto-Promote to LTM',
                        type: 'toggle',
                        description: 'Automatically promote high-salience memories',
                        default: true,
                        runtime: 'dynamic',
                    },
                ],
            },
            {
                icon: '🔗',
                title: 'Integration URLs',
                description: 'External service connections',
                fields: [
                    {
                        key: 'fractalmemory_url',
                        label: 'SomaFractalMemory URL',
                        type: 'url',
                        placeholder: 'http://somafractalmemory:9595',
                        description: 'URL for long-term memory service',
                        runtime: 'static',
                        hint: '⚠️ Requires restart to take effect',
                    },
                    {
                        key: 'lago_url',
                        label: 'Lago Billing URL',
                        type: 'url',
                        placeholder: 'http://lago:3000',
                        description: 'URL for billing service',
                        runtime: 'static',
                    },
                    {
                        key: 'keycloak_url',
                        label: 'Keycloak URL',
                        type: 'url',
                        placeholder: 'http://keycloak:8080',
                        description: 'URL for SSO service',
                        runtime: 'static',
                    },
                    {
                        key: 'milvus_url',
                        label: 'Milvus URL',
                        type: 'url',
                        placeholder: 'localhost:19530',
                        description: 'Vector database connection',
                        runtime: 'static',
                    },
                ],
            },
            {
                icon: '⚡',
                title: 'Rate Limiting',
                description: 'Default rate limits for tenants',
                fields: [
                    {
                        key: 'default_rate_limit',
                        label: 'Default Requests/Minute',
                        type: 'number',
                        min: 10,
                        max: 10000,
                        default: 100,
                        description: 'Default rate limit for new tenants',
                        runtime: 'dynamic',
                    },
                    {
                        key: 'burst_allowance',
                        label: 'Burst Multiplier',
                        type: 'range',
                        min: 1,
                        max: 5,
                        step: 0.5,
                        default: 2,
                        unit: 'x',
                        description: 'Allow burst up to X times the rate limit',
                        runtime: 'dynamic',
                    },
                    {
                        key: 'rate_limit_window',
                        label: 'Window Size (seconds)',
                        type: 'number',
                        min: 1,
                        max: 3600,
                        default: 60,
                        runtime: 'dynamic',
                    },
                ],
            },
            {
                icon: '🔒',
                title: 'Security',
                description: 'Security and authentication settings',
                fields: [
                    {
                        key: 'jwt_expiry',
                        label: 'JWT Token Expiry (hours)',
                        type: 'number',
                        min: 1,
                        max: 168,
                        default: 24,
                        runtime: 'dynamic',
                    },
                    {
                        key: 'require_mfa',
                        label: 'Require MFA for Admins',
                        type: 'toggle',
                        default: false,
                        runtime: 'dynamic',
                    },
                    {
                        key: 'allowed_origins',
                        label: 'Allowed CORS Origins',
                        type: 'textarea',
                        placeholder: 'https://app.example.com\nhttps://admin.example.com',
                        description: 'One URL per line',
                        runtime: 'static',
                    },
                ],
            },
        ];
    }

    render() {
        return html`
      <eog-settings-panel
        title="Platform Configuration"
        icon="⚙️"
        endpoint="/api/admin/settings"
        .sections=${this.sections}
      ></eog-settings-panel>
    `;
    }
}

customElements.define('eog-platform-config', EogPlatformConfig);
