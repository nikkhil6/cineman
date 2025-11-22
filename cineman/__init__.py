"""
Cineman - AI Movie Recommender

A Flask-based application for AI-powered movie recommendations using
Google Gemini AI, LangChain, and movie data APIs.
"""

__version__ = "1.0.0"

# Export API client for external use
from .api_client import (
    MovieDataClient,
    APIError,
    AuthError,
    QuotaError,
    NotFoundError,
    TransientError,
    APIErrorType
)

__all__ = [
    "MovieDataClient",
    "APIError",
    "AuthError",
    "QuotaError",
    "NotFoundError",
    "TransientError",
    "APIErrorType",
]

