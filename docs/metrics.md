# Prometheus Metrics for CineMan

## Overview

CineMan exposes comprehensive metrics in Prometheus format through the `/api/metrics` endpoint. These metrics enable external monitoring of application performance, API usage, caching effectiveness, and system health.

## Accessing Metrics

**Endpoint:** `GET /api/metrics`

**Response Format:** Prometheus text format (`text/plain; version=0.0.4`)

**Example:**
```bash
curl http://localhost:5000/api/metrics
```

## Available Metrics

### HTTP Request Metrics

#### `cineman_http_requests_total`
**Type:** Counter  
**Description:** Total number of HTTP requests processed by the application  
**Labels:**
- `method`: HTTP method (GET, POST, etc.)
- `endpoint`: Request endpoint or path
- `status`: HTTP status code (200, 404, 500, etc.)

**Example:**
```
cineman_http_requests_total{method="GET",endpoint="/api/movie",status="200"} 127
cineman_http_requests_total{method="POST",endpoint="/chat",status="200"} 45
```

#### `cineman_http_request_duration_seconds`
**Type:** Histogram  
**Description:** HTTP request duration in seconds  
**Labels:**
- `method`: HTTP method
- `endpoint`: Request endpoint

**Buckets:** 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0

**Use Case:** Calculate percentiles (p50, p95, p99) for request latency

---

### External API Metrics

#### `cineman_external_api_calls_total`
**Type:** Counter  
**Description:** Total number of external API calls (TMDB, OMDB, Gemini)  
**Labels:**
- `api_name`: Name of the external API (tmdb, omdb, gemini)
- `status`: Call status (success, error)

**Example:**
```
cineman_external_api_calls_total{api_name="tmdb",status="success"} 234
cineman_external_api_calls_total{api_name="omdb",status="error"} 12
```

#### `cineman_external_api_duration_seconds`
**Type:** Histogram  
**Description:** External API call duration in seconds  
**Labels:**
- `api_name`: Name of the external API

**Use Case:** Monitor external API latency and identify slow dependencies

---

### Cache Metrics

#### `cineman_cache_hits_total`
**Type:** Counter  
**Description:** Total number of cache hits  
**Labels:**
- `cache_type`: Type of cache (omdb, session, movie_data)

**Example:**
```
cineman_cache_hits_total{cache_type="omdb"} 456
```

#### `cineman_cache_misses_total`
**Type:** Counter  
**Description:** Total number of cache misses  
**Labels:**
- `cache_type`: Type of cache

**Cache Hit Rate Calculation:**
```promql
sum(rate(cineman_cache_hits_total[5m])) by (cache_type) /
(sum(rate(cineman_cache_hits_total[5m])) by (cache_type) + 
 sum(rate(cineman_cache_misses_total[5m])) by (cache_type))
```

---

### Movie Validation Metrics

#### `cineman_movie_validations_total`
**Type:** Counter  
**Description:** Total number of movie validations performed  
**Labels:**
- `result`: Validation result (valid, invalid, dropped, corrected)

**Example:**
```
cineman_movie_validations_total{result="valid"} 345
cineman_movie_validations_total{result="dropped"} 23
cineman_movie_validations_total{result="corrected"} 12
```

**Use Case:** Monitor LLM hallucination rate and validation effectiveness

#### `cineman_movie_validation_duration_seconds`
**Type:** Histogram  
**Description:** Movie validation duration in seconds  

**Use Case:** Measure validation latency impact on recommendation pipeline

---

### Duplicate Detection Metrics

#### `cineman_duplicate_recommendations_total`
**Type:** Counter  
**Description:** Total number of duplicate movie recommendations detected

**Use Case:** Monitor recommendation quality and session memory effectiveness

---

### Rate Limiter Metrics

#### `cineman_rate_limit_usage`
**Type:** Gauge  
**Description:** Current API rate limit usage count

#### `cineman_rate_limit_max`
**Type:** Gauge  
**Description:** Maximum API rate limit

#### `cineman_rate_limit_remaining`
**Type:** Gauge  
**Description:** Remaining API rate limit calls

**Example:**
```
cineman_rate_limit_usage 35
cineman_rate_limit_max 50
cineman_rate_limit_remaining 15
```

#### `cineman_rate_limit_exceeded_total`
**Type:** Counter  
**Description:** Total number of times rate limit was exceeded

**Use Case:** Monitor API quota exhaustion and user impact

---

### LLM/AI Metrics

#### `cineman_llm_invocations_total`
**Type:** Counter  
**Description:** Total number of LLM invocations  
**Labels:**
- `status`: Invocation status (success, error)

**Example:**
```
cineman_llm_invocations_total{status="success"} 456
cineman_llm_invocations_total{status="error"} 3
```

#### `cineman_llm_invocation_duration_seconds`
**Type:** Histogram  
**Description:** LLM invocation duration in seconds

**Use Case:** Monitor AI response time and identify performance bottlenecks

---

### Session Metrics

#### `cineman_active_sessions`
**Type:** Gauge  
**Description:** Number of active user sessions

**Use Case:** Monitor concurrent user activity

#### `cineman_session_duration_seconds`
**Type:** Histogram  
**Description:** User session duration in seconds

**Use Case:** Analyze user engagement patterns

---

## Monitoring Best Practices

### 1. Alerting Rules

#### High Error Rate
```yaml
- alert: HighAPIErrorRate
  expr: |
    rate(cineman_http_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m
  annotations:
    summary: "High API error rate detected"
```

