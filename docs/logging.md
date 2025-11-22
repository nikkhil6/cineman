# Structured JSON Logging Guide

## Overview

Cineman uses structured JSON logging to provide comprehensive observability across the entire application stack. This document describes the logging format, configuration, and best practices.

## Features

- **Structured JSON Logging**: All logs are output in JSON format (production) or human-readable format (development)
- **Request/Session Tracing**: Unique `request_id` and `session_id` propagated through all layers
- **Performance Metrics**: External API latency tracking, cache events, and LLM token usage
- **Security**: Automatic scrubbing of API keys, tokens, and PII
- **Configurable**: Log level controlled via `LOG_LEVEL` environment variable

## Configuration

### Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `LOG_LEVEL` | DEBUG, INFO, WARNING, ERROR, CRITICAL | INFO | Minimum log level to output |
| `FLASK_ENV` | development, production | production | Controls output format (console vs JSON) |
| `DEBUG` | 0, 1 | 0 | Alternative way to enable development mode |

### Log Output Format

#### Development Mode (Console)
When `FLASK_ENV=development` or `DEBUG=1`:
```
2025-11-22T14:05:33.190388Z [info     ] request_started          environment=local method=GET path=/api/movie request_id=abc-123 service=cineman
```

#### Production Mode (JSON)
Default format for production deployments:
```json
{
  "event": "request_started",
  "level": "info",
  "timestamp": "2025-11-22T14:05:33.190388Z",
  "service": "cineman",
  "environment": "local",
  "request_id": "abc-123",
  "session_id": "def-456",
  "method": "GET",
  "path": "/api/movie"
}
```

## Standard Log Fields

### Common Fields (Present in All Logs)

| Field | Type | Description |
|-------|------|-------------|
| `event` | string | Event name describing what happened |
| `level` | string | Log level (info, warning, error, debug) |
| `timestamp` | string | ISO 8601 timestamp in UTC |
| `service` | string | Always "cineman" |
| `environment` | string | Deployment environment (local, gcp-app-engine, gcp-cloud-run) |
| `request_id` | string | Unique ID for each HTTP request |
| `session_id` | string | User session ID (when available) |

### Event-Specific Fields

Different events include additional context fields:

#### HTTP Request Events
```json
{
  "event": "request_started",
  "method": "POST",
  "path": "/chat",
  "remote_addr": "192.168.1.1",
  "user_agent": "Mozilla/5.0..."
}
```

```json
{
  "event": "request_completed",
  "method": "POST",
  "path": "/chat",
  "status_code": 200,
  "duration_ms": 1234.56
}
```

#### External API Call Events
```json
{
  "event": "external_api_call_started",
  "api_name": "tmdb",
  "operation": "search_movie",
  "title": "Inception"
}
```

```json
{
  "event": "external_api_call_completed",
  "api_name": "tmdb",
  "operation": "search_movie",
  "title": "Inception",
  "duration_ms": 123.45
}
```

#### Cache Events
```json
{
  "event": "cache_event",
  "cache_key": "omdb:inception",
  "event_type": "get",
  "cache_hit": true,
  "title": "Inception"
}
```

#### LLM Usage Events
```json
{
  "event": "llm_usage",
  "model": "gemini-2.5-flash",
  "input_tokens": 150,
  "output_tokens": 350,
  "total_tokens": 500,
  "duration_ms": 2500.00
}
```

#### Pipeline Phase Events
```json
{
  "event": "pipeline_phase",
  "phase": "movie_validation",
  "status": "started"
}
```

```json
{
  "event": "pipeline_phase",
  "phase": "movie_validation",
  "status": "completed",
  "duration_ms": 456.78
}
```

## Request and Session Tracing

### Request ID

A unique `request_id` (UUID) is automatically generated for each HTTP request and propagated throughout the entire request lifecycle. This allows you to:

- Trace a single request through all log entries
- Correlate logs across different components
- Debug specific user interactions

The `request_id` is also included in the response headers as `X-Request-ID`.

### Session ID

The `session_id` tracks user sessions across multiple requests. It is:

- Created when a user starts a new session
- Stored in Flask's session cookie
- Propagated to all logs during that session
- Used to track conversation history and recommendations

## Security and Privacy

### Automatic Scrubbing

All logs are automatically scrubbed to remove sensitive information:

