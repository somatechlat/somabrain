/**
 * Auth Components Index
 * 
 * Export all reusable OAuth/Auth components for easy importing.
 * Components can be reused across:
 * - Eye of God (SysAdmin)
 * - Tenant Admin Portal
 * - Any future auth configuration needs
 */

export { EogOauthProviderForm } from './eog-oauth-provider-form.js';
export { EogOauthProviderList } from './eog-oauth-provider-list.js';
export { EogRoleEditor } from './eog-role-editor.js';
export { EogUserList } from './eog-user-list.js';

// Component documentation
export const AUTH_COMPONENTS = {
    'eog-oauth-provider-form': {
        description: 'Configures OAuth providers (Google, Facebook, GitHub, Keycloak, OIDC)',
        properties: {
            provider: 'Object - Provider data',
            providerType: 'String - Selected provider type',
            mode: 'String - "create" or "edit"',
            isLoading: 'Boolean - Loading state',
            errors: 'Object - Validation errors',
            isPlatformLevel: 'Boolean - Platform vs Tenant scope'
        },
        events: {
            submit: 'Provider data to save',
            cancel: 'Form cancelled',
            'test-connection': 'Test provider connection'
        }
    },
    'eog-oauth-provider-list': {
        description: 'List of configured OAuth providers with actions',
        properties: {
            providers: 'Array - List of providers',
            isLoading: 'Boolean - Loading state',
            isPlatformLevel: 'Boolean - Platform vs Tenant scope',
            selectedProviderId: 'String - Currently selected provider'
        },
        events: {
            'add-provider': 'Add new provider',
            'select-provider': 'Provider selected',
            'configure-provider': 'Configure provider',
            'test-connection': 'Test provider connection',
            'toggle-provider': 'Enable/disable provider',
            'delete-provider': 'Delete provider'
        }
    },
    'eog-role-editor': {
        description: 'Permission matrix editor for roles',
        properties: {
            role: 'Object - Current role',
            matrix: 'Array - Permission matrix from API',
            isLoading: 'Boolean - Loading state',
            isEditable: 'Boolean - Can edit permissions'
        },
        events: {
            save: 'Save permission changes',
            cancel: 'Cancel editing'
        }
    },
    'eog-user-list': {
        description: 'User management list with filters and actions',
        properties: {
            users: 'Array - List of users',
            roles: 'Array - Available roles for filter',
            isLoading: 'Boolean - Loading state',
            selectedUserId: 'String - Selected user ID',
            filters: 'Object - Current filter values'
        },
        events: {
            'add-user': 'Add new user',
            'select-user': 'User selected',
            'edit-user': 'Edit user',
            'toggle-status': 'Enable/disable user',
            'filter-change': 'Filters changed'
        }
    }
};
