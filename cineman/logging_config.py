"""
Structured JSON logging configuration for Cineman.

This module sets up structured logging using structlog with:
- JSON formatting for production
- Console formatting for development
- Request/session ID propagation
- Log scrubbing for sensitive data (API keys, PII)
- Configurable log levels via environment variables
"""

import os
import logging
import structlog
from typing import Any, Dict, Optional
import re

# Log level configuration via environment variable
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Sensitive data patterns for scrubbing
SENSITIVE_PATTERNS = {
    "api_key": re.compile(r'(api[_\-]?key["\s:=]+)([a-zA-Z0-9_\-]{20,})', re.IGNORECASE),
    "gemini_key": re.compile(r'(gemini[_\-]?api[_\-]?key["\s:=]+)([a-zA-Z0-9_\-]{20,})', re.IGNORECASE),
    "tmdb_key": re.compile(r'(tmdb[_\-]?api[_\-]?key["\s:=]+)([a-zA-Z0-9_\-]{20,})', re.IGNORECASE),
    "omdb_key": re.compile(r'(omdb[_\-]?api[_\-]?key["\s:=]+)([a-zA-Z0-9_\-]{20,})', re.IGNORECASE),
    "bearer_token": re.compile(r'(bearer\s+)([a-zA-Z0-9_\-]{20,})', re.IGNORECASE),
    "authorization": re.compile(r'(authorization["\s:=]+)([a-zA-Z0-9_\-]{20,})', re.IGNORECASE),
}

# Sensitive field names that should be fully redacted
SENSITIVE_FIELD_NAMES = {
    "api_key", "apikey", "api-key",
    "gemini_api_key", "gemini-api-key", "gemini_key",
    "tmdb_api_key", "tmdb-api-key", "tmdb_key",
    "omdb_api_key", "omdb-api-key", "omdb_key",
    "password", "passwd", "pwd",
    "secret", "token", "auth", "authorization",
    "bearer", "access_token", "refresh_token",
}

# Email pattern for PII scrubbing
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')


# Fields that should never be scrubbed (e.g., request tracking)
SAFE_FIELD_NAMES = {
    "request_id", "session_id", "event", "timestamp", "level",
    "service", "environment", "duration_ms", "status_code",
}


def scrub_sensitive_data(value: Any, parent_key: str = None) -> Any:
    """
    Recursively scrub sensitive data from log entries.
    
    Args:
        value: Value to scrub (can be dict, list, str, or other)
        parent_key: Parent key name for field-level redaction
        
    Returns:
        Scrubbed value with sensitive data replaced with [REDACTED]
    """
    if isinstance(value, dict):
        return {k: scrub_sensitive_data(v, k) for k, v in value.items()}
    elif isinstance(value, list):
        return [scrub_sensitive_data(item, parent_key) for item in value]
    elif isinstance(value, str):
        # Never scrub safe fields like request_id, session_id
        if parent_key and parent_key.lower() in SAFE_FIELD_NAMES:
            return value
        
        # Check if parent key is a sensitive field name
        if parent_key and parent_key.lower() in SENSITIVE_FIELD_NAMES:
            return "[REDACTED]"
        
        # Scrub API keys (looking for 20+ character alphanumeric sequences that look like keys)
        # Pattern: AIza... or any long alphanumeric string in certain contexts
        scrubbed = value
        
        # Bearer tokens
        scrubbed = re.sub(r'Bearer\s+[A-Za-z0-9_\-]+', 'Bearer [REDACTED]', scrubbed, flags=re.IGNORECASE)
        
        # Google API key pattern (AIza... with 20+ more characters)
        scrubbed = re.sub(r'AIza[A-Za-z0-9_\-]{20,}', '[REDACTED]', scrubbed)
        
        # Generic API key pattern - alphanumeric strings 25+ chars (likely API keys)
        # But skip if it looks like a UUID (has dashes in specific positions)
        if not re.match(r'^[a-f0-9]{8}\-[a-f0-9]{4}\-[a-f0-9]{4}\-[a-f0-9]{4}\-[a-f0-9]{12}$', value, re.IGNORECASE):
            scrubbed = re.sub(r'\b[A-Za-z0-9_\-]{25,}\b', '[REDACTED]', scrubbed)
        
        # Specific patterns
        for pattern_name, pattern in SENSITIVE_PATTERNS.items():
            scrubbed = pattern.sub(r'\1[REDACTED]', scrubbed)
        
        # Scrub email addresses (PII)
        scrubbed = EMAIL_PATTERN.sub('[EMAIL_REDACTED]', scrubbed)
        
        return scrubbed
    else:
        # Never scrub safe fields
        if parent_key and parent_key.lower() in SAFE_FIELD_NAMES:
            return value
        
        # Check if parent key is sensitive (for non-string values)
        if parent_key and parent_key.lower() in SENSITIVE_FIELD_NAMES:
            return "[REDACTED]"
        return value


def add_app_context(logger: Any, method_name: str, event_dict: Dict) -> Dict:
    """
    Add application context to log entries.
    
    Args:
        logger: Logger instance
        method_name: Logging method name
        event_dict: Event dictionary to enhance
        
    Returns:
        Enhanced event dictionary
    """
    # Add service name
    event_dict["service"] = "cineman"
    
    # Add environment if available
    if os.getenv("GAE_ENV"):
        event_dict["environment"] = "gcp-app-engine"
    elif os.getenv("CLOUD_RUN_SERVICE"):
        event_dict["environment"] = "gcp-cloud-run"
    else:
        event_dict["environment"] = "local"
    
    return event_dict


def add_scrubbing(logger: Any, method_name: str, event_dict: Dict) -> Dict:
    """
    Processor to scrub sensitive data from log entries.
    
    Args:
        logger: Logger instance
        method_name: Logging method name
        event_dict: Event dictionary to scrub
        
    Returns:
        Scrubbed event dictionary
    """
    return scrub_sensitive_data(event_dict)


def configure_structlog():
    """
    Configure structlog for the application.
    
    Sets up processors, formatters, and output based on environment.
    """
    # Determine if we're in development mode
    is_dev = os.getenv("FLASK_ENV") == "development" or os.getenv("DEBUG") == "1"
    
    # Set up processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_app_context,
        add_scrubbing,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Add appropriate formatter based on environment
    if is_dev:
        # Console output for development
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(LOG_LEVEL)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a configured structlog logger.
    
    Args:
        name: Optional logger name (defaults to calling module)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Configure logging on module import
configure_structlog()
