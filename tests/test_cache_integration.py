"""
Integration tests for cache functionality.

These tests focus on validating that:
1. Cache is properly integrated with tools
2. Cache improves performance by reducing API calls
3. Cache handles edge cases correctly

Note: Most detailed cache behavior is tested in test_cache.py unit tests.
These integration tests validate the end-to-end scenarios.
"""

import pytest
import time
from cineman.cache import get_cache, MovieCache


class TestCacheBasicIntegration:
    """Basic integration tests for cache."""
    
    def test_cache_stores_and_retrieves_data(self):
        """Test that cache can store and retrieve data."""
        cache = MovieCache()
        
        data = {"title": "Inception", "year": "2010", "rating": 8.8}
        cache.set("Inception", data, source="test")
        
        result = cache.get("Inception", source="test")
        
        assert result is not None
        assert result["title"] == "Inception"
        assert result["year"] == "2010"
        assert result["rating"] == 8.8
    
    def test_cache_respects_source_separation(self):
        """Test that different sources maintain separate caches."""
        cache = MovieCache()
        
        tmdb_data = {"source": "tmdb", "rating": 8.8}
        omdb_data = {"source": "omdb", "rating": 8.7}
        
        cache.set("Inception", tmdb_data, source="tmdb")
        cache.set("Inception", omdb_data, source="omdb")
        
        tmdb_result = cache.get("Inception", source="tmdb")
        omdb_result = cache.get("Inception", source="omdb")
        
        assert tmdb_result["source"] == "tmdb"
        assert omdb_result["source"] == "omdb"
        assert tmdb_result["rating"] == 8.8
        assert omdb_result["rating"] == 8.7
    
    def test_cache_expiration_workflow(self):
        """Test that expired entries are properly evicted."""
        cache = MovieCache(ttl=1)  # 1 second TTL
        
        data = {"title": "Test Movie"}
        cache.set("Test", data, source="test")
        
        # Should be available immediately
        result1 = cache.get("Test", source="test")
        assert result1 is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        result2 = cache.get("Test", source="test")
        assert result2 is None
    
    def test_cache_hit_ratio_tracking(self):
        """Test that cache tracks hit ratio correctly."""
        cache = MovieCache()
        
        # Store some data
        for i in range(5):
            cache.set(f"Movie{i}", {"id": i}, source="test")
        
        # Half hits, half misses
        for i in range(5):
            cache.get(f"Movie{i}", source="test")  # Hits
        for i in range(5, 10):
            cache.get(f"Movie{i}", source="test")  # Misses
        
        stats = cache.get_stats()
        assert stats["hits"] == 5
        assert stats["misses"] == 5
        assert stats["hit_ratio"] == 0.5
    
    def test_cache_lru_eviction_workflow(self):
        """Test LRU eviction when cache is full."""
        cache = MovieCache(max_size=3)
        
        # Fill cache
        cache.set("Movie1", {"id": 1}, source="test")
        cache.set("Movie2", {"id": 2}, source="test")
        cache.set("Movie3", {"id": 3}, source="test")
        
        # Access Movie1 to make it recent
        cache.get("Movie1", source="test")
        
        # Add new movie - should evict Movie2 (least recently used)
        cache.set("Movie4", {"id": 4}, source="test")
        
        # Movie1 should still be there
        assert cache.get("Movie1", source="test") is not None
        # Movie2 should be evicted
        assert cache.get("Movie2", source="test") is None
        # Movie3 and Movie4 should be there
        assert cache.get("Movie3", source="test") is not None
        assert cache.get("Movie4", source="test") is not None


class TestCachePerformanceScenarios:
    """Test performance-related cache scenarios."""
    
    def test_repeated_access_pattern(self):
        """Test cache improves performance for repeated accesses."""
        cache = MovieCache()
        
        # Simulate popular movies being accessed multiple times
        popular_movies = ["Inception", "The Matrix", "Interstellar"]
        
        # Store movies
        for movie in popular_movies:
            cache.set(movie, {"title": movie, "popular": True}, source="test")
        
        # Access each movie multiple times
        for _ in range(10):
            for movie in popular_movies:
                result = cache.get(movie, source="test")
                assert result is not None
                assert result["popular"] is True
        
        # After warmup, all should be hits
        stats = cache.get_stats()
        # All 30 get operations should be hits (data was pre-stored with set)
        assert stats["hits"] == 30
        assert stats["misses"] == 0
        assert stats["hit_ratio"] == 1.0
    
    def test_mixed_workload(self):
        """Test cache with mixed hit/miss workload."""
        cache = MovieCache()
        
        # Store some movies
        for i in range(10):
            cache.set(f"Movie{i}", {"id": i}, source="test")
        
        # Mixed access pattern: some hits, some misses
        access_pattern = (
            list(range(10)) +  # All hits
            list(range(10, 15)) +  # All misses
            list(range(5)) +  # More hits
            list(range(15, 20))  # More misses
        )
        
        for i in access_pattern:
            cache.get(f"Movie{i}", source="test")
        
        stats = cache.get_stats()
        # Total get operations: 25 (access_pattern length)
        # Hits: 10 (first range) + 5 (second range 0-5) = 15
        # Misses: 5 (range 10-15) + 5 (range 15-20) = 10
        assert stats["total_requests"] == 25
        assert stats["hits"] == 15
        assert stats["misses"] == 10


