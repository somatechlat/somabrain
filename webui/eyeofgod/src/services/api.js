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
    list: () => request('/saas/tiers'),
    get: (id) => request(`/saas/tiers/${id}`),
    create: (data) => request('/saas/tiers', {
        method: 'POST',
        body: JSON.stringify(data)
    }),
    update: (id, data) => request(`/saas/tiers/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data)
    }),
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
 * 🚨 SRE: Complete infrastructure visibility
 */
export const healthApi = {
    simple: () => request('/health/simple'),
    full: () => request('/health/full'),
    services: () => request('/health/full'),
    infrastructure: () => request('/health/infrastructure'),
    database: () => request('/health/database'),
};

/**
 * Audit API
 * 🔒 Security: Complete action visibility
 */
export const auditApi = {
    list: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        return request(`/audit/${query ? `?${query}` : ''}`);
    },
};

/**
 * Platform Stats API
 * 📊 SRE: Platform metrics
 */
export const statsApi = {
    dashboard: () => request('/admin/stats/dashboard'),
    revenue: () => request('/admin/stats/revenue'),
    memory: () => request('/admin/stats/memory'),
};

/**
 * OAuth Providers API
 * 🔐 Security: Identity provider management
 */
export const oauthApi = {
    list: () => request('/oauth/providers'),
    get: (id) => request(`/oauth/providers/${id}`),
    create: (data) => request('/oauth/providers', {
        method: 'POST',
        body: JSON.stringify(data),
    }),
    update: (id, data) => request(`/oauth/providers/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }),
    delete: (id) => request(`/oauth/providers/${id}`, {
        method: 'DELETE',
    }),
    test: (id) => request(`/oauth/providers/${id}/test`, {
        method: 'POST',
    }),
};

/**
 * Users API
 * 👥 Platform and tenant user management
 */
export const usersApi = {
    list: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        return request(`/admin/users${query ? `?${query}` : ''}`);
    },
    get: (id) => request(`/admin/users/${id}`),
    create: (data) => request('/admin/users', {
        method: 'POST',
        body: JSON.stringify(data),
    }),
    update: (id, data) => request(`/admin/users/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }),
    disable: (id) => request(`/admin/users/${id}/disable`, {
        method: 'POST',
    }),
    enable: (id) => request(`/admin/users/${id}/enable`, {
        method: 'POST',
    }),
};

/**
 * Memory API
 * 🧠 Memory system operations
 */
export const memoryApi = {
    stats: () => request('/admin/memory/stats'),
    nodes: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        return request(`/admin/memory/nodes${query ? `?${query}` : ''}`);
    },
    getNode: (id) => request(`/admin/memory/nodes/${id}`),
    graph: (nodeId, depth = 2) => request(`/admin/memory/nodes/${nodeId}/graph?depth=${depth}`),
};

/**
 * Settings API
 * ⚙️ Platform configuration
 */
export const settingsApi = {
    get: () => request('/admin/settings'),
    update: (data) => request('/admin/settings', {
        method: 'PATCH',
        body: JSON.stringify(data),
    }),
};

/**
 * Features API
 * ✨ Feature flags management
 */
export const featuresApi = {
    list: () => request('/admin/features'),
    update: (code, data) => request(`/admin/features/${code}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }),
};

/**
 * Roles & Permissions API
 */
export const rolesApi = {
    list: () => request('/roles/'),
    get: (id) => request(`/roles/${id}`),
    create: (data) => request('/roles/', {
        method: 'POST',
        body: JSON.stringify(data)
    }),
    update: (id, data) => request(`/roles/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data)
    }),
    delete: (id) => request(`/roles/${id}`, {
        method: 'DELETE'
    }),
    getMatrix: (roleId) => request(`/roles/${roleId}/matrix`),
    updateMatrix: (roleId, matrix) => request(`/roles/${roleId}/matrix`, {
        method: 'POST',
        body: JSON.stringify(matrix)
    }),
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
    roles: rolesApi,
    oauth: oauthApi,
    users: usersApi,
    memory: memoryApi,
    settings: settingsApi,
    features: featuresApi,
};
