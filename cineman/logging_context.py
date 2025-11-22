"""
Context management for request and session ID propagation.

This module provides utilities for propagating request_id and session_id
throughout the application stack using contextvars (thread-safe).
"""

import uuid
from contextvars import ContextVar
from typing import Optional
import structlog

# Context variables for request and session tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar("session_id", default=None)


def generate_request_id() -> str:
    """
    Generate a unique request ID.
    
    Returns:
        UUID string for request tracking
    """
    return str(uuid.uuid4())


def set_request_id(request_id: Optional[str] = None) -> str:
    """
    Set the request ID in context.
    
    Args:
        request_id: Optional request ID (generates new one if not provided)
        
    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = generate_request_id()
    
    request_id_var.set(request_id)
    structlog.contextvars.bind_contextvars(request_id=request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """
    Get the current request ID from context.
    
    Returns:
        Current request ID or None if not set
    """
    return request_id_var.get()


def set_session_id(session_id: str) -> str:
    """
    Set the session ID in context.
    
    Args:
        session_id: Session ID to set
        
    Returns:
        The session ID that was set
    """
    session_id_var.set(session_id)
    structlog.contextvars.bind_contextvars(session_id=session_id)
    return session_id


def get_session_id() -> Optional[str]:
    """
    Get the current session ID from context.
    
    Returns:
        Current session ID or None if not set
    """
    return session_id_var.get()


def clear_context():
    """
    Clear all context variables.
    
    Useful for cleanup after request processing.
    """
    request_id_var.set(None)
    session_id_var.set(None)
    structlog.contextvars.clear_contextvars()


def bind_context(**kwargs):
    """
    Bind additional context variables to structlog.
    
    Args:
        **kwargs: Key-value pairs to bind to log context
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys):
    """
    Unbind context variables from structlog.
    
    Args:
        *keys: Keys to unbind from log context
    """
    structlog.contextvars.unbind_contextvars(*keys)
