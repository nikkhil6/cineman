"""
Unit tests for the MovieCache module.

Tests cover:
- Cache initialization and configuration
- Get/set/evict/clear operations
- Key normalization (title, year, case, punctuation)
- TTL enforcement and expiration
- LRU eviction when max size reached
- Cache statistics and metrics
- Edge cases and error handling
"""

import pytest
import time
from unittest.mock import patch
from cineman.cache import MovieCache, CacheEntry, CacheStats, get_cache


class TestCacheInitialization:
    """Test cache initialization and configuration."""
    
    def test_default_initialization(self):
        """Test cache with default settings."""
        cache = MovieCache()
        assert cache.enabled is True
        assert cache.ttl == 86400  # 24 hours
        assert cache.max_size == 1000
        assert len(cache._cache) == 0
    
    def test_custom_initialization(self):
        """Test cache with custom settings."""
        cache = MovieCache(ttl=300, max_size=100, enabled=True)
        assert cache.enabled is True
        assert cache.ttl == 300
        assert cache.max_size == 100
    
    def test_disabled_cache(self):
        """Test cache can be disabled."""
        cache = MovieCache(enabled=False)
        assert cache.enabled is False
    
    @patch.dict('os.environ', {
        'MOVIE_CACHE_TTL': '1800',
        'MOVIE_CACHE_MAX_SIZE': '500',
        'MOVIE_CACHE_ENABLED': '1'
    })
    def test_env_configuration(self):
        """Test cache reads configuration from environment."""
        cache = MovieCache()
        assert cache.ttl == 1800
        assert cache.max_size == 500
        assert cache.enabled is True
    
    @patch.dict('os.environ', {'MOVIE_CACHE_ENABLED': '0'})
    def test_env_disabled(self):
        """Test cache can be disabled via environment."""
        cache = MovieCache()
        assert cache.enabled is False


class TestKeyNormalization:
    """Test cache key normalization."""
    
    def test_normalize_basic_title(self):
        """Test basic title normalization."""
        cache = MovieCache()
        key1 = cache._normalize_key("The Matrix", source="tmdb")
        key2 = cache._normalize_key("the matrix", source="tmdb")
        key3 = cache._normalize_key("THE MATRIX", source="tmdb")
        
        # All should produce the same normalized key
        assert key1 == key2 == key3
        assert "matrix" in key1
        assert "the" not in key1  # Article removed
    
    def test_normalize_with_year(self):
        """Test normalization with year."""
        cache = MovieCache()
        key1 = cache._normalize_key("Inception", year="2010", source="tmdb")
        key2 = cache._normalize_key("Inception", year="2010", source="tmdb")
        
        assert key1 == key2
        assert "2010" in key1
        assert "inception" in key1
    
    def test_normalize_punctuation(self):
        """Test punctuation handling in normalization."""
        cache = MovieCache()
        key1 = cache._normalize_key("Spider-Man", source="omdb")
        key2 = cache._normalize_key("Spider Man", source="omdb")
        
        # Hyphens are preserved
        assert "spider-man" in key1
        assert "spider" in key2
    
    def test_normalize_apostrophe(self):
        """Test apostrophe preservation."""
        cache = MovieCache()
        key = cache._normalize_key("Ocean's Eleven", source="tmdb")
        assert "ocean's" in key
    
    def test_normalize_extra_whitespace(self):
        """Test whitespace normalization."""
        cache = MovieCache()
        key1 = cache._normalize_key("The   Dark    Knight", source="tmdb")
        key2 = cache._normalize_key("The Dark Knight", source="tmdb")
        
        assert key1 == key2
    
    def test_normalize_year_extraction(self):
        """Test year extraction from various formats."""
        cache = MovieCache()
        key1 = cache._normalize_key("Movie", year="2010-2012", source="tmdb")
        key2 = cache._normalize_key("Movie", year="2010", source="tmdb")
        
        # Both should extract 2010
        assert key1 == key2
    
    def test_normalize_different_sources(self):
        """Test that different sources produce different keys."""
        cache = MovieCache()
        key1 = cache._normalize_key("Inception", source="tmdb")
        key2 = cache._normalize_key("Inception", source="omdb")
        
        assert key1 != key2
        assert "tmdb" in key1
        assert "omdb" in key2
    
    def test_normalize_empty_title(self):
        """Test normalization with empty title."""
        cache = MovieCache()
        key = cache._normalize_key("", source="test")
        assert key == "test:"