#### API Keys and Tokens
The following patterns are automatically redacted:
- `api_key`, `apikey`, `api-key`
- `gemini_api_key`, `gemini-api-key`
- `tmdb_api_key`, `tmdb-api-key`
- `omdb_api_key`, `omdb-api-key`
- `password`, `secret`, `token`
- `authorization`, `bearer`

Example:
```json
{
  "api_key": "[REDACTED]",
  "authorization": "Bearer [REDACTED]"
}
```

#### Personal Information (PII)
- Email addresses are replaced with `[EMAIL_REDACTED]`

### Best Practices

1. **Never log user inputs directly** without scrubbing
2. **Never log full API responses** that might contain sensitive data
3. **Use specific field names** that are recognized by the scrubber
4. **Review logs regularly** to ensure no sensitive data leaks

## Usage Examples

### Basic Logging

```python
from cineman.logging_config import get_logger

logger = get_logger(__name__)

# Simple info log
logger.info("user_action", action="clicked_movie", movie_id=123)

# Error with exception
try:
    risky_operation()
except Exception as e:
    logger.error("operation_failed", error=str(e), exc_info=True)
```

### External API Tracking

```python
from cineman.logging_metrics import track_external_api_call

with track_external_api_call("tmdb", "search_movie", title="Inception"):
    response = requests.get(tmdb_url, params=params)
    # Automatically logs start, duration, and completion
```

### Cache Events

```python
from cineman.logging_metrics import log_cache_event

# Log cache hit/miss
log_cache_event("movie:inception", "get", hit=True)

# Log cache set
log_cache_event("movie:inception", "set", ttl=300)
```

### Pipeline Phase Tracking

```python
from cineman.logging_metrics import track_phase

with track_phase("movie_validation", movie_count=3):
    validated_movies = validate_movies(movies)
    # Automatically logs phase start, duration, and completion
```

### Adding Context

```python
from cineman.logging_context import bind_context, set_session_id

# Set session ID (automatically included in all subsequent logs)
set_session_id("user-session-123")

# Add additional context
bind_context(user_tier="premium", feature_flag="new_ui")

# All logs now include these fields
logger.info("recommendation_generated", movie_count=5)
```

## Log Events Reference

### Application Lifecycle
- `database_initialized` - Database tables created successfully
- `database_init_delayed` - Database initialization deferred to first request
- `database_verified` - Database tables verified on first request
- `chain_initialized` - LangChain recommendation chain loaded
- `chain_init_failed` - Failed to initialize AI chain
- `session_manager_initialized` - Session manager ready

### HTTP Request/Response
- `request_started` - Incoming HTTP request
- `request_completed` - HTTP request completed successfully
- `request_failed` - HTTP request failed with exception

### Chat/Recommendations
- `chat_request_rejected` - Chat request rejected (e.g., empty message)
- `chat_context_loaded` - Session context loaded for request
- `llm_call_completed` - LLM invocation finished
- `rate_limit_exceeded` - Daily API limit reached
- `rate_limit_updated` - Rate limit counter incremented
- `movies_recommended` - New movies recommended to user
- `validation_completed` - Movie validation finished
- `chat_request_completed` - Chat request fully processed
- `chat_request_failed` - Chat request failed with error

### External APIs
- `external_api_call_started` - External API call initiated
- `external_api_call_completed` - External API call succeeded
- `external_api_call_failed` - External API call failed
- `tmdb_movie_found` - Movie found in TMDB
- `tmdb_movie_not_found` - Movie not found in TMDB
- `tmdb_request_failed` - TMDB API request error

### Cache
- `cache_event` - Cache operation (get, set, delete, clear)

### Session Management
- `session_cleared` - User session cleared/reset
- `session_clear_failed` - Failed to clear session

### Pipeline Phases
- `pipeline_phase` - Pipeline phase event (started, completed, failed)

## Querying Logs

### In Development (Console)

Grep for specific events:
```bash
# Show all external API calls
grep "external_api_call" app.log

# Show errors only
grep "\[error" app.log

# Track a specific request
grep "request_id=abc-123" app.log
```

### In Production (JSON)

Use `jq` for JSON processing:
```bash
# Show all errors
cat app.log | jq 'select(.level=="error")'

# Track a specific session
cat app.log | jq 'select(.session_id=="def-456")'

# Show API latencies
cat app.log | jq 'select(.event=="external_api_call_completed") | {api: .api_name, duration: .duration_ms}'

# Calculate average API latency
cat app.log | jq -s 'map(select(.event=="external_api_call_completed")) | map(.duration_ms) | add/length'
```

