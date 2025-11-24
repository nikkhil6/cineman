# API Client Abstraction

## Overview

The `MovieDataClient` provides a robust abstraction layer for making HTTP requests to external movie data APIs (TMDB and OMDb). It implements automatic retries, configurable timeouts, and standardized error classification to ensure reliable and predictable API interactions.

## Architecture

### Core Components

1. **MovieDataClient**: Main client class that handles HTTP requests
2. **Error Taxonomy**: Standardized error types for different failure scenarios
3. **Retry Logic**: Exponential backoff with configurable limits
4. **Logging**: Comprehensive logging of retries and failures

### Integration Points

- `cineman/tools/tmdb.py`: TMDB API integration
- `cineman/tools/omdb.py`: OMDb API integration
- `cineman/validation.py`: Movie validation logic (indirect usage)

## Features

### 1. Automatic Retries with Exponential Backoff

The client automatically retries failed requests for transient errors:
- **Default retry count**: 3 attempts
- **Backoff delays**: 0.5s, 1s, 2s (exponential)
- **Retry strategy**: Only retries transient errors (network issues, 5xx, 429)

```python
# Default configuration
client = MovieDataClient()
# Retries: 0.5s delay, 1s delay, 2s delay

# Custom configuration
client = MovieDataClient(
    max_retries=2,
    backoff_base=1.0
)
# Retries: 1s delay, 2s delay
```

### 2. Configurable Timeouts

Per-request timeouts prevent indefinite waiting:
- **Default timeout**: 3 seconds
- **Override per request**: Can be customized for specific calls

```python
client = MovieDataClient(timeout=5.0)

# Use default timeout (5s)
response = client.get(url, params=params)

# Override for this request (10s)
response = client.get(url, params=params, timeout=10.0)
```

### 3. Error Taxonomy

All errors are classified into specific types for better error handling:

#### AuthError (401, 403)
Authentication or authorization failures. These are not retried.

```python
try:
    response = client.get(url, params=params)
except AuthError as e:
    logger.error(f"Invalid API key: {e.message}")
    # Handle authentication failure
```

#### QuotaError (429)
Rate limiting or quota exceeded. Retried with exponential backoff.

```python
try:
    response = client.get(url, params=params)
except QuotaError as e:
    logger.warning(f"Rate limited: {e.message}")
    # Handle quota exceeded
```

#### NotFoundError (404)
Resource not found. Not retried.

```python
try:
    response = client.get(url, params=params)
except NotFoundError as e:
    # Handle not found
    return {"status": "not_found"}
```

#### TransientError
Temporary failures that may succeed on retry:
- Network errors (ConnectionError, Timeout)
- Server errors (500, 502, 503, 504)

```python
try:
    response = client.get(url, params=params)
except TransientError as e:
    logger.error(f"Transient failure after retries: {e.message}")
    # Handle after exhausting retries
```

### 4. Comprehensive Logging

All retry attempts and failures are logged with context:

```
[TMDB] Request attempt 1/4: GET https://api.themoviedb.org/3/search/movie (timeout=3.0s)
[TMDB] Request failed with status 500: Internal Server Error
[TMDB] Retrying after 0.5s (attempt 1/3, error_type=transient)
[TMDB] Request attempt 2/4: GET https://api.themoviedb.org/3/search/movie (timeout=3.0s)
[TMDB] Request succeeded after 2 attempt(s)
```

## Configuration

### Environment Variables

All configuration can be overridden via environment variables:

```bash
# Default timeout for all requests (seconds)
export API_CLIENT_TIMEOUT=3.0

# Maximum number of retry attempts
export API_CLIENT_MAX_RETRIES=3

# Base delay for exponential backoff (seconds)
export API_CLIENT_BACKOFF_BASE=0.5
```

### Programmatic Configuration

```python
from cineman.api_client import MovieDataClient

# Use defaults from environment
client = MovieDataClient()

# Override specific settings
client = MovieDataClient(
    timeout=5.0,
    max_retries=2,
    backoff_base=1.0
)
```

## Usage Examples

### TMDB Integration

```python
from cineman.tools.tmdb import get_movie_poster_core

# Simple usage - handles all errors internally
result = get_movie_poster_core("Inception")

if result["status"] == "success":
    print(f"Title: {result['title']}")
    print(f"Year: {result['year']}")
    print(f"Poster: {result['poster_url']}")
elif result["status"] == "auth_error":
    print("Invalid API key")
elif result["status"] == "quota_error":
    print("Rate limit exceeded")
elif result["status"] == "not_found":
    print("Movie not found")
else:
    print(f"Error: {result['error']}")
```

### OMDb Integration

```python
from cineman.tools.omdb import fetch_omdb_data_core

# Simple usage - handles all errors internally
result = fetch_omdb_data_core("Inception")

if result["status"] == "success":
    print(f"Title: {result['Title']}")
    print(f"Director: {result['Director']}")
    print(f"IMDb Rating: {result['IMDb_Rating']}")
    print(f"Attempts: {result['attempts']}")
    print(f"Elapsed: {result['elapsed']}s")
elif result["status"] == "forbidden":
    print("Authentication error")
elif result["status"] == "quota_error":
    print("Quota exceeded")
elif result["status"] == "not_found":
    print("Movie not found")
else:
    print(f"Error: {result['error']}")
```

### Direct Client Usage

