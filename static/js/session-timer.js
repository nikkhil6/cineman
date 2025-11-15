/**
 * Session Timer Monitor
 * 
 * Displays a countdown timer showing when the chat session will reset.
 * The timer updates every 10 seconds and warns users before session expiration.
 */

(function() {
    'use strict';
    
    const TIMER_UPDATE_INTERVAL = 10000; // Update every 10 seconds
    const WARNING_THRESHOLD = 300; // Show warning when < 5 minutes remain
    
    let timerContainer = null;
    let timerDisplay = null;
    let lastRemainingSeconds = null;
    
    /**
     * Initialize the session timer
     */
    function initSessionTimer() {
        createTimerUI();
        updateTimer(); // Initial update
        setInterval(updateTimer, TIMER_UPDATE_INTERVAL);
    }
    
    /**
     * Create the timer UI elements
     */
    function createTimerUI() {
        // Create timer container
        timerContainer = document.createElement('div');
        timerContainer.id = 'session-timer-container';
        timerContainer.className = 'session-timer-container';
        timerContainer.innerHTML = `
            <div class="session-timer" title="Session expires in">
                <span class="timer-icon">⏱️</span>
                <span class="timer-display">--:--</span>
            </div>
        `;
        
        // Insert into header-right section, before API status
        const headerRight = document.querySelector('.header-right');
        if (headerRight) {
            const apiStatus = document.querySelector('.api-status-container');
            if (apiStatus) {
                headerRight.insertBefore(timerContainer, apiStatus);
            } else {
                headerRight.insertBefore(timerContainer, headerRight.firstChild);
            }
            
            timerDisplay = timerContainer.querySelector('.timer-display');
        }
    }
    
    /**
     * Update the timer display
     */
    async function updateTimer() {
        try {
            const response = await fetch('/api/session/timeout');
            const data = await response.json();
            
            if (data.status === 'success' && data.session_exists) {
                const remaining = data.remaining_seconds;
                lastRemainingSeconds = remaining;
                
                // Update display
                updateTimerDisplay(remaining);
                
                // Update warning state
                updateWarningState(remaining);
            } else {
                // No session or expired
                updateTimerDisplay(data.timeout_seconds || 3600);
                timerContainer.classList.remove('warning', 'critical');
            }
        } catch (error) {
            console.error('Failed to update session timer:', error);
            // Show default time on error
            if (timerDisplay) {
                timerDisplay.textContent = '60:00';
            }
        }
    }
    
    /**
     * Update timer display with formatted time
     */
    function updateTimerDisplay(seconds) {
        if (!timerDisplay) return;
        
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        
        timerDisplay.textContent = `${minutes}:${secs.toString().padStart(2, '0')}`;
        
        // Update title
        const timer = timerContainer.querySelector('.session-timer');
        if (timer) {
            if (seconds > 60) {
                timer.title = `Session resets in ${minutes} minutes`;
            } else {
                timer.title = `Session resets in ${seconds} seconds`;
            }
        }
    }
    
    /**
     * Update warning state based on remaining time
     */
    function updateWarningState(seconds) {
        if (!timerContainer) return;
        
        // Remove existing classes
        timerContainer.classList.remove('warning', 'critical');
        
        // Add appropriate class
        if (seconds < 60) {
            timerContainer.classList.add('critical');
        } else if (seconds < WARNING_THRESHOLD) {
            timerContainer.classList.add('warning');
        }
    }
    
    /**
     * Format remaining time for display
     */
    function formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSessionTimer);
    } else {
        initSessionTimer();
    }
})();
