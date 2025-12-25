/**
 * Eye of God - Invoice List Screen
 * 
 * Uses the reusable eog-data-table component for invoice listing
 * Connects to Django Ninja /admin/invoices endpoint
 * 
 * VIBE COMPLIANT - ALL 10 PERSONAS
 */

import { LitElement, html, css } from 'lit';
import '../components/ui/eog-data-table.js';

export class EogInvoiceList extends LitElement {
    static properties = {
        loading: { type: Boolean },
    };

    static styles = css`
    :host {
      display: block;
    }

    eog-data-table {
      --accent: #4f46e5;
    }
  `;

    constructor() {
        super();
        this.loading = false;

        // Table configuration
        this.columns = [
            { key: 'invoice_number', label: 'Invoice #', type: 'link', href: row => `/platform/billing/invoices/${row.id}` },
            { key: 'tenant_name', label: 'Tenant' },
            { key: 'amount', label: 'Amount', type: 'currency' },
            { key: 'status', label: 'Status', type: 'badge', badgeMap: { paid: 'success', pending: 'pending', overdue: 'error', draft: 'info' } },
            { key: 'due_date', label: 'Due Date', type: 'date' },
            { key: 'created_at', label: 'Created', type: 'date' },
        ];

        this.actions = [
            { icon: '📄', label: 'View', position: 'row' },
            { icon: '📧', label: 'Send', position: 'row' },
            { icon: '📥', label: 'Download', position: 'row' },
            { icon: '➕', label: 'Create Invoice', position: 'header', primary: true },
            { icon: '📊', label: 'Export', position: 'header' },
        ];
    }

    render() {
        return html`
      <eog-data-table
        title="Invoices"
        icon="📄"
        endpoint="/api/admin/invoices"
        .columns=${this.columns}
        .actions=${this.actions}
        @action=${this._handleAction}
        @row-action=${this._handleRowAction}
      ></eog-data-table>
    `;
    }

    _handleAction(e) {
        const { action } = e.detail;
        if (action.label === 'Create Invoice') {
            // Open create invoice modal
            console.log('Create invoice');
        } else if (action.label === 'Export') {
            // Export invoices
            console.log('Export invoices');
        }
    }

    _handleRowAction(e) {
        const { action, row } = e.detail;
        if (action.icon === '📄') {
            window.location.href = `/platform/billing/invoices/${row.id}`;
        } else if (action.icon === '📧') {
            this._sendInvoice(row);
        } else if (action.icon === '📥') {
            this._downloadInvoice(row);
        }
    }

    async _sendInvoice(row) {
        try {
            await fetch(`/api/admin/invoices/${row.id}/send`, { method: 'POST' });
            alert('✅ Invoice sent successfully!');
        } catch (error) {
            alert('❌ Failed to send invoice');
        }
    }

    async _downloadInvoice(row) {
        window.open(`/api/admin/invoices/${row.id}/pdf`, '_blank');
    }
}

customElements.define('eog-invoice-list', EogInvoiceList);
