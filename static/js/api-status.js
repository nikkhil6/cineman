/**
 * API Status Monitor
 * 
 * Periodically checks the status of external APIs (Gemini, TMDB, OMDB)
 * and displays status indicators in the top-right corner of the page.
 */

(function() {
    'use strict';
    
    const STATUS_CHECK_INTERVAL = 60000; // Check every 60 seconds
    const STATUS_ICONS = {
        operational: '🟢',
        degraded: '🟡',
        error: '🔴'
    };
    
    let statusContainer = null;
    let statusTooltip = null;
    let lastCheckTime = null;
    
    /**
     * Initialize the status monitor
     */
    function initStatusMonitor() {
        createStatusUI();
        checkAPIStatus(); // Initial check
        setInterval(checkAPIStatus, STATUS_CHECK_INTERVAL);
    }
    
    /**
     * Create the status UI elements
     */
    function createStatusUI() {
        // Create status container
        statusContainer = document.createElement('div');
        statusContainer.id = 'api-status-container';
        statusContainer.className = 'api-status-container';
        statusContainer.innerHTML = `
            <div class="api-status-indicator" title="API Status">
                <span class="status-icon">⚪</span>
                <span class="status-text">Checking...</span>
            </div>
        `;
        
        // Create tooltip for detailed status
        statusTooltip = document.createElement('div');
        statusTooltip.id = 'api-status-tooltip';
        statusTooltip.className = 'api-status-tooltip';
        statusTooltip.style.display = 'none';
        
        // Insert into header-right section
        const headerRight = document.querySelector('.header-right');
        if (headerRight) {
            headerRight.insertBefore(statusContainer, headerRight.firstChild);
            document.body.appendChild(statusTooltip);
            
            // Add hover events
            statusContainer.addEventListener('mouseenter', showTooltip);
            statusContainer.addEventListener('mouseleave', hideTooltip);
        }
    }
    
    /**
     * Check API status from the backend
     */
    async function checkAPIStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.status === 'success') {
                lastCheckTime = new Date();
                updateStatusUI(data.services);
            } else {
                updateStatusUI(null, 'Error checking status');
            }
        } catch (error) {
            console.error('Failed to check API status:', error);
            updateStatusUI(null, 'Connection error');
        }
    }
    
    /**
     * Update the status UI with latest data
     */
    function updateStatusUI(services, errorMessage) {
        const indicator = statusContainer.querySelector('.api-status-indicator');
        const icon = statusContainer.querySelector('.status-icon');
        const text = statusContainer.querySelector('.status-text');
        
        if (errorMessage) {
            icon.textContent = STATUS_ICONS.error;
            text.textContent = 'Error';
            indicator.className = 'api-status-indicator status-error';
            updateTooltip(null, errorMessage);
            return;
        }
        
        // Determine overall status
        const statuses = Object.values(services).map(s => s.status);
        let overallStatus = 'operational';
        
        if (statuses.some(s => s === 'error')) {
            overallStatus = 'error';
        } else if (statuses.some(s => s === 'degraded')) {
            overallStatus = 'degraded';
        }
        
        // Update indicator
        icon.textContent = STATUS_ICONS[overallStatus];
        text.textContent = overallStatus === 'degraded' ? 'Degraded' : 
                          overallStatus === 'error' ? 'Issues' : '';
        indicator.className = `api-status-indicator status-${overallStatus}`;
        
        // Update tooltip
        updateTooltip(services);
    }
    
    /**
     * Update tooltip content
     */
    function updateTooltip(services, errorMessage) {
        if (errorMessage) {
            statusTooltip.innerHTML = `
                <div class="tooltip-header">API Status</div>
                <div class="tooltip-error">${errorMessage}</div>
            `;
            return;
        }
        
        const formatTime = (ms) => {
            return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`;
        };
        
        const serviceLabels = {
            gemini: 'Gemini AI',
            tmdb: 'TMDB',
            omdb: 'OMDB'
        };
        
        let tooltipHTML = '<div class="tooltip-header">API Status</div>';
        tooltipHTML += '<div class="tooltip-services">';
        
        for (const [key, service] of Object.entries(services)) {
            const statusClass = `service-status-${service.status}`;
            const icon = STATUS_ICONS[service.status];
            const label = serviceLabels[key] || key;
            
            tooltipHTML += `
                <div class="service-item ${statusClass}">
                    <span class="service-icon">${icon}</span>
                    <span class="service-name">${label}</span>
                    <span class="service-time">${formatTime(service.response_time)}</span>
                </div>
            `;
            
            if (service.message && service.status !== 'operational') {
                tooltipHTML += `
                    <div class="service-message">${service.message}</div>
                `;
            }
        }
        
        tooltipHTML += '</div>';
        
        if (lastCheckTime) {
            const timeStr = lastCheckTime.toLocaleTimeString();
            tooltipHTML += `<div class="tooltip-footer">Last checked: ${timeStr}</div>`;
        }
        
        statusTooltip.innerHTML = tooltipHTML;
    }
    
    /**
     * Show tooltip
     */
    function showTooltip(event) {
        const rect = statusContainer.getBoundingClientRect();
        statusTooltip.style.display = 'block';
        statusTooltip.style.top = `${rect.bottom + 10}px`;
        statusTooltip.style.right = `${window.innerWidth - rect.right}px`;
    }
    
    /**
     * Hide tooltip
     */
    function hideTooltip() {
        statusTooltip.style.display = 'none';
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initStatusMonitor);
    } else {
        initStatusMonitor();
    }
})();
