"""
Integration tests for TMDB and OMDb tools with MovieDataClient.

Tests verify that the tools correctly integrate with the API client
and handle various error scenarios appropriately.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from cineman.tools.tmdb import get_movie_poster_core
from cineman.tools.omdb import fetch_omdb_data_core
from cineman.api_client import AuthError, QuotaError, NotFoundError, TransientError, APIError



class TestTMDBToolIntegration:
    """Test TMDB tool integration with MovieDataClient."""
    
    def test_successful_tmdb_search(self):
        """Test successful TMDB movie search."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 12345,
                    "title": "Inception",
                    "poster_path": "/inception.jpg",
                    "release_date": "2010-07-16",
                    "vote_average": 8.8,
                    "vote_count": 29000
                }
            ]
        }
        
        with patch('cineman.tools.tmdb.TMDB_API_KEY', 'test_key'):
            with patch('cineman.tools.tmdb._get_tmdb_client') as mock_client_getter:
                mock_client = Mock()
                mock_client.get.return_value = mock_response
                mock_client_getter.return_value = mock_client
                
                result = get_movie_poster_core("Inception")
                
                assert result["status"] == "success"
                assert result["title"] == "Inception"
                assert result["year"] == "2010"
                assert result["tmdb_id"] == 12345
                assert result["vote_average"] == 8.8
                assert result["poster_url"] == "https://image.tmdb.org/t/p/w500/inception.jpg"
    
    def test_tmdb_not_found(self):
        """Test TMDB returns not found for unknown movie."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        
        with patch('cineman.tools.tmdb.TMDB_API_KEY', 'test_key'):
            with patch('cineman.tools.tmdb._get_tmdb_client') as mock_client_getter:
                mock_client = Mock()
                mock_client.get.return_value = mock_response
                mock_client_getter.return_value = mock_client
                
                result = get_movie_poster_core("NonExistentMovie123456")
                
                assert result["status"] == "not_found"
    
    def test_tmdb_auth_error(self):
        """Test TMDB handles authentication error."""
        with patch('cineman.tools.tmdb.TMDB_API_KEY', 'test_key'):
            with patch('cineman.tools.tmdb._get_tmdb_client') as mock_client_getter:
                mock_client = Mock()
                mock_client.get.side_effect = AuthError("Invalid API key", 401)
                mock_client_getter.return_value = mock_client
                
                result = get_movie_poster_core("Inception")
                
                assert result["status"] == "auth_error"
                assert "error_type" in result
                assert result["error_type"] == "auth"
    
    def test_tmdb_quota_error(self):
        """Test TMDB handles quota error."""
        with patch('cineman.tools.tmdb.TMDB_API_KEY', 'test_key'):
            with patch('cineman.tools.tmdb._get_tmdb_client') as mock_client_getter:
                mock_client = Mock()
                mock_client.get.side_effect = QuotaError("Rate limit exceeded", 429)
                mock_client_getter.return_value = mock_client
                
                result = get_movie_poster_core("Inception")
                
                assert result["status"] == "quota_error"
                assert result["error_type"] == "quota"
    
    def test_tmdb_transient_error(self):
        """Test TMDB handles transient error."""
        with patch('cineman.tools.tmdb.TMDB_API_KEY', 'test_key'):
            with patch('cineman.tools.tmdb._get_tmdb_client') as mock_client_getter:
                mock_client = Mock()
                mock_client.get.side_effect = TransientError("Connection timeout", None)
                mock_client_getter.return_value = mock_client
                
                result = get_movie_poster_core("Inception")
                
                assert result["status"] == "error"
                assert result["error_type"] == "transient"
    
    def test_tmdb_no_api_key(self, monkeypatch):
        """Test TMDB handles missing API key."""
        monkeypatch.setenv("TMDB_API_KEY", "")
        
        # Need to reload the module to pick up the env change
        # For this test, we'll just call with a mocked env check
        with patch('cineman.tools.tmdb.TMDB_API_KEY', None):
            result = get_movie_poster_core("Inception")
            
            assert result["status"] == "error"
            assert "not configured" in result["error"].lower()


class TestOMDbToolIntegration:
    """Test OMDb tool integration with MovieDataClient."""
    
    def test_successful_omdb_search(self):
        """Test successful OMDb movie search."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Response": "True",
            "Title": "Inception",
            "Year": "2010",
            "Director": "Christopher Nolan",
            "imdbRating": "8.8",
            "Poster": "https://example.com/poster.jpg",
            "Ratings": [
                {"Source": "Internet Movie Database", "Value": "8.8/10"},
                {"Source": "Rotten Tomatoes", "Value": "87%"}
            ]
        }
        
        with patch('cineman.tools.omdb.OMDB_API_KEY', 'test_key'):
            with patch('cineman.tools.omdb._get_omdb_client') as mock_client_getter:
                mock_client = Mock()
                mock_client.get.return_value = mock_response
                mock_client.max_retries = 3
                mock_client_getter.return_value = mock_client
                
                result = fetch_omdb_data_core("Inception")
                
                assert result["status"] == "success"
                assert result["Title"] == "Inception"
                assert result["Year"] == "2010"
                assert result["Director"] == "Christopher Nolan"
                assert result["IMDb_Rating"] == "8.8"
                assert result["Rotten_Tomatoes"] == "87%"
    
    def test_omdb_not_found(self):
        """Test OMDb returns not found for unknown movie."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Response": "False",
            "Error": "Movie not found!"
        }
        
        with patch('cineman.tools.omdb.OMDB_API_KEY', 'test_key'):
            with patch('cineman.tools.omdb._get_omdb_client') as mock_client_getter:
                mock_client = Mock()
                mock_client.get.return_value = mock_response
                mock_client.max_retries = 3
                mock_client_getter.return_value = mock_client
                
                result = fetch_omdb_data_core("NonExistentMovie123456")
                
                assert result["status"] == "not_found"
    
    def test_omdb_auth_error(self):
        """Test OMDb handles authentication error."""
        # Clear cache to avoid cached results
        from cineman.tools.omdb import _clear_cache
        _clear_cache("omdb:testautherror")
        
        with patch('cineman.tools.omdb.OMDB_API_KEY', 'test_key'):
            with patch('cineman.tools.omdb._get_omdb_client') as mock_client_getter:
                mock_client = Mock()
                mock_client.get.side_effect = AuthError("Invalid API key", 403)
                mock_client.max_retries = 3
                mock_client_getter.return_value = mock_client
                
                result = fetch_omdb_data_core("TestAuthError")
                
                assert result["status"] == "forbidden"
                assert result["error_type"] == "auth"
    
    def test_omdb_quota_error(self):
        """Test OMDb handles quota error."""
        # Clear cache to avoid cached results
        from cineman.tools.omdb import _clear_cache
        _clear_cache("omdb:testquotaerror")
        
        with patch('cineman.tools.omdb.OMDB_API_KEY', 'test_key'):
            with patch('cineman.tools.omdb._get_omdb_client') as mock_client_getter:
                mock_client = Mock()
                mock_client.get.side_effect = QuotaError("Daily limit exceeded", 429)
                mock_client.max_retries = 3
                mock_client_getter.return_value = mock_client
                
                result = fetch_omdb_data_core("TestQuotaError")
                
                assert result["status"] == "quota_error"
                assert result["error_type"] == "quota"
    
    def test_omdb_transient_error(self):
        """Test OMDb handles transient error."""
        # Clear cache to avoid cached results
        from cineman.tools.omdb import _clear_cache
        _clear_cache("omdb:testtransienterror")
        
        with patch('cineman.tools.omdb.OMDB_API_KEY', 'test_key'):
            with patch('cineman.tools.omdb._get_omdb_client') as mock_client_getter:
                mock_client = Mock()
                mock_client.get.side_effect = TransientError("Connection timeout", None)
                mock_client.max_retries = 3
                mock_client_getter.return_value = mock_client
                
                result = fetch_omdb_data_core("TestTransientError")
                
                assert result["status"] == "error"
                assert result["error_type"] == "transient"
    
    def test_omdb_disabled(self, monkeypatch):
        """Test OMDb handles disabled state."""
        monkeypatch.setenv("OMDB_ENABLED", "0")
        
        with patch('cineman.tools.omdb.OMDB_ENABLED', False):
            result = fetch_omdb_data_core("Inception")
            
            assert result["status"] == "disabled"
    
    def test_omdb_no_api_key(self, monkeypatch):
        """Test OMDb handles missing API key."""
        with patch('cineman.tools.omdb.OMDB_API_KEY', None):
            result = fetch_omdb_data_core("Inception")
            
            assert result["status"] == "error"
            assert "not configured" in result["error"].lower()
    
    def test_omdb_caching(self):
        """Test OMDb uses caching correctly."""
        # Clear cache before test
        from cineman.tools.omdb import _clear_cache
        _clear_cache("omdb:inception")
        
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Response": "True",
            "Title": "Inception",
            "Year": "2010",
            "Director": "Christopher Nolan",
            "imdbRating": "8.8",
            "Poster": "https://example.com/poster.jpg",
            "Ratings": []
        }
        
        with patch('cineman.tools.omdb.OMDB_API_KEY', 'test_key'):
            with patch('cineman.tools.omdb._get_omdb_client') as mock_client_getter:
                mock_client = Mock()
                mock_client.get.return_value = mock_response
                mock_client.max_retries = 3
                mock_client_getter.return_value = mock_client
                
                # First call
                result1 = fetch_omdb_data_core("Inception")
                assert result1["status"] == "success"
                assert "_cached" not in result1
                
                # Second call should be cached
                result2 = fetch_omdb_data_core("Inception")
                assert result2["status"] == "success"
                assert result2.get("_cached") is True
                
                # Client should only be called once
                assert mock_client.get.call_count == 1


class TestParallelRequests:
    """Test parallel requests to ensure thread safety."""
    
    def test_parallel_tmdb_requests(self):
        """Test multiple parallel TMDB requests."""
        import threading
        
        results = []
        errors = []
        
        def search_movie(title):
            try:
                mock_response = Mock()
                mock_response.ok = True
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "results": [
                        {
                            "id": hash(title) % 10000,
                            "title": title,
                            "poster_path": f"/{title}.jpg",
                            "release_date": "2020-01-01",
                            "vote_average": 7.5,
                            "vote_count": 1000
                        }
                    ]
                }
                
                with patch('cineman.tools.tmdb.TMDB_API_KEY', 'test_key'):
                    with patch('cineman.tools.tmdb._get_tmdb_client') as mock_client_getter:
                        mock_client = Mock()
                        mock_client.get.return_value = mock_response
                        mock_client_getter.return_value = mock_client
                        
                        result = get_movie_poster_core(title)
                        results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        movies = [f"Movie{i}" for i in range(10)]
        for movie in movies:
            thread = threading.Thread(target=search_movie, args=(movie,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0
        assert len(results) == 10
        
        # Verify all results are successful
        for result in results:
            assert result["status"] == "success"
    
    def test_parallel_omdb_requests(self):
        """Test multiple parallel OMDb requests."""
        import threading
        
        results = []
        errors = []
        
        def search_movie(title):
            try:
                mock_response = Mock()
                mock_response.ok = True
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "Response": "True",
                    "Title": title,
                    "Year": "2020",
                    "Director": "Director",
                    "imdbRating": "7.5",
                    "Poster": f"https://example.com/{title}.jpg",
                    "Ratings": []
                }
                
                # Clear cache for this test
                from cineman.tools.omdb import _clear_cache
                _clear_cache(f"omdb:{title.lower()}")
                
                with patch('cineman.tools.omdb.OMDB_API_KEY', 'test_key'):
                    with patch('cineman.tools.omdb._get_omdb_client') as mock_client_getter:
                        mock_client = Mock()
                        mock_client.get.return_value = mock_response
                        mock_client.max_retries = 3
                        mock_client_getter.return_value = mock_client
                        
                        result = fetch_omdb_data_core(title)
                        results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        movies = [f"Movie{i}" for i in range(10)]
        for movie in movies:
            thread = threading.Thread(target=search_movie, args=(movie,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify no errors
        assert len(errors) == 0
        assert len(results) == 10
        
        # Verify all results are successful
        for result in results:
            assert result["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
