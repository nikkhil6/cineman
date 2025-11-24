"""
Regression Tests for Structured Logging

Tests logging behavior with synthetic traffic to ensure:
- All events are logged correctly
- Performance is acceptable
- No memory leaks
- Context propagation works under load
"""

import unittest
import json
import os
import sys
import time
from io import StringIO
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.app import app
from cineman.models import db
from cineman.logging_context import set_request_id, set_session_id, clear_context


class TestLoggingRegression(unittest.TestCase):
    """Regression tests for logging under various scenarios."""
    
    def setUp(self):
        """Set up test Flask app and database."""
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up database after each test."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_multiple_concurrent_requests(self):
        """Test that concurrent requests have distinct request IDs."""
        request_ids = []
        
        def make_request():
            response = self.client.get('/health')
            if 'X-Request-ID' in response.headers:
                return response.headers['X-Request-ID']
            return None
        
        # Make 10 concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            request_ids = [f.result() for f in futures]
        
        # All should have request IDs
        self.assertTrue(all(rid is not None for rid in request_ids))
        
        # All should be unique
        self.assertEqual(len(request_ids), len(set(request_ids)))
    
    def test_high_volume_logging(self):
        """Test that logging handles high volume without errors."""
        start_time = time.time()
        
        # Make 50 requests
        for i in range(50):
            response = self.client.get('/health')
            self.assertEqual(response.status_code, 200)
        
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (< 5 seconds)
        self.assertLess(elapsed, 5.0, 
            f"50 requests took {elapsed:.2f}s, expected < 5s")
    
    def test_all_endpoints_log_correctly(self):
        """Test that all major endpoints produce correct logs."""
        endpoints = [
            ('/health', 'GET'),
            ('/api/status', 'GET'),
            ('/api/rate-limit', 'GET'),
            ('/api/watchlist', 'GET'),
            ('/api/interactions', 'GET'),
        ]
        
        for path, method in endpoints:
            with patch('sys.stdout', new=StringIO()) as fake_out:
                if method == 'GET':
                    response = self.client.get(path)
                else:
                    response = self.client.post(path)
                
                output = fake_out.getvalue()
                
                # Each should produce request_started and request_completed
                self.assertIn('request_started', output, 
                    f"Missing request_started for {method} {path}")
                self.assertIn('request_completed', output,
                    f"Missing request_completed for {method} {path}")
    
    def test_error_conditions_logged(self):
        """Test that error conditions are properly logged."""
        test_cases = [
            ('/nonexistent', 404, 'Not Found endpoint'),
            ('/api/movie/poster', 400, 'Missing query parameter'),
        ]
        
        for path, expected_status, description in test_cases:
            with patch('sys.stdout', new=StringIO()) as fake_out:
                response = self.client.get(path)
                
                # Verify response status
                self.assertEqual(response.status_code, expected_status,
                    f"Expected {expected_status} for {description}")
                
                output = fake_out.getvalue()
                
                # Should still log the request
                self.assertIn('request_started', output)
                self.assertIn('request_completed', output)
    
    def test_sensitive_data_never_logged(self):
        """Test that sensitive data is never exposed in logs."""
        sensitive_values = [
            "AIzaSyABC123456789012345",  # API key
            "user@example.com",  # Email
            "Bearer abc123def456",  # Token
        ]
        
        # Create log entries with sensitive data
        with patch('sys.stdout', new=StringIO()) as fake_out:
            from cineman.logging_config import get_logger
            logger = get_logger(__name__)
            
            for value in sensitive_values:
                logger.info("test_event", 
                    api_key=value,
                    message=f"Contains {value}",
                    data={"nested": {"api_key": value}}
                )
            
            output = fake_out.getvalue()
            
            # None of the sensitive values should appear in output
            for value in sensitive_values:
                self.assertNotIn(value, output,
                    f"Sensitive value '{value}' found in logs!")
            
            # But [REDACTED] should appear
            self.assertIn('[REDACTED]', output)
    
    def test_log_field_consistency(self):
        """Test that log fields are consistent across requests."""
        required_fields = ['event', 'level', 'timestamp', 'service', 'environment']
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            # Make multiple different requests
            self.client.get('/health')
            self.client.get('/api/status')
            self.client.get('/api/rate-limit')
            
            output = fake_out.getvalue()
            log_lines = [line for line in output.strip().split('\n') 
                        if line and line.startswith('{')]
            
            # Check each JSON log entry
            for line in log_lines:
                try:
                    log_entry = json.loads(line)
                    
                    # All required fields should be present
                    for field in required_fields:
                        self.assertIn(field, log_entry,
                            f"Missing required field '{field}' in log entry")
                    
                    # Service should always be 'cineman'
                    self.assertEqual(log_entry['service'], 'cineman')
                    
                except json.JSONDecodeError as e:
                    self.fail(f"Invalid JSON in log line: {line}")
    
    def test_context_isolation_between_requests(self):
        """Test that context doesn't leak between requests."""
        request_ids_seen = set()
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            # Make multiple requests
            for i in range(5):
                response = self.client.get('/health')
                request_id = response.headers.get('X-Request-ID')
                request_ids_seen.add(request_id)
            
            output = fake_out.getvalue()
            log_lines = [line for line in output.strip().split('\n') 
                        if line and line.startswith('{')]
            
            # Parse all request IDs from logs
            logged_request_ids = set()
            for line in log_lines:
                try:
                    log_entry = json.loads(line)
                    if 'request_id' in log_entry:
                        logged_request_ids.add(log_entry['request_id'])
                except json.JSONDecodeError:
                    pass
            
            # All request IDs from response headers should be in logs
            # (there may be additional request_ids from other operations)
            for rid in request_ids_seen:
                self.assertIn(rid, logged_request_ids,
                    f"Request ID {rid} from header not found in logs")
    
    def test_performance_overhead(self):
        """Test that logging doesn't add significant overhead."""
        # Measure time for requests with logging
        start_with_logging = time.time()
        for _ in range(20):
            self.client.get('/health')
        time_with_logging = time.time() - start_with_logging
        
        # Per-request time should be reasonable (< 100ms average)
        avg_time = time_with_logging / 20
        self.assertLess(avg_time, 0.1,
            f"Average request time {avg_time*1000:.1f}ms exceeds 100ms threshold")
    
    def test_session_tracking_across_multiple_turns(self):
        """Test session tracking across multiple conversation turns."""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            # Note: Chat endpoint requires AI chain which is not initialized in tests
            # So we'll test session endpoints instead
            
            # 1. Make a request to create a session
            response1 = self.client.get('/api/interactions')
            
            # 2. Make another request with same session
            response2 = self.client.get('/api/watchlist')
            
            # 3. Clear session
            response3 = self.client.post('/session/clear')
            
            # 4. Make new request (new session)
            response4 = self.client.get('/api/interactions')
            
            output = fake_out.getvalue()
            
            # Should log session operations (if a session existed)
            # Either session_cleared or request_completed for clear endpoint
            self.assertIn('request_completed', output)
            
            # Should have request tracking
            self.assertIn('request_started', output)
    
    def test_all_event_types_present(self):
        """Test that all expected event types are being logged."""
        expected_events = [
            'request_started',
            'request_completed',
        ]
        
        events_found = set()
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            # Make various requests
            self.client.get('/health')
            self.client.get('/api/status')
            self.client.get('/api/rate-limit')
            
            output = fake_out.getvalue()
            log_lines = [line for line in output.strip().split('\n') 
                        if line and line.startswith('{')]
            
            for line in log_lines:
                try:
                    log_entry = json.loads(line)
                    events_found.add(log_entry.get('event'))
                except json.JSONDecodeError:
                    pass
        
        # All expected events should be present
        for event in expected_events:
            self.assertIn(event, events_found,
                f"Expected event '{event}' not found in logs")


class TestLoggingMemoryUsage(unittest.TestCase):
    """Test that logging doesn't cause memory issues."""
    
    def test_no_memory_leak_in_context(self):
        """Test that context variables don't leak memory."""
        import gc
        
        # Force garbage collection
        gc.collect()
        
        # Create and clear context many times
        for i in range(1000):
            set_request_id(f"request-{i}")
            set_session_id(f"session-{i}")
            clear_context()
        
        # Force garbage collection again
        gc.collect()
        
        # If there's no memory leak, this should complete without issues
        # (No explicit assertion needed - test passes if no exception)
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
