"""
MovieDataClient: Robust API client abstraction for external movie APIs.

This module provides a unified interface for making HTTP requests to external
movie data APIs (TMDB, OMDb) with built-in retry logic, timeout handling, 
and standardized error classification.

Key Features:
- Automatic retries with exponential backoff
- Configurable timeouts per request
- Error taxonomy for different failure types
- Comprehensive logging of retry attempts and failures
- Thread-safe for parallel requests

Error Taxonomy:
- TransientError: Temporary failures that may succeed on retry (network issues, 5xx errors)
- AuthError: Authentication/authorization failures (401, 403)
- QuotaError: Rate limiting or quota exceeded (429)
- NotFoundError: Resource not found (404)
"""

import os
import time
import logging
import requests
from typing import Dict, Any, Optional
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class APIErrorType(Enum):
    """Classification of API errors."""
    TRANSIENT = "transient"  # Temporary failures (network issues, 5xx)
    AUTH = "auth"  # Authentication failures (401, 403)
    QUOTA = "quota"  # Rate limiting (429)
    NOT_FOUND = "not_found"  # Resource not found (404)
    UNKNOWN = "unknown"  # Unclassified errors


class APIError(Exception):
    """Base exception for all API errors."""
    
    def __init__(self, message: str, error_type: APIErrorType, status_code: Optional[int] = None, 
                 original_error: Optional[Exception] = None):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.original_error = original_error
        super().__init__(message)


class TransientError(APIError):
    """Temporary error that may succeed on retry."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 original_error: Optional[Exception] = None):
        super().__init__(message, APIErrorType.TRANSIENT, status_code, original_error)


class AuthError(APIError):
    """Authentication or authorization error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message, APIErrorType.AUTH, status_code)


class QuotaError(APIError):
    """Rate limiting or quota exceeded error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message, APIErrorType.QUOTA, status_code)


class NotFoundError(APIError):
    """Resource not found error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message, APIErrorType.NOT_FOUND, status_code)