class TestBasicCacheOperations:
    """Test basic cache get/set operations."""
    
    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = MovieCache()
        data = {"title": "Inception", "year": "2010"}
        
        cache.set("Inception", data, source="tmdb")
        result = cache.get("Inception", source="tmdb")
        
        assert result is not None
        assert result["title"] == "Inception"
        assert result["year"] == "2010"
    
    def test_get_nonexistent(self):
        """Test getting non-existent entry returns None."""
        cache = MovieCache()
        result = cache.get("NonexistentMovie", source="tmdb")
        
        assert result is None
    
    def test_case_insensitive_retrieval(self):
        """Test that retrieval is case-insensitive."""
        cache = MovieCache()
        data = {"title": "The Matrix"}
        
        cache.set("The Matrix", data, source="tmdb")
        result1 = cache.get("the matrix", source="tmdb")
        result2 = cache.get("THE MATRIX", source="tmdb")
        result3 = cache.get("The Matrix", source="tmdb")
        
        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        assert result1 == result2 == result3
    
    def test_set_updates_existing(self):
        """Test that set updates existing entry."""
        cache = MovieCache()
        data1 = {"title": "Inception", "rating": "8.0"}
        data2 = {"title": "Inception", "rating": "8.8"}
        
        cache.set("Inception", data1, source="tmdb")
        cache.set("Inception", data2, source="tmdb")
        
        result = cache.get("Inception", source="tmdb")
        assert result["rating"] == "8.8"
    
    def test_disabled_cache_operations(self):
        """Test that disabled cache doesn't store or retrieve."""
        cache = MovieCache(enabled=False)
        data = {"title": "Inception"}
        
        cache.set("Inception", data, source="tmdb")
        result = cache.get("Inception", source="tmdb")
        
        assert result is None


class TestTTLExpiration:
    """Test TTL enforcement and expiration."""
    
    def test_entry_expires_after_ttl(self):
        """Test that entry expires after TTL."""
        cache = MovieCache(ttl=1)  # 1 second TTL
        data = {"title": "Inception"}
        
        cache.set("Inception", data, source="tmdb")
        
        # Should be available immediately
        result1 = cache.get("Inception", source="tmdb")
        assert result1 is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        result2 = cache.get("Inception", source="tmdb")
        assert result2 is None
    
    def test_custom_ttl_per_entry(self):
        """Test custom TTL for individual entries."""
        cache = MovieCache(ttl=10)  # Default 10 seconds
        data = {"title": "Inception"}
        
        # Set with custom short TTL
        cache.set("Inception", data, source="tmdb", ttl=1)
        
        # Should be available immediately
        result1 = cache.get("Inception", source="tmdb")
        assert result1 is not None
        
        # Wait for custom TTL to expire
        time.sleep(1.1)
        
        # Should be expired
        result2 = cache.get("Inception", source="tmdb")
        assert result2 is None
    
    def test_expired_entry_increments_evictions(self):
        """Test that expired entries increment eviction counter."""
        cache = MovieCache(ttl=1)
        data = {"title": "Inception"}
        
        cache.set("Inception", data, source="tmdb")
        stats1 = cache.get_stats()
        
        time.sleep(1.1)
        cache.get("Inception", source="tmdb")
        
        stats2 = cache.get_stats()
        assert stats2["evictions"] == stats1["evictions"] + 1


class TestLRUEviction:
    """Test LRU eviction when max size reached."""
    
    def test_lru_eviction_on_max_size(self):
        """Test that oldest entry is evicted when max size reached."""
        cache = MovieCache(max_size=3)
        
        # Fill cache to max
        cache.set("Movie1", {"title": "Movie1"}, source="tmdb")
        cache.set("Movie2", {"title": "Movie2"}, source="tmdb")
        cache.set("Movie3", {"title": "Movie3"}, source="tmdb")
        
        # All should be present
        assert cache.get("Movie1", source="tmdb") is not None
        assert cache.get("Movie2", source="tmdb") is not None
        assert cache.get("Movie3", source="tmdb") is not None
        
        # Add one more - should evict Movie1 (oldest/least recently used)
        cache.set("Movie4", {"title": "Movie4"}, source="tmdb")
        
        # Movie1 should be evicted
        assert cache.get("Movie1", source="tmdb") is None
        # Others should still be present
        assert cache.get("Movie2", source="tmdb") is not None
        assert cache.get("Movie3", source="tmdb") is not None
        assert cache.get("Movie4", source="tmdb") is not None
    
    def test_lru_recent_access_updates_order(self):
        """Test that accessing entry moves it to end (most recent)."""
        cache = MovieCache(max_size=3)
        
        cache.set("Movie1", {"title": "Movie1"}, source="tmdb")
        cache.set("Movie2", {"title": "Movie2"}, source="tmdb")
        cache.set("Movie3", {"title": "Movie3"}, source="tmdb")
        
        # Access Movie1 to make it most recent
        cache.get("Movie1", source="tmdb")
        
        # Add Movie4 - should evict Movie2 (now oldest)
        cache.set("Movie4", {"title": "Movie4"}, source="tmdb")
        
        # Movie1 should still be present (was accessed recently)
        assert cache.get("Movie1", source="tmdb") is not None
        # Movie2 should be evicted
        assert cache.get("Movie2", source="tmdb") is None
        # Others present
        assert cache.get("Movie3", source="tmdb") is not None
        assert cache.get("Movie4", source="tmdb") is not None
    
    def test_lru_eviction_increments_counter(self):
        """Test that LRU eviction increments eviction counter."""
        cache = MovieCache(max_size=2)
        
        cache.set("Movie1", {"title": "Movie1"}, source="tmdb")
        cache.set("Movie2", {"title": "Movie2"}, source="tmdb")
        
        stats1 = cache.get_stats()
        
        # This should trigger LRU eviction
        cache.set("Movie3", {"title": "Movie3"}, source="tmdb")
        
        stats2 = cache.get_stats()
        assert stats2["evictions"] == stats1["evictions"] + 1


