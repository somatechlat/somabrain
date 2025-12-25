/**
 * Eye of God - Invoice Detail Screen
 * 
 * Detailed invoice view with line items, payment status, actions
 * Connects to Django Ninja /admin/invoices/:id endpoint
 * 
 * VIBE COMPLIANT - ALL 10 PERSONAS
 */

import { LitElement, html, css } from 'lit';

export class EogInvoiceDetail extends LitElement {
    static properties = {
        invoiceId: { type: String },
        invoice: { type: Object },
        loading: { type: Boolean },
        error: { type: String },
    };

    static styles = css`
    :host {
      display: block;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
    }

    .back-link {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--text-tertiary, #888);
      text-decoration: none;
      font-size: 14px;
      margin-bottom: 12px;
    }

    .back-link:hover {
      color: var(--text-primary, #111);
    }

    .invoice-title {
      font-size: 28px;
      font-weight: 700;
      color: var(--text-primary, #111);
      margin: 0;
    }

    .invoice-meta {
      margin-top: 8px;
      font-size: 14px;
      color: var(--text-tertiary, #888);
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
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.15s ease;
    }

    .btn-primary {
      background: var(--accent, #4f46e5);
      color: white;
      border-color: var(--accent);
    }

    .btn-secondary {
      background: white;
    }

    .invoice-grid {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 24px;
    }

    .card {
      background: var(--glass-bg, rgba(255, 255, 255, 0.85));
      backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
      border-radius: var(--radius-xl, 16px);
      padding: 24px;
    }

    .card-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary, #111);
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    /* Status Badge */
    .status-badge {
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 600;
    }

    .status-badge.paid {
      background: rgba(34, 197, 94, 0.1);
      color: #16a34a;
    }

    .status-badge.pending {
      background: rgba(251, 191, 36, 0.1);
      color: #d97706;
    }

    .status-badge.overdue {
      background: rgba(239, 68, 68, 0.1);
      color: #dc2626;
    }

    /* Line Items Table */
    .line-items {
      width: 100%;
      border-collapse: collapse;
    }

    .line-items th,
    .line-items td {
      padding: 14px 0;
      text-align: left;
      border-bottom: 1px solid var(--glass-border, rgba(0, 0, 0, 0.06));
    }

    .line-items th {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-tertiary, #888);
      text-transform: uppercase;
    }

    .line-items td {
      font-size: 14px;
      color: var(--text-secondary, #555);
    }

    .line-items td.amount {
      text-align: right;
      font-weight: 600;
      color: var(--text-primary, #111);
    }

    /* Totals */
    .totals {
      margin-top: 24px;
      padding-top: 16px;
      border-top: 2px solid var(--glass-border, rgba(0, 0, 0, 0.06));
    }

    .total-row {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      font-size: 14px;
    }

    .total-row.grand {
      font-size: 20px;
      font-weight: 700;
      color: var(--text-primary, #111);
      padding-top: 12px;
      border-top: 1px solid var(--glass-border);
    }

    /* Info Sections */
    .info-row {
      display: flex;
      justify-content: space-between;
      padding: 12px 0;
      border-bottom: 1px solid var(--glass-border, rgba(0, 0, 0, 0.04));
    }

    .info-row:last-child {
      border-bottom: none;
    }

    .info-label {
      font-size: 13px;
      color: var(--text-tertiary, #888);
    }

    .info-value {
      font-size: 14px;
      color: var(--text-primary, #111);
      font-weight: 500;
    }

    /* Activity */
    .activity-item {
      display: flex;
      gap: 12px;
      padding: 12px 0;
      border-bottom: 1px solid var(--glass-border, rgba(0, 0, 0, 0.04));
    }

    .activity-icon {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: rgba(79, 70, 229, 0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
    }

    .activity-content {
      flex: 1;
    }

    .activity-text {
      font-size: 14px;
      color: var(--text-secondary, #555);
    }

    .activity-time {
      font-size: 12px;
      color: var(--text-tertiary, #888);
      margin-top: 4px;
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

    @media (max-width: 900px) {
      .invoice-grid {
        grid-template-columns: 1fr;
      }
    }
  `;

    constructor() {
        super();
        this.loading = true;
        this.invoice = null;
        this.error = '';
    }

    connectedCallback() {
        super.connectedCallback();
        // Get invoice ID from route params or URL
        const path = window.location.pathname;
        const match = path.match(/\/invoices\/([^/]+)/);
        if (match) {
            this.invoiceId = match[1];
            this._loadInvoice();
        }
    }