class MovieDataClient:
    """
    HTTP client for movie data APIs with retry logic and error handling.
    
    Configuration via environment variables:
    - API_CLIENT_TIMEOUT: Default timeout in seconds (default: 3.0)
    - API_CLIENT_MAX_RETRIES: Maximum retry attempts (default: 3)
    - API_CLIENT_BACKOFF_BASE: Base delay for exponential backoff in seconds (default: 0.5)
    """
    
    def __init__(
        self,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        backoff_base: Optional[float] = None
    ):
        """
        Initialize the MovieDataClient.
        
        Args:
            timeout: Request timeout in seconds (default: 3.0 or from env)
            max_retries: Maximum number of retry attempts (default: 3 or from env)
            backoff_base: Base delay for exponential backoff (default: 0.5 or from env)
        """
        self.timeout = timeout or float(os.getenv("API_CLIENT_TIMEOUT", "3.0"))
        self.max_retries = max_retries or int(os.getenv("API_CLIENT_MAX_RETRIES", "3"))
        self.backoff_base = backoff_base or float(os.getenv("API_CLIENT_BACKOFF_BASE", "0.5"))
        
        # Create session for connection pooling
        self.session = requests.Session()
        
        logger.info(
            f"MovieDataClient initialized: timeout={self.timeout}s, "
            f"max_retries={self.max_retries}, backoff_base={self.backoff_base}s"
        )
    
    def _classify_error(self, response: Optional[requests.Response], 
                       exception: Optional[Exception]) -> APIErrorType:
        """
        Classify an error based on HTTP status code or exception type.
        
        Args:
            response: HTTP response object (if available)
            exception: Exception that occurred (if available)
            
        Returns:
            APIErrorType classification
        """
        # HTTP status code based classification
        if response is not None:
            status = response.status_code
            
            if status == 401 or status == 403:
                return APIErrorType.AUTH
            elif status == 404:
                return APIErrorType.NOT_FOUND
            elif status == 429:
                return APIErrorType.QUOTA
            elif 500 <= status < 600:
                return APIErrorType.TRANSIENT
            elif 400 <= status < 500:
                # Other 4xx errors are generally not transient
                return APIErrorType.UNKNOWN
        
        # Exception based classification
        if exception is not None:
            if isinstance(exception, requests.exceptions.Timeout):
                return APIErrorType.TRANSIENT
            elif isinstance(exception, requests.exceptions.ConnectionError):
                return APIErrorType.TRANSIENT
            elif isinstance(exception, requests.exceptions.RequestException):
                return APIErrorType.TRANSIENT
        
        return APIErrorType.UNKNOWN
    
    def _should_retry(self, error_type: APIErrorType, attempt: int) -> bool:
        """
        Determine if a request should be retried based on error type and attempt count.
        
        Args:
            error_type: Type of error that occurred
            attempt: Current attempt number (0-indexed)
            
        Returns:
            True if should retry, False otherwise
        """
        # Don't retry if we've exhausted attempts
        if attempt >= self.max_retries:
            return False
        
        # Only retry transient errors and quota errors
        return error_type in (APIErrorType.TRANSIENT, APIErrorType.QUOTA)
    
    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: 0.5s, 1s, 2s (by default)
        return self.backoff_base * (2 ** attempt)
    
    def _raise_classified_error(self, error_type: APIErrorType, message: str, 
                               status_code: Optional[int] = None,
                               original_error: Optional[Exception] = None):
        """
        Raise an appropriately classified error.
        
        Args:
            error_type: Type of error
            message: Error message
            status_code: HTTP status code (if available)
            original_error: Original exception (if available)
        """
        if error_type == APIErrorType.AUTH:
            raise AuthError(message, status_code)
        elif error_type == APIErrorType.QUOTA:
            raise QuotaError(message, status_code)
        elif error_type == APIErrorType.NOT_FOUND:
            raise NotFoundError(message, status_code)
        elif error_type == APIErrorType.TRANSIENT:
            raise TransientError(message, status_code, original_error)
        else:
            raise APIError(message, error_type, status_code, original_error)
    
    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        api_name: str = "API"
    ) -> requests.Response:
        """
        Make a GET request with retry logic and error handling.
        
        Args:
            url: Request URL
            params: Query parameters
            headers: Request headers
            timeout: Override default timeout for this request
            api_name: Name of the API for logging (e.g., "TMDB", "OMDb")
            
        Returns:
            Response object if successful
            
        Raises:
            AuthError: Authentication failure
            QuotaError: Rate limit exceeded
            NotFoundError: Resource not found
            TransientError: Temporary failure after retries
            APIError: Other unclassified errors
        """
        request_timeout = timeout or self.timeout
        attempt = 0
        last_error: Optional[Exception] = None
        last_response: Optional[requests.Response] = None
        
        # Build log context
        log_context = f"[{api_name}]"
        
        while attempt <= self.max_retries:
            try:
                logger.debug(
                    f"{log_context} Request attempt {attempt + 1}/{self.max_retries + 1}: "
                    f"GET {url} (timeout={request_timeout}s)"
                )
                
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=request_timeout
                )
                
                # Successful response (2xx)
                if response.ok:
                    if attempt > 0:
                        logger.info(
                            f"{log_context} Request succeeded after {attempt + 1} attempt(s)"
                        )
                    return response
                
                # Non-2xx response - classify and handle
                last_response = response
                error_type = self._classify_error(response, None)
                
                logger.warning(
                    f"{log_context} Request failed with status {response.status_code}: "
                    f"{response.text[:200]}"
                )
                
                # Check if we should retry
                if self._should_retry(error_type, attempt):
                    backoff_delay = self._calculate_backoff(attempt)
                    logger.info(
                        f"{log_context} Retrying after {backoff_delay}s "
                        f"(attempt {attempt + 1}/{self.max_retries}, error_type={error_type.value})"
                    )
                    time.sleep(backoff_delay)
                    attempt += 1
                    continue
                
                # Non-retryable error - raise immediately
                error_msg = (
                    f"{api_name} request failed with status {response.status_code}: "
                    f"{response.text[:200]}"
                )
                self._raise_classified_error(error_type, error_msg, response.status_code)
                
            except requests.exceptions.RequestException as e:
                last_error = e
                error_type = self._classify_error(None, e)
                
                logger.warning(
                    f"{log_context} Request exception: {type(e).__name__}: {str(e)}"
                )
                
                # Check if we should retry
                if self._should_retry(error_type, attempt):
                    backoff_delay = self._calculate_backoff(attempt)
                    logger.info(
                        f"{log_context} Retrying after {backoff_delay}s "
                        f"(attempt {attempt + 1}/{self.max_retries}, error_type={error_type.value})"
                    )
                    time.sleep(backoff_delay)
                    attempt += 1
                    continue
                
                # Non-retryable or exhausted retries
                error_msg = f"{api_name} request failed: {type(e).__name__}: {str(e)}"
                self._raise_classified_error(error_type, error_msg, None, e)
        
        # Should not reach here, but handle exhausted retries
        if last_response is not None:
            error_type = self._classify_error(last_response, None)
            error_msg = (
                f"{api_name} request failed after {self.max_retries + 1} attempts: "
                f"status {last_response.status_code}"
            )
            logger.error(f"{log_context} {error_msg}")
            self._raise_classified_error(error_type, error_msg, last_response.status_code)
        elif last_error is not None:
            error_type = self._classify_error(None, last_error)
            error_msg = (
                f"{api_name} request failed after {self.max_retries + 1} attempts: "
                f"{type(last_error).__name__}: {str(last_error)}"
            )
            logger.error(f"{log_context} {error_msg}")
            self._raise_classified_error(error_type, error_msg, None, last_error)
        
        # Fallback (should never reach here)
        raise APIError(
            f"{api_name} request failed after {self.max_retries + 1} attempts",
            APIErrorType.UNKNOWN
        )
    
    def close(self):
        """Close the underlying session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