#### Rate Limit Approaching
```yaml
- alert: RateLimitApproaching
  expr: cineman_rate_limit_remaining < 10
  annotations:
    summary: "API rate limit nearly exhausted"
```

#### External API Degradation
```yaml
- alert: ExternalAPIDegraded
  expr: |
    rate(cineman_external_api_calls_total{status="error"}[5m]) > 0.1
  for: 5m
  annotations:
    summary: "External API experiencing high error rate"
```

#### Cache Miss Rate Too High
```yaml
- alert: HighCacheMissRate
  expr: |
    sum(rate(cineman_cache_misses_total[5m])) by (cache_type) /
    (sum(rate(cineman_cache_hits_total[5m])) by (cache_type) + 
     sum(rate(cineman_cache_misses_total[5m])) by (cache_type)) > 0.5
  for: 10m
  annotations:
    summary: "Cache miss rate above 50%"
```

### 2. Dashboard Panels

#### Request Rate Panel
```promql
sum(rate(cineman_http_requests_total[5m])) by (endpoint)
```

#### Error Rate Panel
```promql
sum(rate(cineman_http_requests_total{status=~"5.."}[5m])) /
sum(rate(cineman_http_requests_total[5m]))
```

#### P95 Latency Panel
```promql
histogram_quantile(0.95, 
  sum(rate(cineman_http_request_duration_seconds_bucket[5m])) by (le, endpoint)
)
```

#### Validation Success Rate
```promql
sum(rate(cineman_movie_validations_total{result="valid"}[5m])) /
sum(rate(cineman_movie_validations_total[5m]))
```

### 3. Performance Monitoring

**Key Metrics to Monitor:**

1. **Request Latency:** Track p50, p95, p99 for all endpoints
2. **External API Health:** Monitor success rate and latency for TMDB, OMDB, Gemini
3. **Cache Effectiveness:** Maintain >70% cache hit rate for OMDB
4. **Validation Quality:** Monitor dropped recommendation rate (<5%)
5. **Rate Limit Usage:** Track daily API quota consumption
6. **LLM Performance:** Monitor success rate and response time

### 4. Capacity Planning

Use these metrics for capacity planning:
- `cineman_active_sessions`: Concurrent user capacity
- `cineman_rate_limit_usage`: API quota consumption patterns
- `cineman_http_request_duration_seconds`: Response time trends
- `cineman_external_api_calls_total`: External dependency load

---

## Security Considerations

### What Metrics DO NOT Expose:

✅ **Safe Metrics:**
- Request counts and rates
- Latency measurements
- Cache hit/miss ratios
- Validation statistics
- Error rates

❌ **NOT Exposed:**
- API keys or credentials
- User data or session content
- Movie titles or personal preferences
- IP addresses or user identifiers
- Internal system paths or configuration

### Recommended Access Control:

1. **Internal Network Only:** Restrict `/api/metrics` to internal monitoring infrastructure
2. **Authentication:** Consider adding basic auth for production deployments
3. **Rate Limiting:** Apply rate limiting to metrics endpoint to prevent abuse
4. **Read-Only:** Metrics endpoint is read-only by design

Example nginx configuration:
```nginx
location /api/metrics {
    allow 10.0.0.0/8;  # Internal network
    deny all;
    proxy_pass http://cineman;
}
```

---

## Integration Examples

### Prometheus Configuration

Add to `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'cineman'
    scrape_interval: 15s
    static_configs:
      - targets: ['cineman:5000']
    metrics_path: '/api/metrics'
```

### Grafana Dashboard

Import the CineMan dashboard (sample queries):

1. **Request Rate:** `rate(cineman_http_requests_total[5m])`
2. **Error Rate:** `rate(cineman_http_requests_total{status=~"5.."}[5m])`
3. **Cache Hit Rate:** Calculate from hits/total
4. **LLM Latency:** `histogram_quantile(0.95, rate(cineman_llm_invocation_duration_seconds_bucket[5m]))`

### Health Check Integration

Combine with existing `/health` endpoint:
```bash
# Check application health
curl http://localhost:5000/health

# Pull metrics for monitoring
curl http://localhost:5000/api/metrics
```

---

## Troubleshooting

### Metrics Not Updating

**Problem:** Metrics show stale data  
**Solution:**
1. Check that application is receiving traffic
2. Verify instrumentation is active in code paths
3. Restart application to reset counters if needed

### High Memory Usage

**Problem:** Prometheus metrics consuming too much memory  
**Solution:**
1. Reduce cardinality of labels (avoid high-cardinality values)
2. Increase scrape interval in Prometheus
3. Set retention limits in Prometheus

### Missing Metrics

**Problem:** Some metrics not appearing in `/api/metrics`  
**Solution:**
1. Ensure code path is executed at least once
2. Check that metric is properly initialized
3. Verify no exceptions during metric recording

---

## Changelog

### Version 1.0.0 (Current)
- Initial metrics implementation
- HTTP request tracking
- External API monitoring
- Cache metrics
- Movie validation metrics
- Rate limiter tracking
- LLM performance metrics
- Session metrics

### Future Enhancements
- Database query metrics
- User interaction metrics (likes/dislikes/watchlist)
- Recommendation quality metrics
- Custom business metrics
- Distributed tracing integration

---

## Support

For questions or issues with metrics:
1. Check application logs for errors
2. Verify Prometheus can reach the endpoint
3. Review security policies (firewall, authentication)
4. Open an issue on GitHub with relevant details

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [prometheus_client Python Library](https://github.com/prometheus/client_python)
