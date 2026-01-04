"""
In-Memory Caching Layer for TMDB/OMDb Metadata with TTL.

This module provides a centralized, normalized-keyed caching layer for movie
metadata from external APIs (TMDB and OMDb). It helps reduce API calls and
improves performance by caching frequently-accessed movie data.

Key Features:
- Normalized key generation (title, year, case/punctuation handling)
- Configurable TTL (time-to-live) with default 24h, override via ENV
- LRU eviction when cache size exceeds maximum
- Structured logging for cache events (hits, misses, evictions)
- Cache statistics and metrics tracking
- Extensible design for future Redis/distributed cache support

Usage Example:
    >>> from cineman.cache import MovieCache
    >>> cache = MovieCache()
    >>> 
    >>> # Store movie data
    >>> cache.set("Inception", {"title": "Inception", "year": "2010"}, source="tmdb")
    >>> 
    >>> # Retrieve movie data
    >>> result = cache.get("inception", source="tmdb")  # Case-insensitive
    >>> print(result)
    >>> 
    >>> # Get cache statistics
    >>> stats = cache.get_stats()
    >>> print(f"Hit ratio: {stats['hit_ratio']:.2%}")
"""

import os
import re
import time
import logging
from typing import Dict, Any, Optional, Tuple
from collections import OrderedDict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """
    Represents a single cache entry with metadata.
    
    Attributes:
        value: The cached data
        timestamp: When the entry was created (Unix timestamp)
        ttl: Time-to-live in seconds
        source: Data source identifier (e.g., "tmdb", "omdb")
        hits: Number of times this entry was accessed
        normalized_key: The normalized cache key
    """
    value: Dict[str, Any]
    timestamp: float
    ttl: float
    source: str
    hits: int = 0
    normalized_key: str = ""


@dataclass
class CacheStats:
    """
    Cache statistics and metrics.
    
    Attributes:
        total_requests: Total number of cache lookups
        hits: Number of cache hits
        misses: Number of cache misses
        evictions: Number of entries evicted (TTL or LRU)
        current_size: Current number of entries in cache
        max_size: Maximum allowed cache size
        hit_ratio: Cache hit ratio (0.0 to 1.0)
    """
    total_requests: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    current_size: int = 0
    max_size: int = 0
    
    @property
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests


