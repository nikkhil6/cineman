"""
Prometheus metrics for CineMan application.

This module provides metrics collection for monitoring application performance,
external API usage, caching effectiveness, and validation accuracy.
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
import time


# API Request Metrics
http_requests_total = Counter(
    'cineman_http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'cineman_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# External API Call Metrics
external_api_calls_total = Counter(
    'cineman_external_api_calls_total',
    'Total number of external API calls',
    ['api_name', 'status']
)

external_api_duration_seconds = Histogram(
    'cineman_external_api_duration_seconds',
    'External API call duration in seconds',
    ['api_name']
)

# Cache Metrics
cache_hits_total = Counter(
    'cineman_cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'cineman_cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

# Movie Validation Metrics
movie_validations_total = Counter(
    'cineman_movie_validations_total',
    'Total number of movie validations',
    ['result']  # valid, invalid, dropped, corrected
)

movie_validation_duration_seconds = Histogram(
    'cineman_movie_validation_duration_seconds',
    'Movie validation duration in seconds'
)

# Duplicate Recommendation Metrics
duplicate_recommendations_total = Counter(
    'cineman_duplicate_recommendations_total',
    'Total number of duplicate movie recommendations detected'
)

# Rate Limiter Metrics
rate_limit_usage = Gauge(
    'cineman_rate_limit_usage',
    'Current API rate limit usage count'
)

rate_limit_max = Gauge(
    'cineman_rate_limit_max',
    'Maximum API rate limit'
)

rate_limit_remaining = Gauge(
    'cineman_rate_limit_remaining',
    'Remaining API rate limit calls'
)

rate_limit_exceeded_total = Counter(
    'cineman_rate_limit_exceeded_total',
    'Total number of times rate limit was exceeded'
)

# AI/LLM Metrics
llm_invocations_total = Counter(
    'cineman_llm_invocations_total',
    'Total number of LLM invocations',
    ['status']  # success, error
)

llm_invocation_duration_seconds = Histogram(
    'cineman_llm_invocation_duration_seconds',
    'LLM invocation duration in seconds'
)

# Session Metrics
active_sessions = Gauge(
    'cineman_active_sessions',
    'Number of active user sessions'
)

session_duration_seconds = Histogram(
    'cineman_session_duration_seconds',
    'User session duration in seconds'
)


def track_request(method, endpoint):
    """
    Decorator to track HTTP request metrics.
    
    Usage:
        @track_request('GET', '/api/movie')
        def get_movie():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 200
            try:
                result = func(*args, **kwargs)
                # Extract status code if result is a tuple
                if isinstance(result, tuple) and len(result) >= 2:
                    status = result[1]
                return result
            except Exception as e:
                status = 500
                raise
            finally:
                duration = time.time() - start_time
                http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
                http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
        return wrapper
    return decorator


import structlog

logger = structlog.get_logger()

def track_external_api_call(api_name):
    """
    Decorator to track external API call metrics.
    
    Usage:
        @track_external_api_call('tmdb')
        def call_tmdb_api():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'
            try:
                result = func(*args, **kwargs)
                # Determine status from result
                if isinstance(result, dict):
                    api_status = result.get('status', 'success')
                    if api_status in ('error', 'forbidden', 'not_found'):
                        status = 'error'
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                duration = time.time() - start_time
                external_api_calls_total.labels(api_name=api_name, status=status).inc()
                external_api_duration_seconds.labels(api_name=api_name).observe(duration)
                
                # Log the event
                logger.info(
                    "external_api_call",
                    api_name=api_name,
                    status=status,
                    duration_ms=round(duration * 1000, 2)
                )
        return wrapper
    return decorator


def track_validation(result_type):
    """
    Record a movie validation result.
    
    Args:
        result_type: One of 'valid', 'invalid', 'dropped', 'corrected'
    """
    movie_validations_total.labels(result=result_type).inc()


def track_cache_operation(cache_type, hit=True):
    """
    Record a cache hit or miss.
    
    Args:
        cache_type: Type of cache (e.g., 'movie_data', 'session')
        hit: True for cache hit, False for cache miss
    """
    if hit:
        cache_hits_total.labels(cache_type=cache_type).inc()
    else:
        cache_misses_total.labels(cache_type=cache_type).inc()


def track_duplicate_recommendation():
    """Record a duplicate movie recommendation detection."""
    duplicate_recommendations_total.inc()


def update_rate_limit_metrics(usage, limit, remaining):
    """
    Update rate limiter metrics.
    
    Args:
        usage: Current usage count
        limit: Maximum limit
        remaining: Remaining calls
    """
    rate_limit_usage.set(usage)
    rate_limit_max.set(limit)
    rate_limit_remaining.set(remaining)


def track_rate_limit_exceeded():
    """Record a rate limit exceeded event."""
    rate_limit_exceeded_total.inc()


def track_llm_invocation(success=True, duration=None):
    """
    Record an LLM invocation.
    
    Args:
        success: Whether the invocation was successful
        duration: Duration in seconds (optional)
    """
    status = 'success' if success else 'error'
    llm_invocations_total.labels(status=status).inc()
    if duration is not None:
        llm_invocation_duration_seconds.observe(duration)


def update_active_sessions(count):
    """
    Update the active sessions count.
    
    Args:
        count: Number of active sessions
    """
    active_sessions.set(count)


def track_session_duration(duration):
    """
    Record a session duration.
    
    Args:
        duration: Session duration in seconds
    """
    session_duration_seconds.observe(duration)


def get_metrics():
    """
    Generate Prometheus metrics in text format.
    
    Returns:
        Tuple of (metrics_text, content_type)
    """
    return generate_latest(), CONTENT_TYPE_LATEST