### In Google Cloud Logging

Query examples:
```
# All errors
severity >= ERROR

# Specific session
jsonPayload.session_id = "def-456"

# Slow API calls
jsonPayload.duration_ms > 1000

# Rate limit events
jsonPayload.event = "rate_limit_exceeded"
```

## Performance Considerations

### Log Volume

Logging has minimal performance impact:
- Structured logging is efficient (no string formatting overhead)
- JSON serialization is fast
- Context propagation uses thread-local storage

### Controlling Volume

Adjust `LOG_LEVEL` to control verbosity:
- `DEBUG`: Very verbose, includes all diagnostic info
- `INFO`: Standard level, includes important events (default)
- `WARNING`: Only warnings and errors
- `ERROR`: Only errors and critical issues

### Sampling (Future Enhancement)

For very high-traffic deployments, consider implementing log sampling:
```python
# Log only 10% of requests (not yet implemented)
if random.random() < 0.1:
    logger.info("sampled_event", ...)
```

## Integration with Monitoring

### Application Performance Monitoring (APM)

The structured logs can be easily integrated with APM tools:

- **Google Cloud Monitoring**: Automatically ingested from Cloud Logging
- **Datadog**: Use Datadog agent to collect and parse JSON logs
- **New Relic**: Configure log forwarder for structured logs
- **Elasticsearch/Kibana**: Ship logs via Filebeat or Fluentd

### Metrics Extraction

Extract metrics from logs:
```bash
# API latency percentiles
cat app.log | jq -s 'map(select(.event=="external_api_call_completed")) | map(.duration_ms) | sort | .[length*0.95|floor]'

# Cache hit rate
cat app.log | jq -s '
  map(select(.event=="cache_event" and .event_type=="get")) |
  {total: length, hits: (map(select(.cache_hit==true)) | length)} |
  .hit_rate = (.hits / .total * 100)
'
```

## Troubleshooting

### No Logs Appearing

1. Check `LOG_LEVEL` - set to `INFO` or `DEBUG`
2. Verify logging is configured: `from cineman.logging_config import configure_structlog; configure_structlog()`
3. Ensure Flask middleware is initialized: `init_logging_middleware(app)`

### Sensitive Data in Logs

1. Check that scrubbing is enabled (it is by default)
2. Verify field names match `SENSITIVE_FIELD_NAMES` in `logging_config.py`
3. Add new patterns to `SENSITIVE_PATTERNS` if needed

### Missing Request ID

1. Ensure Flask middleware is initialized
2. Check that `@app.before_request` hooks are running
3. Verify context is not being cleared prematurely

### Performance Issues

1. Reduce log level from `DEBUG` to `INFO`
2. Check for excessive logging in tight loops
3. Monitor log volume and consider sampling

## Testing

### Unit Tests

Test log output and scrubbing:
```python
import json
from cineman.logging_config import scrub_sensitive_data

def test_api_key_scrubbing():
    data = {"api_key": "secret123", "user": "john"}
    scrubbed = scrub_sensitive_data(data)
    assert scrubbed["api_key"] == "[REDACTED]"
    assert scrubbed["user"] == "john"
```

### Integration Tests

Verify request tracing:
```python
def test_request_tracing(client):
    response = client.post('/chat', json={"message": "test"})
    assert 'X-Request-ID' in response.headers
```

## Migration from Legacy Logging

### Before (Legacy Print Statements)
```python
print(f"Processing request for user {user_id}")
print(f"API call took {duration}ms")
```

### After (Structured Logging)
```python
logger.info("request_processing", user_id=user_id)
logger.info("api_call_completed", duration_ms=duration)
```

### Benefits
1. **Structured**: Easy to parse and query
2. **Contextual**: Automatic request/session IDs
3. **Secure**: Automatic scrubbing
4. **Traceable**: Full request lifecycle tracking

## Appendix

### Related Files
- `cineman/logging_config.py` - Core logging configuration
- `cineman/logging_context.py` - Context management for IDs
- `cineman/logging_middleware.py` - Flask middleware
- `cineman/logging_metrics.py` - Metrics tracking utilities

### References
- [Structlog Documentation](https://www.structlog.org/)
- [JSON Logging Best Practices](https://12factor.net/logs)
- [Google Cloud Logging](https://cloud.google.com/logging/docs)
