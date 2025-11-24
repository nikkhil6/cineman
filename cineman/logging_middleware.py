"""
Flask middleware for structured logging.

This module provides Flask middleware to:
- Inject request_id and session_id into logging context
- Log HTTP request/response details
- Track request duration and status codes
"""

import time
from flask import Flask, request, g
from typing import Any
from cineman.logging_config import get_logger
from cineman.logging_context import (
    set_request_id,
    set_session_id,
    clear_context,
)

logger = get_logger(__name__)


def init_logging_middleware(app: Flask):
    """
    Initialize logging middleware for Flask application.
    
    Args:
        app: Flask application instance
    """
    
    @app.before_request
    def before_request_logging():
        """
        Set up logging context before each request.
        """
        # Generate and set request ID
        request_id = set_request_id()
        g.request_id = request_id
        g.request_start_time = time.time()
        
        # Set session ID if available
        if hasattr(request, 'cookies') and 'session' in request.cookies:
            # Try to get session_id from Flask session
            from flask import session
            if 'session_id' in session:
                set_session_id(session['session_id'])
        
        # Log incoming request
        logger.info(
            "request_started",
            method=request.method,
            path=request.path,
            remote_addr=request.remote_addr,
            user_agent=request.headers.get('User-Agent', 'Unknown'),
        )
    
    @app.after_request
    def after_request_logging(response):
        """
        Log request completion after each request.
        
        Args:
            response: Flask response object
            
        Returns:
            Unmodified response
        """
        # Calculate request duration
        duration_ms = None
        if hasattr(g, 'request_start_time'):
            duration_ms = (time.time() - g.request_start_time) * 1000
        
        # Log request completion
        logger.info(
            "request_completed",
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2) if duration_ms else None,
        )
        
        # Add request ID to response headers for tracing
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
        
        return response
    
    @app.teardown_request
    def teardown_request_logging(exception=None):
        """
        Clean up logging context after request.
        
        Args:
            exception: Exception if request failed
        """
        if exception:
            logger.error(
                "request_failed",
                method=request.method,
                path=request.path,
                error=str(exception),
                exc_info=True,
            )
        
        # Clear context to avoid leaking between requests
        clear_context()