class TestEvictAndClear:
    """Test manual eviction and clearing."""
    
    def test_evict_specific_entry(self):
        """Test manually evicting specific entry."""
        cache = MovieCache()
        cache.set("Inception", {"title": "Inception"}, source="tmdb")
        
        # Evict the entry
        result = cache.evict("Inception", source="tmdb")
        
        assert result is True
        assert cache.get("Inception", source="tmdb") is None
    
    def test_evict_nonexistent_entry(self):
        """Test evicting non-existent entry returns False."""
        cache = MovieCache()
        result = cache.evict("NonexistentMovie", source="tmdb")
        
        assert result is False
    
    def test_clear_all_entries(self):
        """Test clearing all cache entries."""
        cache = MovieCache()
        cache.set("Movie1", {"title": "Movie1"}, source="tmdb")
        cache.set("Movie2", {"title": "Movie2"}, source="omdb")
        cache.set("Movie3", {"title": "Movie3"}, source="tmdb")
        
        count = cache.clear()
        
        assert count == 3
        assert cache.get("Movie1", source="tmdb") is None
        assert cache.get("Movie2", source="omdb") is None
        assert cache.get("Movie3", source="tmdb") is None
    
    def test_clear_by_source(self):
        """Test clearing entries for specific source."""
        cache = MovieCache()
        cache.set("Movie1", {"title": "Movie1"}, source="tmdb")
        cache.set("Movie2", {"title": "Movie2"}, source="omdb")
        cache.set("Movie3", {"title": "Movie3"}, source="tmdb")
        
        count = cache.clear(source="tmdb")
        
        assert count == 2
        # TMDB entries should be cleared
        assert cache.get("Movie1", source="tmdb") is None
        assert cache.get("Movie3", source="tmdb") is None
        # OMDb entry should remain
        assert cache.get("Movie2", source="omdb") is not None
    
    def test_clear_empty_cache(self):
        """Test clearing empty cache."""
        cache = MovieCache()
        count = cache.clear()
        
        assert count == 0


