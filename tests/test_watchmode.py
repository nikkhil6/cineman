"""
Unit tests for Watchmode streaming sources API client.

Tests cover:
- TMDB watch providers fallback
- Rate limiting
- Platform info extraction
- Caching behavior
- Error handling
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestWatchmodeModule:
    """Test suite for Watchmode streaming sources."""
    
    @pytest.fixture(autouse=True)
    def reset_watchmode_state(self, monkeypatch):
        """Reset watchmode state before each test."""
        # Set test environment
        monkeypatch.setenv("TMDB_API_KEY", "test_key")
        monkeypatch.setenv("WATCHMODE_API_KEY", "")  # Disable by default
        monkeypatch.setenv("WATCHMODE_ENABLED", "0")  # Disable by default
        
        # Import and reset module state
        import cineman.tools.watchmode as watchmode
        watchmode._watchmode_usage = {"count": 0, "reset_date": None}
        watchmode._watchmode_client = None
        watchmode._tmdb_watch_client = None
        
        yield
        
        # Cleanup
        watchmode._watchmode_usage = {"count": 0, "reset_date": None}
    
    def test_platform_info_known_platform(self):
        """Test platform info extraction for known platforms."""
        from cineman.tools.watchmode import _get_platform_info
        
        result = _get_platform_info("Netflix")
        assert result["name"] == "Netflix"
        assert result["icon"] == "🔴"
        assert result["color"] == "#E50914"
    
    def test_platform_info_unknown_platform(self):
        """Test platform info extraction for unknown platforms."""
        from cineman.tools.watchmode import _get_platform_info
        
        result = _get_platform_info("UnknownStreamingService")
        assert result["name"] == "UnknownStreamingService"
        assert result["icon"] == "📺"  # Default icon
    
    def test_platform_name_normalization(self):
        """Test platform name normalization."""
        from cineman.tools.watchmode import _normalize_platform_name
        
        assert _normalize_platform_name("Netflix") == "netflix"
        assert _normalize_platform_name("Amazon Prime") == "amazon_prime"
        assert _normalize_platform_name("Disney+") == "disney_plus"
        assert _normalize_platform_name("HBO-Max") == "hbo_max"
    
    def test_check_watchmode_rate_limit_initial(self):
        """Test rate limit check when first called."""
        from cineman.tools.watchmode import _check_watchmode_rate_limit
        
        assert _check_watchmode_rate_limit() is True
    
    def test_check_watchmode_rate_limit_exceeded(self, monkeypatch):
        """Test rate limit check when limit exceeded."""
        import cineman.tools.watchmode as watchmode
        
        # Set to max limit
        monkeypatch.setattr(watchmode, "WATCHMODE_MONTHLY_LIMIT", 10)
        watchmode._watchmode_usage["count"] = 10
        watchmode._watchmode_usage["reset_date"] = datetime.now() + timedelta(days=30)
        
        assert watchmode._check_watchmode_rate_limit() is False
    
    def test_check_watchmode_rate_limit_reset(self, monkeypatch):
        """Test rate limit resets when date passes."""
        import cineman.tools.watchmode as watchmode
        
        # Set to exceeded but reset date is in the past
        monkeypatch.setattr(watchmode, "WATCHMODE_MONTHLY_LIMIT", 10)
        watchmode._watchmode_usage["count"] = 10
        watchmode._watchmode_usage["reset_date"] = datetime.now() - timedelta(days=1)
        
        # Should reset and allow
        assert watchmode._check_watchmode_rate_limit() is True
        assert watchmode._watchmode_usage["count"] == 0
    
    def test_increment_watchmode_usage(self):
        """Test incrementing usage counter."""
        import cineman.tools.watchmode as watchmode
        
        watchmode._increment_watchmode_usage()
        assert watchmode._watchmode_usage["count"] == 1
        
        watchmode._increment_watchmode_usage()
        assert watchmode._watchmode_usage["count"] == 2
    
    def test_get_watchmode_usage_stats(self):
        """Test getting usage stats."""
        import cineman.tools.watchmode as watchmode
        from cineman.tools.watchmode import get_watchmode_usage_stats
        
        watchmode._watchmode_usage["count"] = 50
        watchmode._watchmode_usage["reset_date"] = datetime(2025, 12, 1)
        
        stats = get_watchmode_usage_stats()
        assert stats["count"] == 50
        assert stats["limit"] == watchmode.WATCHMODE_MONTHLY_LIMIT
        assert stats["remaining"] == watchmode.WATCHMODE_MONTHLY_LIMIT - 50
        assert stats["reset_date"] == "2025-12-01T00:00:00"
    
    def test_get_streaming_sources_no_tmdb_id(self):
        """Test streaming sources returns error without TMDB ID."""
        from cineman.tools.watchmode import get_streaming_sources
        
        result = get_streaming_sources("Inception", tmdb_id=None)
        assert result["status"] == "error"
        assert "TMDB ID required" in result["error"]
    
    def test_fetch_tmdb_watch_providers_success(self, monkeypatch):
        """Test TMDB watch providers fetch success."""
        from cineman.tools.watchmode import _fetch_tmdb_watch_providers
        from cineman.api_client import MovieDataClient
        
        # Mock the client
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": 27205,
            "results": {
                "US": {
                    "link": "https://www.themoviedb.org/movie/27205/watch",
                    "flatrate": [
                        {
                            "provider_id": 8,
                            "provider_name": "Netflix",
                            "logo_path": "/netflix_logo.png"
                        }
                    ],
                    "rent": [
                        {
                            "provider_id": 2,
                            "provider_name": "Apple TV",
                            "logo_path": "/apple_logo.png"
                        }
                    ],
                    "buy": []
                }
            }
        }
        
        with patch.object(MovieDataClient, 'get', return_value=mock_response):
            result = _fetch_tmdb_watch_providers(27205, "Inception", "US")
            
            assert result["status"] == "success"
            assert result["source"] == "tmdb"
            assert len(result["platforms"]["subscription"]) == 1
            assert result["platforms"]["subscription"][0]["name"] == "Netflix"
            assert len(result["platforms"]["rent"]) == 1
    
    def test_fetch_tmdb_watch_providers_not_found(self, monkeypatch):
        """Test TMDB watch providers when no providers available."""
        from cineman.tools.watchmode import _fetch_tmdb_watch_providers
        from cineman.api_client import MovieDataClient
        
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": 27205,
            "results": {}  # No results
        }
        
        with patch.object(MovieDataClient, 'get', return_value=mock_response):
            result = _fetch_tmdb_watch_providers(27205, "Inception", "US")
            
            assert result["status"] == "not_found"
    
    def test_get_streaming_sources_uses_cache(self, monkeypatch):
        """Test that streaming sources uses cache."""
        from cineman.tools.watchmode import get_streaming_sources
        from cineman.cache import get_cache
        
        # Pre-populate cache
        cache = get_cache()
        cached_data = {
            "status": "success",
            "source": "tmdb",
            "platforms": {"subscription": [], "rent": [], "buy": [], "free": [], "all": []},
            "attribution": "Cached data"
        }
        cache.set("Inception:27205:US", cached_data, source="streaming")
        
        result = get_streaming_sources("Inception", tmdb_id=27205, region="US")
        
        # Should return cached data
        assert result["attribution"] == "Cached data"
    
    def test_get_streaming_sources_fallback_to_tmdb(self, monkeypatch):
        """Test that streaming sources falls back to TMDB when Watchmode not configured."""
        from cineman.tools.watchmode import get_streaming_sources, _fetch_tmdb_watch_providers
        from cineman.api_client import MovieDataClient
        
        # Mock TMDB response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": 27205,
            "results": {
                "US": {
                    "link": "https://www.themoviedb.org/movie/27205/watch",
                    "flatrate": [
                        {"provider_id": 8, "provider_name": "Netflix", "logo_path": "/netflix.png"}
                    ],
                    "rent": [],
                    "buy": []
                }
            }
        }
        
        with patch.object(MovieDataClient, 'get', return_value=mock_response):
            result = get_streaming_sources(
                "Inception", 
                tmdb_id=27205, 
                region="US",
                use_cache=False
            )
            
            assert result["status"] == "success"
            assert result["source"] == "tmdb"
            assert len(result["platforms"]["subscription"]) == 1


class TestWatchmodeAPIClient:
    """Test Watchmode API client functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_watchmode(self, monkeypatch):
        """Setup Watchmode with API key enabled."""
        monkeypatch.setenv("WATCHMODE_API_KEY", "test_watchmode_key")
        monkeypatch.setenv("WATCHMODE_ENABLED", "1")
        monkeypatch.setenv("TMDB_API_KEY", "test_key")
        
        import cineman.tools.watchmode as watchmode
        watchmode.WATCHMODE_API_KEY = "test_watchmode_key"
        watchmode.WATCHMODE_ENABLED = True
        watchmode._watchmode_usage = {"count": 0, "reset_date": None}
        watchmode._watchmode_client = None
        
        yield
        
        watchmode.WATCHMODE_API_KEY = None
        watchmode.WATCHMODE_ENABLED = False
        watchmode._watchmode_usage = {"count": 0, "reset_date": None}
    
    def test_fetch_watchmode_sources_success(self):
        """Test successful Watchmode API fetch."""
        from cineman.tools.watchmode import _fetch_watchmode_sources
        from cineman.api_client import MovieDataClient
        
        # Mock search response
        search_response = Mock()
        search_response.ok = True
        search_response.json.return_value = {
            "title_results": [
                {"id": 123456, "name": "Inception"}
            ]
        }
        
        # Mock sources response
        sources_response = Mock()
        sources_response.ok = True
        sources_response.json.return_value = [
            {
                "name": "Netflix",
                "type": "sub",
                "web_url": "https://netflix.com/watch/inception",
                "region": "US"
            },
            {
                "name": "Amazon Prime Video",
                "type": "rent",
                "web_url": "https://amazon.com/video/inception",
                "price": "$3.99",
                "region": "US"
            }
        ]
        
        with patch.object(MovieDataClient, 'get', side_effect=[search_response, sources_response]):
            result = _fetch_watchmode_sources(27205, "Inception")
            
            assert result["status"] == "success"
            assert result["source"] == "watchmode"
            assert len(result["platforms"]["subscription"]) == 1
            assert len(result["platforms"]["rent"]) == 1
            assert result["watchmode_id"] == 123456
    
    def test_fetch_watchmode_sources_not_found(self):
        """Test Watchmode when title not found."""
        from cineman.tools.watchmode import _fetch_watchmode_sources
        from cineman.api_client import MovieDataClient
        
        # Mock search response with no results
        search_response = Mock()
        search_response.ok = True
        search_response.json.return_value = {
            "title_results": []
        }
        
        with patch.object(MovieDataClient, 'get', return_value=search_response):
            result = _fetch_watchmode_sources(99999, "NonexistentMovie")
            
            assert result["status"] == "not_found"
    
    def test_fetch_watchmode_sources_rate_limited(self, monkeypatch):
        """Test Watchmode when rate limited."""
        import cineman.tools.watchmode as watchmode
        from cineman.tools.watchmode import _fetch_watchmode_sources
        
        # Set usage to max
        monkeypatch.setattr(watchmode, "WATCHMODE_MONTHLY_LIMIT", 10)
        watchmode._watchmode_usage["count"] = 10
        watchmode._watchmode_usage["reset_date"] = datetime.now() + timedelta(days=30)
        
        result = _fetch_watchmode_sources(27205, "Inception")
        
        assert result["status"] == "quota_error"
        assert "Monthly Watchmode API limit reached" in result["error"]


class TestStreamingPlatformIcons:
    """Test streaming platform icon mappings."""
    
    def test_all_major_platforms_have_icons(self):
        """Test that all major streaming platforms have icon mappings."""
        from cineman.tools.watchmode import STREAMING_PLATFORM_ICONS
        
        major_platforms = [
            "netflix", "amazon_prime", "disney_plus", "hulu", 
            "hbo_max", "apple_tv_plus", "peacock", "paramount_plus"
        ]
        
        for platform in major_platforms:
            assert platform in STREAMING_PLATFORM_ICONS or \
                   any(platform in key for key in STREAMING_PLATFORM_ICONS.keys())
    
    def test_platform_icon_structure(self):
        """Test that platform icon entries have required fields."""
        from cineman.tools.watchmode import STREAMING_PLATFORM_ICONS
        
        for key, info in STREAMING_PLATFORM_ICONS.items():
            assert "name" in info
            assert "icon" in info
            assert "color" in info
            assert info["color"].startswith("#")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
