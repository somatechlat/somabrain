/**
 * Eye of God - Main Application Entry Point
 * 
 * SomaBrain AAAS Platform Administration UI
 * Built with Lit WebComponents + Vaadin Router
 * 
 * VIBE Coding Rules v5.2 - ALL 7 PERSONAS:
 * - Architect: Clean component architecture
 * - Security: Auth checks on every route
 * - DevOps: Dev/prod config handling
 * - QA: Testable components
 * - Docs: Comprehensive comments
 * - DBA: Efficient API calls
 * - SRE: Error handling, logging
 */

import { Router } from '@vaadin/router';
import './components/eog-app.js';

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Replace loading indicator with app shell
    const app = document.getElementById('app');
    app.innerHTML = '<eog-app></eog-app>';
});