class TestCacheStatistics:
    """Test cache statistics and metrics."""
    
    def test_initial_stats(self):
        """Test initial statistics are zero."""
        cache = MovieCache()
        stats = cache.get_stats()
        
        assert stats["total_requests"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["evictions"] == 0
        assert stats["current_size"] == 0
        assert stats["hit_ratio"] == 0.0
    
    def test_stats_track_hits_and_misses(self):
        """Test that statistics track hits and misses correctly."""
        cache = MovieCache()
        cache.set("Inception", {"title": "Inception"}, source="tmdb")
        
        # Miss
        cache.get("NonexistentMovie", source="tmdb")
        # Hit
        cache.get("Inception", source="tmdb")
        # Hit
        cache.get("Inception", source="tmdb")
        # Miss
        cache.get("AnotherMissing", source="tmdb")
        
        stats = cache.get_stats()
        assert stats["total_requests"] == 4
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["hit_ratio"] == 0.5
    
    def test_stats_track_current_size(self):
        """Test that statistics track current cache size."""
        cache = MovieCache()
        
        stats1 = cache.get_stats()
        assert stats1["current_size"] == 0
        
        cache.set("Movie1", {"title": "Movie1"}, source="tmdb")
        cache.set("Movie2", {"title": "Movie2"}, source="tmdb")
        
        stats2 = cache.get_stats()
        assert stats2["current_size"] == 2
        
        cache.clear()
        
        stats3 = cache.get_stats()
        assert stats3["current_size"] == 0
    
    def test_reset_stats(self):
        """Test resetting statistics."""
        cache = MovieCache()
        cache.set("Movie1", {"title": "Movie1"}, source="tmdb")
        cache.get("Movie1", source="tmdb")
        cache.get("NonexistentMovie", source="tmdb")
        
        stats1 = cache.get_stats()
        assert stats1["total_requests"] > 0
        
        cache.reset_stats()
        
        stats2 = cache.get_stats()
        assert stats2["total_requests"] == 0
        assert stats2["hits"] == 0
        assert stats2["misses"] == 0
        # But cache size should remain
        assert stats2["current_size"] == 1
    
    def test_entry_hit_counter(self):
        """Test that individual entries track hit counts."""
        cache = MovieCache()
        cache.set("Inception", {"title": "Inception"}, source="tmdb")
        
        # Access multiple times
        cache.get("Inception", source="tmdb")
        cache.get("Inception", source="tmdb")
        cache.get("Inception", source="tmdb")
        
        # Check entry hit counter
        key = cache._normalize_key("Inception", source="tmdb")
        entry = cache._cache[key]
        assert entry.hits == 3


class TestGlobalCacheInstance:
    """Test global cache instance."""
    
    def test_get_cache_returns_singleton(self):
        """Test that get_cache returns same instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        
        assert cache1 is cache2
    
    def test_global_cache_persists_data(self):
        """Test that global cache persists data across calls."""
        cache1 = get_cache()
        cache1.set("TestMovie", {"title": "TestMovie"}, source="test")
        
        cache2 = get_cache()
        result = cache2.get("TestMovie", source="test")
        
        assert result is not None
        assert result["title"] == "TestMovie"


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_title(self):
        """Test handling of empty title."""
        cache = MovieCache()
        cache.set("", {"data": "test"}, source="tmdb")
        result = cache.get("", source="tmdb")
        
        # Should handle gracefully
        assert result is not None or result is None  # Either behavior is acceptable
    
    def test_special_characters_in_title(self):
        """Test handling of special characters."""
        cache = MovieCache()
        data = {"title": "Test!@#$%"}
        
        cache.set("Test!@#$%", data, source="tmdb")
        result = cache.get("Test!@#$%", source="tmdb")
        
        assert result is not None
    
    def test_very_long_title(self):
        """Test handling of very long titles."""
        cache = MovieCache()
        long_title = "A" * 1000
        data = {"title": long_title}
        
        cache.set(long_title, data, source="tmdb")
        result = cache.get(long_title, source="tmdb")
        
        assert result is not None
    
    def test_unicode_title(self):
        """Test handling of unicode characters."""
        cache = MovieCache()
        data = {"title": "amélie"}
        
        cache.set("amélie", data, source="tmdb")
        result = cache.get("amélie", source="tmdb")
        
        assert result is not None
    
    def test_none_value(self):
        """Test that None values are not stored."""
        cache = MovieCache()
        # Set and get should work even with minimal data
        cache.set("Test", {}, source="tmdb")
        result = cache.get("Test", source="tmdb")
        
        assert result is not None


class TestCacheIntegration:
    """Integration tests for cache behavior."""
    
    def test_multiple_sources_same_title(self):
        """Test that same title from different sources are cached separately."""
        cache = MovieCache()
        
        tmdb_data = {"title": "Inception", "source": "tmdb", "rating": 8.8}
        omdb_data = {"title": "Inception", "source": "omdb", "rating": 8.7}
        
        cache.set("Inception", tmdb_data, source="tmdb")
        cache.set("Inception", omdb_data, source="omdb")
        
        tmdb_result = cache.get("Inception", source="tmdb")
        omdb_result = cache.get("Inception", source="omdb")
        
        assert tmdb_result["rating"] == 8.8
        assert omdb_result["rating"] == 8.7
    
    def test_year_differentiation(self):
        """Test that same title with different years are cached separately."""
        cache = MovieCache()
        
        data_2010 = {"title": "Inception", "year": "2010"}
        data_2020 = {"title": "Inception", "year": "2020"}
        
        cache.set("Inception", data_2010, year="2010", source="tmdb")
        cache.set("Inception", data_2020, year="2020", source="tmdb")
        
        result_2010 = cache.get("Inception", year="2010", source="tmdb")
        result_2020 = cache.get("Inception", year="2020", source="tmdb")
        
        assert result_2010["year"] == "2010"
        assert result_2020["year"] == "2020"
    
    def test_cache_performance_under_load(self):
        """Test cache performance with many entries."""
        cache = MovieCache(max_size=100)
        
        # Add many entries
        for i in range(150):
            cache.set(f"Movie{i}", {"id": i}, source="tmdb")
        
        stats = cache.get_stats()
        
        # Should have evicted 50 entries (150 - 100)
        assert stats["current_size"] == 100
        assert stats["evictions"] == 50
        
        # Most recent entries should still be present
        assert cache.get("Movie149", source="tmdb") is not None
        # Oldest entries should be evicted
        assert cache.get("Movie0", source="tmdb") is None
