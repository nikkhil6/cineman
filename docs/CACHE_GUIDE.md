# Movie Metadata Cache Guide

## Overview

The movie metadata cache is a centralized, in-memory caching layer that reduces external API calls to TMDB and OMDb by caching movie metadata with configurable time-to-live (TTL) and automatic eviction policies.

## Features

- **Normalized Key Generation**: Handles case-insensitive lookups, removes articles, normalizes whitespace
- **Configurable TTL**: Default 24 hours, customizable per entry or via environment variables
- **LRU Eviction**: Automatically evicts least recently used entries when cache reaches max size
- **Source Separation**: Maintains separate cache entries for TMDB and OMDb data
- **Performance Metrics**: Tracks hits, misses, evictions, and hit ratio
- **Structured Logging**: Logs cache events for monitoring and debugging

## Configuration

The cache can be configured via environment variables:

```bash
# Cache TTL in seconds (default: 86400 = 24 hours)
export MOVIE_CACHE_TTL=86400

# Maximum number of cache entries (default: 1000)
export MOVIE_CACHE_MAX_SIZE=1000

# Enable/disable caching (default: 1 = enabled)
export MOVIE_CACHE_ENABLED=1
```

## Usage

### Basic Usage

The cache is automatically integrated with TMDB and OMDb tools. No manual cache management is required:

```python
from cineman.tools.tmdb import get_movie_poster_core
from cineman.tools.omdb import fetch_omdb_data_core

# First call - cache miss, hits API
result1 = get_movie_poster_core("Inception")

# Second call - cache hit, no API call
result2 = get_movie_poster_core("Inception")
```

### Direct Cache Access

For advanced use cases, you can access the cache directly:

```python
from cineman.cache import get_cache

# Get the global cache instance
cache = get_cache()

# Store data
cache.set("Inception", {"title": "Inception", "year": "2010"}, source="custom")

# Retrieve data
result = cache.get("Inception", source="custom")

# Get cache statistics
stats = cache.get_stats()
print(f"Hit ratio: {stats['hit_ratio']:.2%}")

# Clear cache for specific source
cache.clear(source="custom")
```

### Custom TTL

You can specify different TTLs for different types of data:

```python
from cineman.cache import get_cache

cache = get_cache()

# Cache success with default TTL (24 hours)
cache.set("Movie1", {"status": "success", ...}, source="tmdb")

# Cache error with short TTL (5 minutes)
cache.set("Movie2", {"status": "error", ...}, source="tmdb", ttl=300)

# Cache not_found with medium TTL (1 hour)
cache.set("Movie3", {"status": "not_found", ...}, source="tmdb", ttl=3600)
```

## Key Normalization

The cache uses intelligent key normalization to improve hit rates:

### Case Insensitive
```python
cache.set("The Matrix", data, source="tmdb")

cache.get("the matrix", source="tmdb")  # ✓ Hit
cache.get("THE MATRIX", source="tmdb")  # ✓ Hit
cache.get("The Matrix", source="tmdb")  # ✓ Hit
```

### Article Removal
```python
cache.set("Matrix", data, source="tmdb")

cache.get("The Matrix", source="tmdb")  # ✓ Hit
cache.get("A Matrix", source="tmdb")    # ✓ Hit
```

### Whitespace Normalization
```python
cache.set("The  Matrix", data, source="tmdb")

cache.get("The Matrix", source="tmdb")     # ✓ Hit
cache.get("The   Matrix", source="tmdb")   # ✓ Hit
```

### Punctuation Handling
```python
# Hyphens and apostrophes are preserved
cache.set("Spider-Man", data, source="tmdb")
cache.get("Spider-Man", source="tmdb")  # ✓ Hit

cache.set("Ocean's Eleven", data, source="tmdb")
cache.get("Ocean's Eleven", source="tmdb")  # ✓ Hit

# Other punctuation is removed
cache.set("Movie!", data, source="tmdb")
cache.get("Movie", source="tmdb")  # ✓ Hit
```

## Performance Monitoring

Monitor cache performance using the built-in statistics:

```python
from cineman.cache import get_cache

cache = get_cache()
stats = cache.get_stats()

print(f"Total requests: {stats['total_requests']}")
print(f"Cache hits: {stats['hits']}")
print(f"Cache misses: {stats['misses']}")
print(f"Hit ratio: {stats['hit_ratio']:.2%}")
print(f"Current size: {stats['current_size']}/{stats['max_size']}")
print(f"Evictions: {stats['evictions']}")
```

### Expected Performance

With proper cache warming, you can expect:
- **Hit ratio**: 70-90% for typical workloads
- **Latency reduction**: ~100ms per cache hit (vs. external API call)
- **API call reduction**: Up to 80% fewer external API calls

## Cache Eviction

### TTL-Based Eviction

Entries are automatically evicted when they exceed their TTL:
- **Success responses**: 24 hours (default)
- **Error responses**: 5 minutes
- **Not found responses**: 1 hour

### LRU Eviction

When the cache reaches `max_size`, the least recently used entry is evicted to make room for new entries.

## Logging

The cache logs important events for monitoring:

```python
import logging

# Enable debug logging to see cache hits/misses
logging.basicConfig(level=logging.DEBUG)

# Example log output:
# DEBUG:cineman.cache:Cache hit: tmdb:inception (age: 12.3s, hits: 5, hit_ratio: 0.85)
# DEBUG:cineman.cache:Cache miss: tmdb:unknown-movie
# DEBUG:cineman.cache:Cache set: tmdb:inception (ttl: 86400s, size: 150)
# DEBUG:cineman.cache:Cache LRU eviction: tmdb:old-movie (max_size reached)
```