class MovieCache:
    """
    In-memory cache for movie metadata with TTL and LRU eviction.
    
    This class provides a thread-safe (within single process) cache implementation
    for movie metadata from TMDB and OMDb APIs. It uses normalized keys for better
    hit rates and automatically evicts stale entries.
    
    Configuration (via environment variables):
        MOVIE_CACHE_TTL: Default TTL in seconds (default: 86400 = 24 hours)
        MOVIE_CACHE_MAX_SIZE: Maximum number of entries (default: 1000)
        MOVIE_CACHE_ENABLED: Enable/disable caching (default: 1)
    
    Thread Safety Note:
        This implementation is designed for single-process use. For multi-process
        or distributed deployments, consider using Redis or similar distributed cache.
    """
    
    def __init__(
        self,
        ttl: Optional[int] = None,
        max_size: Optional[int] = None,
        enabled: Optional[bool] = None
    ):
        """
        Initialize the movie cache.
        
        Args:
            ttl: Time-to-live in seconds (default: from env or 86400)
            max_size: Maximum cache entries (default: from env or 1000)
            enabled: Enable/disable cache (default: from env or True)
        """
        # Configuration with environment variable fallbacks
        self.ttl = ttl if ttl is not None else int(os.getenv("MOVIE_CACHE_TTL", "86400"))
        self.max_size = max_size if max_size is not None else int(os.getenv("MOVIE_CACHE_MAX_SIZE", "1000"))
        self.enabled = enabled if enabled is not None else (os.getenv("MOVIE_CACHE_ENABLED", "1") != "0")
        
        # Cache storage using OrderedDict for LRU behavior
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Statistics tracking
        self._stats = CacheStats(max_size=self.max_size)
        
        logger.info(
            f"MovieCache initialized: enabled={self.enabled}, ttl={self.ttl}s, "
            f"max_size={self.max_size}"
        )
    
    def _normalize_key(self, title: str, year: Optional[str] = None, source: str = "") -> str:
        """
        Normalize cache key for consistent lookups.
        
        Normalization steps:
        1. Convert to lowercase
        2. Remove extra whitespace
        3. Remove common punctuation (except hyphens and apostrophes)
        4. Strip articles (a, an, the) from the beginning
        5. Include year if provided
        6. Include source prefix
        
        Args:
            title: Movie title
            year: Optional year
            source: Data source (e.g., "tmdb", "omdb")
            
        Returns:
            Normalized cache key
            
        Examples:
            >>> cache._normalize_key("The Matrix", "1999", "tmdb")
            'tmdb:matrix:1999'
            >>> cache._normalize_key("Spider-Man", source="omdb")
            'omdb:spider-man'
        """
        if not title:
            return f"{source}:"
        
        # Convert to lowercase
        normalized = title.lower()
        
        # Remove common punctuation but keep hyphens and apostrophes
        normalized = re.sub(r"[^\w\s'-]", '', normalized)
        
        # Normalize whitespace
        normalized = ' '.join(normalized.split())
        
        # Remove leading articles (a, an, the)
        normalized = re.sub(r'^(a|an|the)\s+', '', normalized)
        
        # Build key with source prefix and optional year
        key_parts = [source, normalized]
        if year:
            # Extract year if in format like "2010" or "2010-2012"
            year_match = re.search(r'\b(19|20)\d{2}\b', str(year))
            if year_match:
                key_parts.append(year_match.group(0))
        
        return ':'.join(key_parts)
    
    def get(
        self,
        title: str,
        year: Optional[str] = None,
        source: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve value from cache if present and not expired.
        
        Args:
            title: Movie title
            year: Optional year for better key specificity
            source: Data source identifier (e.g., "tmdb", "omdb")
            
        Returns:
            Cached value dict if found and valid, None otherwise
        """
        if not self.enabled:
            return None
        
        key = self._normalize_key(title, year, source)
        self._stats.total_requests += 1
        
        # Check if key exists
        if key not in self._cache:
            self._stats.misses += 1
            logger.debug(f"Cache miss: {key}")
            return None
        
        entry = self._cache[key]
        
        # Check if entry has expired
        age = time.time() - entry.timestamp
        if age > entry.ttl:
            # Entry expired - remove it
            del self._cache[key]
            self._stats.misses += 1
            self._stats.evictions += 1
            self._stats.current_size = len(self._cache)
            logger.debug(f"Cache expired: {key} (age: {age:.1f}s)")
            return None
        
        # Cache hit - move to end for LRU and increment hit counter
        self._cache.move_to_end(key)
        entry.hits += 1
        self._stats.hits += 1
        
        logger.debug(
            f"Cache hit: {key} (age: {age:.1f}s, hits: {entry.hits}, "
            f"hit_ratio: {self._stats.hit_ratio:.2%})"
        )
        
        return entry.value
    
    def set(
        self,
        title: str,
        value: Dict[str, Any],
        year: Optional[str] = None,
        source: str = "default",
        ttl: Optional[int] = None
    ) -> None:
        """
        Store value in cache with optional custom TTL.
        
        If cache is at max size, least recently used entry will be evicted.
        
        Args:
            title: Movie title
            value: Data to cache
            year: Optional year for better key specificity
            source: Data source identifier (e.g., "tmdb", "omdb")
            ttl: Optional custom TTL in seconds (overrides default)
        """
        if not self.enabled:
            return
        
        key = self._normalize_key(title, year, source)
        effective_ttl = ttl if ttl is not None else self.ttl
        
        # Check if we need to evict oldest entry (LRU)
        if key not in self._cache and len(self._cache) >= self.max_size:
            # Evict oldest (first) entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._stats.evictions += 1
            logger.debug(f"Cache LRU eviction: {oldest_key} (max_size reached)")
        
        # Store or update entry
        entry = CacheEntry(
            value=value,
            timestamp=time.time(),
            ttl=effective_ttl,
            source=source,
            normalized_key=key
        )
        
        self._cache[key] = entry
        self._cache.move_to_end(key)  # Ensure it's marked as most recent
        self._stats.current_size = len(self._cache)
        
        logger.debug(f"Cache set: {key} (ttl: {effective_ttl}s, size: {self._stats.current_size})")
    
    def evict(self, title: str, year: Optional[str] = None, source: str = "default") -> bool:
        """
        Manually evict a specific cache entry.
        
        Args:
            title: Movie title
            year: Optional year
            source: Data source identifier
            
        Returns:
            True if entry was evicted, False if not found
        """
        if not self.enabled:
            return False
        
        key = self._normalize_key(title, year, source)
        
        if key in self._cache:
            del self._cache[key]
            self._stats.evictions += 1
            self._stats.current_size = len(self._cache)
            logger.info(f"Cache evict: {key}")
            return True
        
        return False
    
    def clear(self, source: Optional[str] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            source: If provided, only clear entries from this source.
                   If None, clear all entries.
        
        Returns:
            Number of entries cleared
        """
        if not self.enabled:
            return 0
        
        if source is None:
            # Clear all entries
            count = len(self._cache)
            self._cache.clear()
            self._stats.current_size = 0
            logger.info(f"Cache cleared: {count} entries")
            return count
        
        # Clear entries for specific source
        keys_to_delete = [
            key for key, entry in self._cache.items()
            if entry.source == source
        ]
        
        for key in keys_to_delete:
            del self._cache[key]
        
        count = len(keys_to_delete)
        self._stats.current_size = len(self._cache)
        logger.info(f"Cache cleared for source '{source}': {count} entries")
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics and metrics.
        
        Returns:
            Dict containing cache statistics including:
            - total_requests: Total cache lookups
            - hits: Number of cache hits
            - misses: Number of cache misses
            - evictions: Number of evicted entries
            - current_size: Current cache size
            - max_size: Maximum cache size
            - hit_ratio: Cache hit ratio (0.0 to 1.0)
            - enabled: Whether cache is enabled
        """
        return {
            "total_requests": self._stats.total_requests,
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "evictions": self._stats.evictions,
            "current_size": self._stats.current_size,
            "max_size": self._stats.max_size,
            "hit_ratio": self._stats.hit_ratio,
            "enabled": self.enabled
        }
    
    def reset_stats(self) -> None:
        """Reset cache statistics without clearing cached data."""
        self._stats = CacheStats(
            max_size=self.max_size,
            current_size=len(self._cache)
        )
        logger.info("Cache statistics reset")


# Global cache instance for shared use across the application
_global_cache: Optional[MovieCache] = None


def get_cache() -> MovieCache:
    """
    Get or create the global cache instance.
    
    This ensures a single cache instance is shared across the application
    for consistent caching behavior and statistics.
    
    Returns:
        Global MovieCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = MovieCache()
    return _global_cache


def reset_global_cache():
    """Reset the global cache instance (useful for testing)."""
    global _global_cache
    _global_cache = None