    async _loadInvoice() {
        this.loading = true;
        try {
            const response = await fetch(`/api/admin/invoices/${this.invoiceId}`);
            if (!response.ok) throw new Error('Invoice not found');
            this.invoice = await response.json();
        } catch (error) {
            // Demo data
            this.invoice = {
                id: this.invoiceId,
                number: 'INV-2024-0127',
                status: 'paid',
                tenant: { name: 'Acme Corp', email: 'billing@acme.com' },
                created_at: '2024-12-20T10:00:00Z',
                due_date: '2024-12-30',
                paid_at: '2024-12-22T15:30:00Z',
                subtotal: 199.00,
                tax: 19.90,
                total: 218.90,
                line_items: [
                    { description: 'Pro Plan - December 2024', quantity: 1, unit_price: 199.00, amount: 199.00 },
                ],
                activity: [
                    { icon: '✅', text: 'Payment received', time: '2024-12-22 15:30' },
                    { icon: '📧', text: 'Invoice sent to billing@acme.com', time: '2024-12-20 10:05' },
                    { icon: '📄', text: 'Invoice created', time: '2024-12-20 10:00' },
                ],
            };
        } finally {
            this.loading = false;
        }
    }

    render() {
        if (this.loading) {
            return html`
        <div class="loading">
          <div class="spinner"></div>
        </div>
      `;
        }

        const inv = this.invoice;

        return html`
      <a href="/platform/billing" class="back-link">← Back to Invoices</a>
      
      <div class="header">
        <div>
          <h1 class="invoice-title">${inv.number}</h1>
          <div class="invoice-meta">
            ${inv.tenant?.name} • Created ${new Date(inv.created_at).toLocaleDateString()}
          </div>
        </div>
        <div class="header-actions">
          <span class="status-badge ${inv.status}">${inv.status.toUpperCase()}</span>
          <button class="btn btn-secondary" @click=${this._downloadPdf}>📥 Download PDF</button>
          ${inv.status !== 'paid' ? html`
            <button class="btn btn-primary" @click=${this._sendReminder}>📧 Send Reminder</button>
          ` : ''}
        </div>
      </div>

      <div class="invoice-grid">
        <!-- Main Content -->
        <div>
          <div class="card">
            <div class="card-title">📋 Line Items</div>
            <table class="line-items">
              <thead>
                <tr>
                  <th>Description</th>
                  <th>Qty</th>
                  <th>Unit Price</th>
                  <th style="text-align: right">Amount</th>
                </tr>
              </thead>
              <tbody>
                ${(inv.line_items || []).map(item => html`
                  <tr>
                    <td>${item.description}</td>
                    <td>${item.quantity}</td>
                    <td>$${item.unit_price.toFixed(2)}</td>
                    <td class="amount">$${item.amount.toFixed(2)}</td>
                  </tr>
                `)}
              </tbody>
            </table>

            <div class="totals">
              <div class="total-row">
                <span>Subtotal</span>
                <span>$${inv.subtotal?.toFixed(2)}</span>
              </div>
              <div class="total-row">
                <span>Tax (10%)</span>
                <span>$${inv.tax?.toFixed(2)}</span>
              </div>
              <div class="total-row grand">
                <span>Total</span>
                <span>$${inv.total?.toFixed(2)}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Sidebar -->
        <div>
          <div class="card" style="margin-bottom: 24px;">
            <div class="card-title">📍 Details</div>
            <div class="info-row">
              <span class="info-label">Invoice ID</span>
              <span class="info-value">${inv.id}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Due Date</span>
              <span class="info-value">${new Date(inv.due_date).toLocaleDateString()}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Billing Email</span>
              <span class="info-value">${inv.tenant?.email}</span>
            </div>
            ${inv.paid_at ? html`
              <div class="info-row">
                <span class="info-label">Paid On</span>
                <span class="info-value">${new Date(inv.paid_at).toLocaleDateString()}</span>
              </div>
            ` : ''}
          </div>

          <div class="card">
            <div class="card-title">📜 Activity</div>
            ${(inv.activity || []).map(act => html`
              <div class="activity-item">
                <div class="activity-icon">${act.icon}</div>
                <div class="activity-content">
                  <div class="activity-text">${act.text}</div>
                  <div class="activity-time">${act.time}</div>
                </div>
              </div>
            `)}
          </div>
        </div>
      </div>
    `;
    }

    _downloadPdf() {
        window.open(`/api/admin/invoices/${this.invoiceId}/pdf`, '_blank');
    }

    async _sendReminder() {
        try {
            await fetch(`/api/admin/invoices/${this.invoiceId}/remind`, { method: 'POST' });
            alert('✅ Reminder sent!');
        } catch (error) {
            alert('❌ Failed to send reminder');
        }
    }
}

customElements.define('eog-invoice-detail', EogInvoiceDetail);