class TestCacheErrorHandling:
    """Test cache behavior with edge cases."""
    
    def test_cache_with_empty_title(self):
        """Test cache handles empty titles gracefully."""
        cache = MovieCache()
        
        # Should not crash
        cache.set("", {"test": "data"}, source="test")
        result = cache.get("", source="test")
        
        # Either works or returns None, both are acceptable
        assert result is None or isinstance(result, dict)
    
    def test_cache_with_special_characters(self):
        """Test cache handles special characters in titles."""
        cache = MovieCache()
        
        titles = [
            "Movie!@#$%",
            "Movie-With-Dashes",
            "Movie's Title",
            "Movie: The Sequel",
            "Amélie"
        ]
        
        for title in titles:
            cache.set(title, {"title": title}, source="test")
            result = cache.get(title, source="test")
            assert result is not None
            assert result["title"] == title
    
    def test_cache_disabled_mode(self):
        """Test that disabled cache doesn't store data."""
        cache = MovieCache(enabled=False)
        
        cache.set("Test", {"data": "value"}, source="test")
        result = cache.get("Test", source="test")
        
        assert result is None
    
    def test_cache_clear_functionality(self):
        """Test cache clear works correctly."""
        cache = MovieCache()
        
        # Add data from multiple sources
        cache.set("Movie1", {"id": 1}, source="tmdb")
        cache.set("Movie2", {"id": 2}, source="omdb")
        cache.set("Movie3", {"id": 3}, source="tmdb")
        
        # Clear specific source
        count = cache.clear(source="tmdb")
        assert count == 2
        
        # TMDB entries should be gone
        assert cache.get("Movie1", source="tmdb") is None
        assert cache.get("Movie3", source="tmdb") is None
        
        # OMDb entry should remain
        assert cache.get("Movie2", source="omdb") is not None
        
        # Clear all
        count = cache.clear()
        assert count == 1
        assert cache.get("Movie2", source="omdb") is None


class TestCacheKeyNormalization:
    """Test cache key normalization for better hit rates."""
    
    def test_case_insensitive_lookup(self):
        """Test that cache lookups are case-insensitive."""
        cache = MovieCache()
        
        cache.set("The Matrix", {"title": "The Matrix"}, source="test")
        
        # Different cases should all hit the same entry
        assert cache.get("the matrix", source="test") is not None
        assert cache.get("THE MATRIX", source="test") is not None
        assert cache.get("The Matrix", source="test") is not None
        
        # All should be cache hits (set doesn't count as a request)
        stats = cache.get_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 0  # All gets hit the cache
    
    def test_whitespace_normalization(self):
        """Test that extra whitespace is normalized."""
        cache = MovieCache()
        
        cache.set("The  Matrix", {"title": "The Matrix"}, source="test")
        
        # Different whitespace should hit same entry
        assert cache.get("The Matrix", source="test") is not None
        assert cache.get("The   Matrix", source="test") is not None
    
    def test_article_removal(self):
        """Test that leading articles are removed for normalization."""
        cache = MovieCache()
        
        cache.set("Matrix", {"title": "The Matrix"}, source="test")
        
        # With or without article should match
        result1 = cache.get("Matrix", source="test")
        result2 = cache.get("The Matrix", source="test")
        
        # Both should hit (normalized to same key)
        assert result1 is not None
        assert result2 is not None


class TestGlobalCacheInstance:
    """Test global cache singleton behavior."""
    
    def test_get_cache_returns_singleton(self):
        """Test that get_cache returns the same instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        
        assert cache1 is cache2
    
    def test_global_cache_persistence(self):
        """Test that global cache persists data across calls."""
        cache1 = get_cache()
        cache1.clear()  # Start fresh
        
        cache1.set("Test", {"data": "value"}, source="test")
        
        cache2 = get_cache()
        result = cache2.get("Test", source="test")
        
        assert result is not None
        assert result["data"] == "value"
