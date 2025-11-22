"""
Metrics and instrumentation for structured logging.

This module provides utilities for tracking:
- External API call latencies
- Cache hit/miss events
- LLM token usage
"""

import time
from contextlib import contextmanager
from typing import Optional, Dict, Any
from cineman.logging_config import get_logger

logger = get_logger(__name__)


@contextmanager
def track_external_api_call(
    api_name: str,
    operation: str,
    **extra_context
):
    """
    Context manager to track external API call latency.
    
    Args:
        api_name: Name of the external API (e.g., "tmdb", "omdb", "gemini")
        operation: Operation being performed (e.g., "search_movie", "get_facts")
        **extra_context: Additional context to log
        
    Yields:
        None
        
    Example:
        with track_external_api_call("tmdb", "search_movie", title="Inception"):
            result = requests.get(...)
    """
    start_time = time.time()
    error = None
    
    logger.info(
        "external_api_call_started",
        api_name=api_name,
        operation=operation,
        **extra_context
    )
    
    try:
        yield
    except Exception as e:
        error = e
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        
        if error:
            logger.error(
                "external_api_call_failed",
                api_name=api_name,
                operation=operation,
                duration_ms=round(duration_ms, 2),
                error=str(error),
                **extra_context
            )
        else:
            logger.info(
                "external_api_call_completed",
                api_name=api_name,
                operation=operation,
                duration_ms=round(duration_ms, 2),
                **extra_context
            )


def log_cache_event(
    cache_key: str,
    event_type: str,
    hit: bool = False,
    **extra_context
):
    """
    Log cache-related events.
    
    Args:
        cache_key: Cache key being accessed
        event_type: Type of event ("get", "set", "delete", "clear")
        hit: Whether it was a cache hit (for "get" events)
        **extra_context: Additional context to log
    """
    logger.info(
        "cache_event",
        cache_key=cache_key,
        event_type=event_type,
        cache_hit=hit if event_type == "get" else None,
        **extra_context
    )


def log_llm_usage(
    model: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    duration_ms: Optional[float] = None,
    **extra_context
):
    """
    Log LLM token usage and metrics.
    
    Args:
        model: Model name (e.g., "gemini-2.5-flash")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        total_tokens: Total tokens (if provided separately)
        duration_ms: API call duration in milliseconds
        **extra_context: Additional context to log
    """
    logger.info(
        "llm_usage",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens or ((input_tokens or 0) + (output_tokens or 0)),
        duration_ms=duration_ms,
        **extra_context
    )


def log_phase(
    phase: str,
    status: str,
    **extra_context
):
    """
    Log major pipeline phase events.
    
    Args:
        phase: Phase name (e.g., "validation", "recommendation", "session_init")
        status: Phase status ("started", "completed", "failed")
        **extra_context: Additional context to log
    """
    log_level = logger.error if status == "failed" else logger.info
    
    log_level(
        "pipeline_phase",
        phase=phase,
        status=status,
        **extra_context
    )


@contextmanager
def track_phase(phase: str, **extra_context):
    """
    Context manager to track a pipeline phase.
    
    Args:
        phase: Phase name
        **extra_context: Additional context to log
        
    Yields:
        None
        
    Example:
        with track_phase("movie_validation", movie_count=3):
            validate_movies(movies)
    """
    start_time = time.time()
    
    log_phase(phase, "started", **extra_context)
    
    error = None
    try:
        yield
    except Exception as e:
        error = e
        raise
    finally:
        duration_ms = (time.time() - start_time) * 1000
        status = "failed" if error else "completed"
        
        log_phase(
            phase,
            status,
            duration_ms=round(duration_ms, 2),
            error=str(error) if error else None,
            **extra_context
        )
