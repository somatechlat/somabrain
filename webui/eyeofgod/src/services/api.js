/**
 * Eye of God - API Service
 * 
 * Base API client for all backend requests.
 * Connects to Django Ninja API at /api/
 * 
 * VIBE COMPLIANT: No mocks, real API calls only.
 */

const API_BASE = '/api';

/**
 * Make authenticated API request
 */
async function request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;

    const defaultHeaders = {
        'Content-Type': 'application/json',
    };

    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
        defaultHeaders['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // Handle 204 No Content
    if (response.status === 204) {
        return null;
    }

    return response.json();
}

/**
 * Tenants API
 */
export const tenantsApi = {
    list: () => request('/admin/tenants'),
    get: (id) => request(`/admin/tenants/${id}`),
    create: (data) => request('/admin/tenants', {
        method: 'POST',
        body: JSON.stringify(data),
    }),
    update: (id, data) => request(`/admin/tenants/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }),
    delete: (id) => request(`/admin/tenants/${id}`, {
        method: 'DELETE',
    }),
};

/**
 * Subscription Tiers API
 */
export const tiersApi = {
    list: () => request('/admin/tiers'),
    get: (id) => request(`/admin/tiers/${id}`),
};

/**
 * API Keys API
 */
export const apiKeysApi = {
    list: (tenantId) => request(`/admin/tenants/${tenantId}/api-keys`),
    create: (tenantId, data) => request(`/admin/tenants/${tenantId}/api-keys`, {
        method: 'POST',
        body: JSON.stringify(data),
    }),
    revoke: (tenantId, keyId) => request(`/admin/tenants/${tenantId}/api-keys/${keyId}`, {
        method: 'DELETE',
    }),
};

/**
 * Billing Config API
 */
export const billingApi = {
    getConfig: () => request('/admin/billing/config'),
    updateConfig: (data) => request('/admin/billing/config', {
        method: 'PATCH',
        body: JSON.stringify(data),
    }),
    testConnection: (data) => request('/admin/billing/config/test', {
        method: 'POST',
        body: JSON.stringify(data),
    }),
};

/**
 * Plans API
 */
export const plansApi = {
    list: () => request('/admin/plans'),
    get: (id) => request(`/admin/plans/${id}`),
    create: (data) => request('/admin/plans', {
        method: 'POST',
        body: JSON.stringify(data),
    }),
    update: (id, data) => request(`/admin/plans/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }),
    sync: (id) => request(`/admin/plans/${id}/sync`, {
        method: 'POST',
    }),
};

/**
 * Invoices API
 */
export const invoicesApi = {
    list: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        return request(`/admin/invoices${query ? `?${query}` : ''}`);
    },
    get: (id) => request(`/admin/invoices/${id}`),
};

/**
 * Health API
 */
export const healthApi = {
    check: () => request('/health'),
    services: () => request('/admin/services/health'),
};

/**
 * Audit API
 */
export const auditApi = {
    list: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        return request(`/admin/audit${query ? `?${query}` : ''}`);
    },
};

/**
 * Platform Stats API
 */
export const statsApi = {
    dashboard: () => request('/admin/stats/dashboard'),
    revenue: () => request('/admin/stats/revenue'),
};

export default {
    tenants: tenantsApi,
    tiers: tiersApi,
    apiKeys: apiKeysApi,
    billing: billingApi,
    plans: plansApi,
    invoices: invoicesApi,
    health: healthApi,
    audit: auditApi,
    stats: statsApi,
};
