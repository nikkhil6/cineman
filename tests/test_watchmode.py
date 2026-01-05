"""
Unit tests for Watchmode streaming integration.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from cineman.tools.watchmode import (
    fetch_watchmode_data_core,
    get_dummy_streaming_data,
    _get_watchmode_client
)


class TestGetDummyStreamingData:
    """Test dummy streaming data generation."""
    
    def test_returns_dict_with_providers(self):
        """Should return dict with providers list."""
        result = get_dummy_streaming_data("Inception", 27205)
        assert isinstance(result, dict)
        assert "providers" in result
        assert isinstance(result["providers"], list)
        assert len(result["providers"]) == 4
    
    def test_generates_search_urls(self):
        """Should generate search URLs with encoded title."""
        result = get_dummy_streaming_data("The Matrix", 603)
        providers = result["providers"]
        
        # Check Netflix search URL
        netflix = next(p for p in providers if p["name"] == "Netflix")
        assert "search?q=The%20Matrix" in netflix["url"]
        
        # Check Amazon Prime search URL
        amazon = next(p for p in providers if p["name"] == "Amazon Prime")
        assert "s?k=The%20Matrix" in amazon["url"]
        assert "prime-instant-video" in amazon["url"]
    
    def test_handles_spaces_in_title(self):
        """Should properly URL-encode titles with spaces."""
        result = get_dummy_streaming_data("Back to the Future")
        providers = result["providers"]
        hulu = next(p for p in providers if p["name"] == "Hulu")
        assert "Back%20to%20the%20Future" in hulu["url"]
    
    def test_includes_free_options(self):
        """Should mark Pluto TV as free."""
        result = get_dummy_streaming_data("Movie")
        providers = result["providers"]
        pluto = next(p for p in providers if p["name"] == "Pluto TV")
        assert pluto["type"] == "free"


class TestFetchWatchmodeDataCore:
    """Test Watchmode API integration."""
    
    @patch('cineman.tools.watchmode.WATCHMODE_API_KEY', None)
    def test_returns_dummy_when_no_api_key(self):
        """Should return dummy data when no API key is configured."""
        result = fetch_watchmode_data_core("Inception", 27205)
        assert result["source"] == "dummy"
        assert len(result["providers"]) == 4
    
    @patch('cineman.tools.watchmode.WATCHMODE_API_KEY', 'test_key')
    @patch('cineman.tools.watchmode._get_watchmode_client')
    @patch('cineman.tools.watchmode.get_cache')
    def test_uses_correct_endpoint_format(self, mock_cache, mock_client):
        """Should use movie-{tmdb_id} endpoint format."""
        # Setup mocks
        mock_cache_instance = Mock()
        mock_cache_instance.get.return_value = None
        mock_cache.return_value = mock_cache_instance
        
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "name": "Netflix",
                "type": "sub",
                "web_url": "https://netflix.com/watch/123",
                "logo_url": "https://logo.url"
            }
        ]
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Execute
        result = fetch_watchmode_data_core("Inception", 27205)
        
        # Verify endpoint format
        call_args = mock_client_instance.get.call_args
        assert "movie-27205" in call_args[0][0]
        assert result["source"] == "watchmode"
    
    @patch('cineman.tools.watchmode.WATCHMODE_API_KEY', 'test_key')
    @patch('cineman.tools.watchmode._get_watchmode_client')
    @patch('cineman.tools.watchmode.get_cache')
    def test_deduplicates_providers(self, mock_cache, mock_client):
        """Should deduplicate multiple entries for same provider."""
        # Setup mocks
        mock_cache_instance = Mock()
        mock_cache_instance.get.return_value = None
        mock_cache.return_value = mock_cache_instance
        
        # Return multiple Netflix entries with different types
        mock_response = Mock()
        mock_response.json.return_value = [
            {"name": "Netflix", "type": "sub", "web_url": "https://netflix.com/sub"},
            {"name": "Netflix", "type": "purchase", "web_url": "https://netflix.com/buy"},
            {"name": "Hulu", "type": "free", "web_url": "https://hulu.com/free"},
            {"name": "Hulu", "type": "sub", "web_url": "https://hulu.com/sub"}
        ]
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Execute
        result = fetch_watchmode_data_core("Test Movie", 123)
        
        # Should have only 2 providers (Netflix and Hulu)
        assert len(result["providers"]) == 2
        
        # Netflix should be sub (priority 1) not purchase (priority 3)
        netflix = next(p for p in result["providers"] if p["name"] == "Netflix")
        assert "sub" in netflix["url"]
        
        # Hulu should be free (priority 0) not sub (priority 1)
        hulu = next(p for p in result["providers"] if p["name"] == "Hulu")
        assert "free" in hulu["url"]
    
    @patch('cineman.tools.watchmode.WATCHMODE_API_KEY', 'test_key')
    @patch('cineman.tools.watchmode._get_watchmode_client')
    @patch('cineman.tools.watchmode.get_cache')
    def test_filters_invalid_urls(self, mock_cache, mock_client):
        """Should filter out providers with invalid URLs."""
        # Setup mocks
        mock_cache_instance = Mock()
        mock_cache_instance.get.return_value = None
        mock_cache.return_value = mock_cache_instance
        
        mock_response = Mock()
        mock_response.json.return_value = [
            {"name": "Netflix", "type": "sub", "web_url": "https://netflix.com"},
            {"name": "InvalidProvider", "type": "sub", "web_url": None},
            {"name": "BadURL", "type": "sub", "web_url": "not-a-url"},
            {"name": "Hulu", "type": "sub", "web_url": "https://hulu.com"}
        ]
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Execute
        result = fetch_watchmode_data_core("Test Movie", 123)
        
        # Should only have 2 valid providers
        assert len(result["providers"]) == 2
        names = [p["name"] for p in result["providers"]]
        assert "Netflix" in names
        assert "Hulu" in names
        assert "InvalidProvider" not in names
        assert "BadURL" not in names