```python
from cineman.api_client import MovieDataClient, AuthError, QuotaError

client = MovieDataClient(timeout=5.0, max_retries=3)

try:
    response = client.get(
        "https://api.example.com/data",
        params={"query": "test"},
        api_name="ExampleAPI"
    )
    data = response.json()
    # Process data
except AuthError as e:
    print(f"Auth error: {e.message}")
except QuotaError as e:
    print(f"Quota error: {e.message}")
except TransientError as e:
    print(f"Failed after retries: {e.message}")
finally:
    client.close()
```

### Context Manager

```python
from cineman.api_client import MovieDataClient

with MovieDataClient() as client:
    response = client.get(url, params=params)
    # Session automatically closed
```

## Error Handling Best Practices

### 1. Graceful Degradation

Always provide fallback behavior for API failures:

```python
result = get_movie_poster_core(title)

if result["status"] == "success":
    # Use full data
    display_movie_with_poster(result)
elif result["status"] == "not_found":
    # Movie doesn't exist
    show_not_found_message()
else:
    # API error - show movie without poster
    display_movie_without_poster(title)
```

### 2. User-Friendly Messages

Map error types to user-friendly messages:

```python
ERROR_MESSAGES = {
    "auth_error": "We're having trouble accessing movie data. Please try again later.",
    "quota_error": "We've reached our API limit. Please try again in a few minutes.",
    "error": "Unable to fetch movie data right now. Please try again.",
}

error_type = result.get("error_type", "unknown")
user_message = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["error"])
```

### 3. Logging for Debugging

Log errors with context for troubleshooting:

```python
import logging

logger = logging.getLogger(__name__)

result = get_movie_poster_core(title)
if result["status"] != "success":
    logger.warning(
        f"TMDB lookup failed for '{title}': "
        f"status={result['status']}, "
        f"error_type={result.get('error_type')}, "
        f"error={result.get('error')}"
    )
```

## Performance Considerations

### Latency Impact

Retries increase latency for failed requests:
- **No retries**: Request timeout only (default 3s)
- **With retries (3)**: Up to 3s + 0.5s + 1s + 2s = 6.5s worst case

### Mitigation Strategies

1. **Cache results**: OMDb already implements caching (300s TTL)
2. **Adjust timeouts**: Lower timeouts for faster failure detection
3. **Reduce retries**: Lower max_retries for latency-sensitive operations

```python
# Fast-fail configuration for interactive use
client = MovieDataClient(
    timeout=2.0,
    max_retries=1,
    backoff_base=0.3
)
```

### Connection Pooling

The client uses `requests.Session` for connection pooling, reducing overhead for multiple requests to the same API.

## Testing

### Unit Tests

Comprehensive unit tests cover all error scenarios:

```bash
# Run API client tests
pytest tests/test_api_client.py -v

# Run integration tests
pytest tests/test_tools_integration.py -v
```

### Test Coverage

- ✅ Timeout handling
- ✅ Retry logic with exponential backoff
- ✅ Error classification (Auth, Quota, NotFound, Transient)
- ✅ Successful requests
- ✅ Parallel request handling (thread safety)
- ✅ Environment variable configuration
- ✅ Custom timeout per request
- ✅ Context manager usage

## Troubleshooting

### High Latency

**Symptom**: Requests taking too long

**Solutions**:
1. Lower timeout: `export API_CLIENT_TIMEOUT=2.0`
2. Reduce retries: `export API_CLIENT_MAX_RETRIES=1`
3. Check API status: Review logs for retry patterns

### Frequent Auth Errors

**Symptom**: Consistent 401/403 errors

**Solutions**:
1. Verify API keys: Check `TMDB_API_KEY` and `OMDB_API_KEY`
2. Check API quotas: Ensure you haven't exceeded limits
3. Test API directly: Use curl to verify credentials

### Rate Limiting

**Symptom**: 429 errors

**Solutions**:
1. Implement caching: Already enabled for OMDb
2. Reduce request frequency: Add delays between requests
3. Upgrade API plan: Consider paid tier for higher limits

### Connection Issues

**Symptom**: Frequent connection errors

**Solutions**:
1. Check network: Verify internet connectivity
2. Review firewall: Ensure outbound HTTPS is allowed
3. Increase timeout: `export API_CLIENT_TIMEOUT=10.0`

## Migration Guide

### From Direct Requests

**Before**:
```python
import requests

response = requests.get(url, params=params, timeout=6)
data = response.json()
```

**After**:
```python
from cineman.api_client import MovieDataClient

client = MovieDataClient()
try:
    response = client.get(url, params=params, api_name="API")
    data = response.json()
except AuthError:
    # Handle auth error
except QuotaError:
    # Handle quota error
except TransientError:
    # Handle after retries
```

### For Tool Developers

The TMDB and OMDb tools already use `MovieDataClient`. No migration needed for code using these tools.

## Future Enhancements

Potential improvements for future versions:

1. **Circuit Breaker**: Temporarily disable failing APIs
2. **Metrics**: Prometheus-compatible metrics for monitoring
3. **Adaptive Timeouts**: Dynamically adjust based on API performance
4. **Request Deduplication**: Prevent duplicate in-flight requests
5. **Response Caching**: Built-in caching layer (currently only in OMDb)

## References

- [TMDB API Documentation](https://developers.themoviedb.org/3)
- [OMDb API Documentation](http://www.omdbapi.com/)
- [Requests Library](https://requests.readthedocs.io/)
- [Exponential Backoff](https://en.wikipedia.org/wiki/Exponential_backoff)