## Best Practices

1. **Use Appropriate TTLs**: 
   - Long TTL for static data (movie titles, directors)
   - Short TTL for dynamic data (ratings, trending status)

2. **Monitor Hit Ratio**:
   - Target 70%+ hit ratio for good performance
   - Low hit ratio may indicate cache size too small or TTL too short

3. **Handle Cache Misses Gracefully**:
   - The tools automatically fall back to API calls on cache miss
   - Don't assume data is always in cache

4. **Avoid Cache Pollution**:
   - Don't cache temporary or user-specific data
   - Use appropriate TTLs for different data types

5. **Size the Cache Appropriately**:
   - Default 1000 entries is good for most use cases
   - Increase if you have high traffic and diverse movie queries
   - Monitor eviction rate to ensure size is adequate

## Future Enhancements

The cache is designed to be easily extended:

- **Redis Backend**: Replace in-memory storage with Redis for distributed caching
- **Persistence**: Add option to persist cache to disk
- **Cache Warming**: Pre-populate cache with popular movies
- **Selective Invalidation**: Invalidate specific entries based on external events
- **Multi-level Cache**: Add L1 (memory) and L2 (Redis) cache tiers

## Troubleshooting

### Low Hit Ratio

**Problem**: Cache hit ratio is below 50%

**Solutions**:
- Increase `MOVIE_CACHE_MAX_SIZE` to avoid premature evictions
- Increase `MOVIE_CACHE_TTL` if data staleness is acceptable
- Check if queries use consistent title formatting

### High Memory Usage

**Problem**: Cache is using too much memory

**Solutions**:
- Decrease `MOVIE_CACHE_MAX_SIZE` to limit entries
- Decrease `MOVIE_CACHE_TTL` to expire entries sooner
- Monitor eviction rate after changes

### Cache Not Working

**Problem**: Cache doesn't seem to be working

**Solutions**:
- Check `MOVIE_CACHE_ENABLED=1` is set
- Verify logging shows cache hits/misses
- Check cache statistics with `cache.get_stats()`
- Ensure same title/year is used for lookup

### Stale Data

**Problem**: Cache returning outdated information

**Solutions**:
- Decrease `MOVIE_CACHE_TTL` for volatile data
- Use shorter custom TTL for specific data types
- Manually clear cache: `cache.clear(source="tmdb")`

## Testing

The cache includes comprehensive test coverage:

```bash
# Run cache unit tests (44 tests)
pytest tests/test_cache.py -v

# Run cache integration tests (16 tests)
pytest tests/test_cache_integration.py -v

# Run all cache-related tests
pytest tests/test_cache*.py -v
```

## API Reference

### MovieCache Class

```python
class MovieCache:
    def __init__(self, ttl=None, max_size=None, enabled=None):
        """Initialize cache with optional configuration."""
        
    def get(self, title, year=None, source="default"):
        """Retrieve cached value or None if not found/expired."""
        
    def set(self, title, value, year=None, source="default", ttl=None):
        """Store value in cache with optional custom TTL."""
        
    def evict(self, title, year=None, source="default"):
        """Manually evict a specific cache entry."""
        
    def clear(self, source=None):
        """Clear cache entries (all or for specific source)."""
        
    def get_stats(self):
        """Get cache statistics and metrics."""
        
    def reset_stats(self):
        """Reset statistics without clearing cached data."""
```

### Global Cache Instance

```python
from cineman.cache import get_cache

# Get or create the global cache instance
cache = get_cache()
```

## Examples

### Example 1: Simple Cache Usage

```python
from cineman.tools.tmdb import get_movie_poster_core
from cineman.cache import get_cache

# Get initial stats
cache = get_cache()
print(f"Initial stats: {cache.get_stats()}")

# Make some queries
movies = ["Inception", "The Matrix", "Interstellar"]
for movie in movies:
    result = get_movie_poster_core(movie)
    print(f"Got: {result['title']}")

# Check stats
stats = cache.get_stats()
print(f"Hit ratio: {stats['hit_ratio']:.2%}")
```

### Example 2: Custom TTL for Different Data

```python
from cineman.cache import get_cache

cache = get_cache()

# Cache movie metadata (long TTL - 24 hours)
cache.set("Movie1", {
    "title": "Inception",
    "director": "Christopher Nolan"
}, source="custom", ttl=86400)

# Cache trending data (short TTL - 5 minutes)
cache.set("trending", {
    "movies": ["Movie1", "Movie2"]
}, source="custom", ttl=300)
```

### Example 3: Monitoring Cache Performance

```python
from cineman.cache import get_cache
import time

cache = get_cache()

# Warmup cache
for i in range(100):
    cache.set(f"Movie{i}", {"id": i}, source="test")

# Simulate queries
for _ in range(1000):
    cache.get(f"Movie{_ % 100}", source="test")

# Check performance
stats = cache.get_stats()
print(f"""
Cache Performance:
- Total requests: {stats['total_requests']}
- Hits: {stats['hits']}
- Misses: {stats['misses']}
- Hit ratio: {stats['hit_ratio']:.2%}
- Current size: {stats['current_size']}
- Evictions: {stats['evictions']}
""")
```

## Conclusion

The movie metadata cache significantly reduces external API calls and improves application performance. With proper configuration and monitoring, you can achieve excellent hit ratios while maintaining fresh data.

For questions or issues, please refer to the test files (`tests/test_cache.py`, `tests/test_cache_integration.py`) for more examples and usage patterns.
