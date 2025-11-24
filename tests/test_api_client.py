"""
Unit tests for MovieDataClient API abstraction.

Tests cover:
- Timeout handling
- Retry logic with exponential backoff
- Error classification (Auth, Quota, NotFound, Transient)
- Successful requests
- Parallel request handling
"""

import pytest
import time
import requests
from unittest.mock import Mock, patch, MagicMock
from cineman.api_client import (
    MovieDataClient,
    APIError,
    AuthError,
    QuotaError,
    NotFoundError,
    TransientError,
    APIErrorType
)


class TestMovieDataClient:
    """Test suite for MovieDataClient."""
    
    def test_initialization_defaults(self):
        """Test client initializes with default values."""
        client = MovieDataClient()
        assert client.timeout == 3.0
        assert client.max_retries == 3
        assert client.backoff_base == 0.5
    
    def test_initialization_custom(self):
        """Test client initializes with custom values."""
        client = MovieDataClient(timeout=5.0, max_retries=2, backoff_base=1.0)
        assert client.timeout == 5.0
        assert client.max_retries == 2
        assert client.backoff_base == 1.0
    
    def test_initialization_from_env(self, monkeypatch):
        """Test client initializes from environment variables."""
        monkeypatch.setenv("API_CLIENT_TIMEOUT", "10.0")
        monkeypatch.setenv("API_CLIENT_MAX_RETRIES", "5")
        monkeypatch.setenv("API_CLIENT_BACKOFF_BASE", "2.0")
        
        client = MovieDataClient()
        assert client.timeout == 10.0
        assert client.max_retries == 5
        assert client.backoff_base == 2.0
    
    def test_successful_request(self):
        """Test successful GET request."""
        client = MovieDataClient()
        
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        
        with patch.object(client.session, 'get', return_value=mock_response):
            response = client.get("https://api.example.com/test", api_name="TestAPI")
            
            assert response.ok
            assert response.status_code == 200
            assert response.json() == {"result": "success"}
    
    def test_auth_error_401(self):
        """Test 401 raises AuthError."""
        client = MovieDataClient()
        
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        with patch.object(client.session, 'get', return_value=mock_response):
            with pytest.raises(AuthError) as exc_info:
                client.get("https://api.example.com/test", api_name="TestAPI")
            
            assert "401" in str(exc_info.value)
            assert exc_info.value.status_code == 401
            assert exc_info.value.error_type == APIErrorType.AUTH
    
    def test_auth_error_403(self):
        """Test 403 raises AuthError."""
        client = MovieDataClient()
        
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        
        with patch.object(client.session, 'get', return_value=mock_response):
            with pytest.raises(AuthError) as exc_info:
                client.get("https://api.example.com/test", api_name="TestAPI")
            
            assert "403" in str(exc_info.value)
            assert exc_info.value.status_code == 403
    
    def test_quota_error_429(self):
        """Test 429 raises QuotaError after retries."""
        client = MovieDataClient(max_retries=2, backoff_base=0.01)
        
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        
        with patch.object(client.session, 'get', return_value=mock_response):
            start = time.time()
            with pytest.raises(QuotaError) as exc_info:
                client.get("https://api.example.com/test", api_name="TestAPI")
            elapsed = time.time() - start
            
            assert "429" in str(exc_info.value)
            assert exc_info.value.status_code == 429
            assert exc_info.value.error_type == APIErrorType.QUOTA
            # Should have retried with backoff (0.01 + 0.02 = 0.03s minimum)
            assert elapsed >= 0.03
    
    def test_not_found_error_404(self):
        """Test 404 raises NotFoundError without retries."""
        client = MovieDataClient()
        
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.text = "Not found"
        
        with patch.object(client.session, 'get', return_value=mock_response):
            with pytest.raises(NotFoundError) as exc_info:
                client.get("https://api.example.com/test", api_name="TestAPI")
            
            assert "404" in str(exc_info.value)
            assert exc_info.value.status_code == 404
            assert exc_info.value.error_type == APIErrorType.NOT_FOUND
    
    def test_transient_error_500_retries(self):
        """Test 500 error retries with exponential backoff."""
        client = MovieDataClient(max_retries=2, backoff_base=0.01)
        
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch.object(client.session, 'get', return_value=mock_response):
            start = time.time()
            with pytest.raises(TransientError) as exc_info:
                client.get("https://api.example.com/test", api_name="TestAPI")
            elapsed = time.time() - start
            
            assert "500" in str(exc_info.value)
            assert exc_info.value.status_code == 500
            assert exc_info.value.error_type == APIErrorType.TRANSIENT
            # Should have retried 2 times with backoff (0.01 + 0.02 = 0.03s minimum)
            assert elapsed >= 0.03
    
    def test_transient_error_connection_error(self):
        """Test ConnectionError is classified as transient and retried."""
        client = MovieDataClient(max_retries=2, backoff_base=0.01)
        
        with patch.object(client.session, 'get', side_effect=requests.exceptions.ConnectionError("Connection failed")):
            start = time.time()
            with pytest.raises(TransientError) as exc_info:
                client.get("https://api.example.com/test", api_name="TestAPI")
            elapsed = time.time() - start
            
            assert "Connection failed" in str(exc_info.value)
            assert exc_info.value.error_type == APIErrorType.TRANSIENT
            # Should have retried with backoff
            assert elapsed >= 0.03
    
    def test_timeout_error_retries(self):
        """Test Timeout is classified as transient and retried."""
        client = MovieDataClient(max_retries=2, backoff_base=0.01, timeout=0.1)
        
        with patch.object(client.session, 'get', side_effect=requests.exceptions.Timeout("Request timeout")):
            start = time.time()
            with pytest.raises(TransientError) as exc_info:
                client.get("https://api.example.com/test", api_name="TestAPI")
            elapsed = time.time() - start
            
            assert "timeout" in str(exc_info.value).lower()
            assert exc_info.value.error_type == APIErrorType.TRANSIENT
            # Should have retried with backoff
            assert elapsed >= 0.03
    
    def test_retry_succeeds_after_failure(self):
        """Test that retry succeeds after initial failure."""
        client = MovieDataClient(max_retries=2, backoff_base=0.01)
        
        # First call fails with 500, second succeeds
        fail_response = Mock()
        fail_response.ok = False
        fail_response.status_code = 500
        fail_response.text = "Server Error"
        
        success_response = Mock()
        success_response.ok = True
        success_response.status_code = 200
        success_response.json.return_value = {"result": "success"}
        
        with patch.object(client.session, 'get', side_effect=[fail_response, success_response]):
            response = client.get("https://api.example.com/test", api_name="TestAPI")
            
            assert response.ok
            assert response.status_code == 200
    
    def test_exponential_backoff_calculation(self):
        """Test exponential backoff calculation."""
        client = MovieDataClient(backoff_base=0.5)
        
        assert client._calculate_backoff(0) == 0.5  # 0.5 * 2^0
        assert client._calculate_backoff(1) == 1.0  # 0.5 * 2^1
        assert client._calculate_backoff(2) == 2.0  # 0.5 * 2^2
    
    def test_should_retry_logic(self):
        """Test retry decision logic."""
        client = MovieDataClient(max_retries=3)
        
        # Should retry transient errors
        assert client._should_retry(APIErrorType.TRANSIENT, 0) is True
        assert client._should_retry(APIErrorType.TRANSIENT, 2) is True
        assert client._should_retry(APIErrorType.TRANSIENT, 3) is False  # Max retries
        
        # Should retry quota errors
        assert client._should_retry(APIErrorType.QUOTA, 0) is True
        assert client._should_retry(APIErrorType.QUOTA, 2) is True
        
        # Should not retry auth errors
        assert client._should_retry(APIErrorType.AUTH, 0) is False
        
        # Should not retry not found errors
        assert client._should_retry(APIErrorType.NOT_FOUND, 0) is False
    
    def test_classify_error_http_status(self):
        """Test error classification based on HTTP status."""
        client = MovieDataClient()
        
        # Auth errors
        resp_401 = Mock(status_code=401)
        assert client._classify_error(resp_401, None) == APIErrorType.AUTH
        
        resp_403 = Mock(status_code=403)
        assert client._classify_error(resp_403, None) == APIErrorType.AUTH
        
        # Not found
        resp_404 = Mock(status_code=404)
        assert client._classify_error(resp_404, None) == APIErrorType.NOT_FOUND
        
        # Quota
        resp_429 = Mock(status_code=429)
        assert client._classify_error(resp_429, None) == APIErrorType.QUOTA
        
        # Transient (5xx)
        resp_500 = Mock(status_code=500)
        assert client._classify_error(resp_500, None) == APIErrorType.TRANSIENT
        
        resp_503 = Mock(status_code=503)
        assert client._classify_error(resp_503, None) == APIErrorType.TRANSIENT
    
    def test_classify_error_exceptions(self):
        """Test error classification based on exception type."""
        client = MovieDataClient()
        
        # Timeout is transient
        timeout_exc = requests.exceptions.Timeout()
        assert client._classify_error(None, timeout_exc) == APIErrorType.TRANSIENT
        
        # Connection error is transient
        conn_exc = requests.exceptions.ConnectionError()
        assert client._classify_error(None, conn_exc) == APIErrorType.TRANSIENT
        
        # Generic request exception is transient
        req_exc = requests.exceptions.RequestException()
        assert client._classify_error(None, req_exc) == APIErrorType.TRANSIENT
    
    def test_custom_timeout_per_request(self):
        """Test that custom timeout can be specified per request."""
        client = MovieDataClient(timeout=3.0)
        
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        
        with patch.object(client.session, 'get', return_value=mock_response) as mock_get:
            client.get("https://api.example.com/test", timeout=10.0, api_name="TestAPI")
            
            # Verify the custom timeout was used
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs['timeout'] == 10.0
    
    def test_context_manager(self):
        """Test client works as context manager."""
        with MovieDataClient() as client:
            assert client.session is not None
        
        # Session should be closed after context exits
        # We can't easily test this without inspecting internal state,
        # but we can verify no errors occur
    
    def test_parallel_requests_no_race_condition(self):
        """Test parallel requests don't cause race conditions."""
        import threading
        
        client = MovieDataClient()
        results = []
        errors = []
        
        def make_request(url_suffix):
            try:
                mock_response = Mock()
                mock_response.ok = True
                mock_response.status_code = 200
                mock_response.json.return_value = {"id": url_suffix}
                
                with patch.object(client.session, 'get', return_value=mock_response):
                    response = client.get(f"https://api.example.com/{url_suffix}", api_name="TestAPI")
                    results.append(response.json())
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request, args=(f"test{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify no errors and all requests succeeded
        assert len(errors) == 0
        assert len(results) == 10
    
    def test_max_retries_environment_variable(self, monkeypatch):
        """Test max retries can be configured via environment variable."""
        monkeypatch.setenv("API_CLIENT_MAX_RETRIES", "1")
        
        client = MovieDataClient()
        
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Error"
        
        call_count = 0
        def count_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response
        
        with patch.object(client.session, 'get', side_effect=count_calls):
            with pytest.raises(TransientError):
                client.get("https://api.example.com/test", api_name="TestAPI")
            
            # Should attempt initial request + 1 retry = 2 total
            assert call_count == 2


class TestErrorClassifications:
    """Test error classification and exception hierarchy."""
    
    def test_auth_error_attributes(self):
        """Test AuthError has correct attributes."""
        error = AuthError("Unauthorized", 401)
        assert error.message == "Unauthorized"
        assert error.status_code == 401
        assert error.error_type == APIErrorType.AUTH
    
    def test_quota_error_attributes(self):
        """Test QuotaError has correct attributes."""
        error = QuotaError("Rate limited", 429)
        assert error.message == "Rate limited"
        assert error.status_code == 429
        assert error.error_type == APIErrorType.QUOTA
    
    def test_not_found_error_attributes(self):
        """Test NotFoundError has correct attributes."""
        error = NotFoundError("Not found", 404)
        assert error.message == "Not found"
        assert error.status_code == 404
        assert error.error_type == APIErrorType.NOT_FOUND
    
    def test_transient_error_attributes(self):
        """Test TransientError has correct attributes."""
        original = requests.exceptions.Timeout()
        error = TransientError("Timeout", None, original)
        assert error.message == "Timeout"
        assert error.error_type == APIErrorType.TRANSIENT
        assert error.original_error == original
    
    def test_api_error_base_class(self):
        """Test all errors inherit from APIError."""
        assert issubclass(AuthError, APIError)
        assert issubclass(QuotaError, APIError)
        assert issubclass(NotFoundError, APIError)
        assert issubclass(TransientError, APIError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
