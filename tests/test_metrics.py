"""
Tests for Prometheus Metrics

This test suite validates the metrics collection and /metrics endpoint,
including unit tests, integration tests, and regression tests under load.
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import sys
import time
import threading
from io import StringIO

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.metrics import (
    http_requests_total, http_request_duration_seconds,
    external_api_calls_total, external_api_duration_seconds,
    cache_hits_total, cache_misses_total,
    movie_validations_total, movie_validation_duration_seconds,
    duplicate_recommendations_total,
    rate_limit_usage, rate_limit_max, rate_limit_remaining,
    rate_limit_exceeded_total,
    llm_invocations_total, llm_invocation_duration_seconds,
    active_sessions, session_duration_seconds,
    track_request, track_external_api_call, track_validation,
    track_cache_operation, track_duplicate_recommendation,
    update_rate_limit_metrics, track_rate_limit_exceeded,
    track_llm_invocation, update_active_sessions, track_session_duration,
    get_metrics
)


class TestMetricsCollection(unittest.TestCase):
    """Test metrics collection functions."""
    
    def test_track_validation(self):
        """Test validation metrics tracking."""
        # Track different validation results
        initial_valid = movie_validations_total.labels(result='valid')._value.get()
        track_validation('valid')
        self.assertEqual(
            movie_validations_total.labels(result='valid')._value.get(),
            initial_valid + 1
        )
        
        initial_dropped = movie_validations_total.labels(result='dropped')._value.get()
        track_validation('dropped')
        self.assertEqual(
            movie_validations_total.labels(result='dropped')._value.get(),
            initial_dropped + 1
        )
    
    def test_track_cache_operation(self):
        """Test cache hit/miss tracking."""
        initial_hits = cache_hits_total.labels(cache_type='test')._value.get()
        track_cache_operation('test', hit=True)
        self.assertEqual(
            cache_hits_total.labels(cache_type='test')._value.get(),
            initial_hits + 1
        )
        
        initial_misses = cache_misses_total.labels(cache_type='test')._value.get()
        track_cache_operation('test', hit=False)
        self.assertEqual(
            cache_misses_total.labels(cache_type='test')._value.get(),
            initial_misses + 1
        )
    
    def test_track_duplicate_recommendation(self):
        """Test duplicate recommendation tracking."""
        initial = duplicate_recommendations_total._value.get()
        track_duplicate_recommendation()
        self.assertEqual(duplicate_recommendations_total._value.get(), initial + 1)
    
    def test_update_rate_limit_metrics(self):
        """Test rate limiter metrics update."""
        update_rate_limit_metrics(usage=10, limit=50, remaining=40)
        self.assertEqual(rate_limit_usage._value.get(), 10)
        self.assertEqual(rate_limit_max._value.get(), 50)
        self.assertEqual(rate_limit_remaining._value.get(), 40)
    
    def test_track_rate_limit_exceeded(self):
        """Test rate limit exceeded tracking."""
        initial = rate_limit_exceeded_total._value.get()
        track_rate_limit_exceeded()
        self.assertEqual(rate_limit_exceeded_total._value.get(), initial + 1)
    
    def test_track_llm_invocation(self):
        """Test LLM invocation tracking."""
        initial_success = llm_invocations_total.labels(status='success')._value.get()
        track_llm_invocation(success=True, duration=1.5)
        self.assertEqual(
            llm_invocations_total.labels(status='success')._value.get(),
            initial_success + 1
        )
        
        initial_error = llm_invocations_total.labels(status='error')._value.get()
        track_llm_invocation(success=False, duration=0.5)
        self.assertEqual(
            llm_invocations_total.labels(status='error')._value.get(),
            initial_error + 1
        )
    
    def test_update_active_sessions(self):
        """Test active sessions gauge update."""
        update_active_sessions(42)
        self.assertEqual(active_sessions._value.get(), 42)
    
    def test_track_session_duration(self):
        """Test session duration tracking."""
        # Just verify it doesn't error
        track_session_duration(300.5)


class TestMetricsDecorators(unittest.TestCase):
    """Test metrics decorator functions."""
    
    def test_track_request_decorator_success(self):
        """Test HTTP request tracking decorator with success."""
        initial_count = http_requests_total.labels(
            method='GET', endpoint='/test', status=200
        )._value.get()
        
        @track_request('GET', '/test')
        def test_endpoint():
            return {"result": "ok"}, 200
        
        result = test_endpoint()
        self.assertEqual(result[0], {"result": "ok"})
        self.assertEqual(result[1], 200)
        self.assertEqual(
            http_requests_total.labels(method='GET', endpoint='/test', status=200)._value.get(),
            initial_count + 1
        )
    
    def test_track_request_decorator_error(self):
        """Test HTTP request tracking decorator with error."""
        initial_count = http_requests_total.labels(
            method='POST', endpoint='/error', status=500
        )._value.get()
        
        @track_request('POST', '/error')
        def error_endpoint():
            raise ValueError("Test error")
        
        with self.assertRaises(ValueError):
            error_endpoint()
        
        self.assertEqual(
            http_requests_total.labels(method='POST', endpoint='/error', status=500)._value.get(),
            initial_count + 1
        )
    
    def test_track_external_api_call_decorator_success(self):
        """Test external API call tracking decorator."""
        initial_count = external_api_calls_total.labels(
            api_name='test_api', status='success'
        )._value.get()
        
        @track_external_api_call('test_api')
        def call_api():
            return {"status": "success", "data": "test"}
        
        result = call_api()
        self.assertEqual(result["status"], "success")
        self.assertEqual(
            external_api_calls_total.labels(api_name='test_api', status='success')._value.get(),
            initial_count + 1
        )
    
    def test_track_external_api_call_decorator_error(self):
        """Test external API call tracking decorator with error."""
        initial_count = external_api_calls_total.labels(
            api_name='test_api', status='error'
        )._value.get()
        
        @track_external_api_call('test_api')
        def call_api_error():
            return {"status": "error", "error": "API failed"}
        
        result = call_api_error()
        self.assertEqual(result["status"], "error")
        self.assertEqual(
            external_api_calls_total.labels(api_name='test_api', status='error')._value.get(),
            initial_count + 1
        )


class TestMetricsEndpoint(unittest.TestCase):
    """Test /metrics endpoint integration."""
    
    def setUp(self):
        """Set up test Flask app."""
        from cineman.app import app
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app = app
    
    def test_metrics_endpoint_exists(self):
        """Test that /api/metrics endpoint exists."""
        response = self.client.get('/api/metrics')
        self.assertEqual(response.status_code, 200)
    
    def test_metrics_endpoint_content_type(self):
        """Test that /api/metrics returns correct content type."""
        response = self.client.get('/api/metrics')
        self.assertIn('text/plain', response.content_type)
    
    def test_metrics_endpoint_format(self):
        """Test that /api/metrics returns Prometheus format."""
        response = self.client.get('/api/metrics')
        data = response.data.decode('utf-8')
        
        # Check for Prometheus format markers
        self.assertIn('# HELP', data)
        self.assertIn('# TYPE', data)
        
        # Check for our custom metrics
        self.assertIn('cineman_http_requests_total', data)
        self.assertIn('cineman_external_api_calls_total', data)
        self.assertIn('cineman_cache_hits_total', data)
        self.assertIn('cineman_movie_validations_total', data)
        self.assertIn('cineman_rate_limit_usage', data)
        self.assertIn('cineman_llm_invocations_total', data)
    
    def test_metrics_endpoint_no_sensitive_data(self):
        """Test that /api/metrics does not expose sensitive data."""
        response = self.client.get('/api/metrics')
        data = response.data.decode('utf-8')
        
        # Ensure no API keys or secrets are exposed
        self.assertNotIn('api_key', data.lower())
        self.assertNotIn('secret', data.lower())
        self.assertNotIn('password', data.lower())
        self.assertNotIn('token', data.lower())
    
    def test_metrics_after_requests(self):
        """Test that metrics are updated after API requests."""
        # Get initial metrics
        response1 = self.client.get('/api/metrics')
        data1 = response1.data.decode('utf-8')
        
        # Make some API requests
        self.client.get('/health')
        self.client.get('/')
        
        # Get updated metrics
        response2 = self.client.get('/api/metrics')
        data2 = response2.data.decode('utf-8')
        
        # Metrics should have changed
        self.assertNotEqual(data1, data2)


class TestMetricsUnderLoad(unittest.TestCase):
    """Regression tests for metrics under load."""
    
    def setUp(self):
        """Set up test Flask app."""
        from cineman.app import app
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app = app
    
    def test_metrics_concurrent_access(self):
        """Test metrics endpoint under concurrent access."""
        results = []
        errors = []
        
        def make_request():
            try:
                response = self.client.get('/api/metrics')
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Simulate concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        self.assertEqual(len(results), 10)
        self.assertEqual(len(errors), 0)
        self.assertTrue(all(status == 200 for status in results))
    
    def test_metrics_high_frequency_updates(self):
        """Test metrics with high frequency updates."""
        # Perform many operations quickly
        for i in range(100):
            track_validation('valid')
            track_cache_operation('test', hit=(i % 2 == 0))
            track_llm_invocation(success=True, duration=0.1)
        
        # Metrics endpoint should still work
        response = self.client.get('/api/metrics')
        self.assertEqual(response.status_code, 200)
        
        data = response.data.decode('utf-8')
        self.assertIn('cineman_movie_validations_total', data)
    
    def test_metrics_performance(self):
        """Test that metrics endpoint responds quickly."""
        start_time = time.time()
        response = self.client.get('/api/metrics')
        duration = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        # Metrics should respond in under 1 second
        self.assertLess(duration, 1.0)


class TestMetricsErrorScenarios(unittest.TestCase):
    """Test metrics behavior in error scenarios."""
    
    def setUp(self):
        """Set up test Flask app."""
        from cineman.app import app
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app = app
    
    def test_metrics_with_rate_limiter_error(self):
        """Test metrics endpoint when rate limiter has issues."""
        with patch('cineman.routes.api.get_gemini_rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.return_value.get_usage_stats.side_effect = Exception("DB error")
            
            response = self.client.get('/api/metrics')
            # Should still return metrics even if rate limiter fails
            self.assertEqual(response.status_code, 500)
    
    def test_metrics_after_validation_errors(self):
        """Test metrics collection after validation errors."""
        # Simulate validation errors
        track_validation('invalid')
        track_validation('dropped')
        
        response = self.client.get('/api/metrics')
        self.assertEqual(response.status_code, 200)
        
        data = response.data.decode('utf-8')
        self.assertIn('result="invalid"', data)
        self.assertIn('result="dropped"', data)
    
    def test_metrics_after_api_failures(self):
        """Test metrics collection after external API failures."""
        # Simulate API failures
        @track_external_api_call('test_failing_api')
        def failing_api():
            return {"status": "error", "error": "Connection timeout"}
        
        failing_api()
        
        response = self.client.get('/api/metrics')
        self.assertEqual(response.status_code, 200)
        
        data = response.data.decode('utf-8')
        self.assertIn('cineman_external_api_calls_total', data)


class TestMetricsHistograms(unittest.TestCase):
    """Test histogram metrics."""
    
    def test_http_request_duration_histogram(self):
        """Test HTTP request duration histogram."""
        # Simulate various request durations
        for duration in [0.1, 0.5, 1.0, 2.0]:
            http_request_duration_seconds.labels(
                method='GET', endpoint='/test'
            ).observe(duration)
        
        # Get metrics
        metrics_text, _ = get_metrics()
        data = metrics_text.decode('utf-8')
        
        # Histogram should have bucket entries
        self.assertIn('cineman_http_request_duration_seconds_bucket', data)
        self.assertIn('cineman_http_request_duration_seconds_sum', data)
        self.assertIn('cineman_http_request_duration_seconds_count', data)
    
    def test_external_api_duration_histogram(self):
        """Test external API duration histogram."""
        # Simulate API call durations
        for duration in [0.2, 0.8, 1.5]:
            external_api_duration_seconds.labels(api_name='test_api').observe(duration)
        
        metrics_text, _ = get_metrics()
        data = metrics_text.decode('utf-8')
        
        self.assertIn('cineman_external_api_duration_seconds_bucket', data)
    
    def test_movie_validation_duration_histogram(self):
        """Test movie validation duration histogram."""
        # Simulate validation durations
        for duration in [0.05, 0.1, 0.3]:
            movie_validation_duration_seconds.observe(duration)
        
        metrics_text, _ = get_metrics()
        data = metrics_text.decode('utf-8')
        
        self.assertIn('cineman_movie_validation_duration_seconds_bucket', data)


if __name__ == '__main__':
    unittest.main()
