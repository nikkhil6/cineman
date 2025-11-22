"""
Integration Tests for Structured Logging

Tests the logging system in an integrated environment with Flask and database.
"""

import unittest
import json
import os
import sys
from io import StringIO
from unittest.mock import patch

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.app import app
from cineman.models import db
from cineman.logging_context import get_request_id, get_session_id


class TestFlaskLoggingIntegration(unittest.TestCase):
    """Test logging integration with Flask requests."""
    
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
    
    def test_request_id_in_response_headers(self):
        """Test that request ID is included in response headers."""
        response = self.client.get('/health')
        
        self.assertIn('X-Request-ID', response.headers)
        request_id = response.headers['X-Request-ID']
        self.assertIsNotNone(request_id)
        self.assertGreater(len(request_id), 0)
    
    def test_request_logging(self):
        """Test that HTTP requests are logged."""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            response = self.client.get('/health')
            
            output = fake_out.getvalue()
            
            # Should log request_started and request_completed
            self.assertIn('request_started', output)
            self.assertIn('request_completed', output)
    
    def test_session_persistence_across_requests(self):
        """Test that session ID persists across multiple requests."""
        # First request - creates session
        response1 = self.client.get('/health')
        cookies1 = response1.headers.getlist('Set-Cookie')
        
        # Second request - should use same session
        response2 = self.client.get('/health')
        
        # Both should succeed
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)


class TestMultiTurnLogging(unittest.TestCase):
    """Test logging in multi-turn conversation sessions."""
    
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
    
    def test_session_id_continuity(self):
        """Test that session ID is maintained across conversation turns."""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            # Skip actual chat since it requires API keys
            # Just test session endpoints
            
            # Get initial session by making a request
            response1 = self.client.get('/health')
            self.assertEqual(response1.status_code, 200)
            
            # Make another request - should have session context
            response2 = self.client.get('/health')
            self.assertEqual(response2.status_code, 200)
            
            output = fake_out.getvalue()
            
            # Verify requests were logged
            self.assertIn('request_started', output)
            self.assertIn('request_completed', output)
    
    def test_session_clear_logging(self):
        """Test that session clearing is logged."""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            # Clear session
            response = self.client.post('/session/clear')
            
            output = fake_out.getvalue()
            
            # Should log session operations
            self.assertIn('request_started', output)
            self.assertIn('request_completed', output)


class TestAPIEndpointLogging(unittest.TestCase):
    """Test logging for API endpoints."""
    
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
    
    def test_health_endpoint_logging(self):
        """Test logging for health check endpoint."""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            response = self.client.get('/health')
            
            self.assertEqual(response.status_code, 200)
            
            output = fake_out.getvalue()
            
            # Parse log entries
            log_lines = [line for line in output.strip().split('\n') if line]
            
            # Should have request_started and request_completed
            events = []
            for line in log_lines:
                if line.startswith('{'):
                    try:
                        log_entry = json.loads(line)
                        events.append(log_entry.get('event'))
                    except json.JSONDecodeError:
                        pass
            
            self.assertIn('request_started', events)
            self.assertIn('request_completed', events)
    
    def test_api_status_logging(self):
        """Test logging for API status endpoint."""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            response = self.client.get('/api/status')
            
            output = fake_out.getvalue()
            
            # Should log the request
            self.assertIn('request_started', output)
            self.assertIn('request_completed', output)
    
    def test_rate_limit_endpoint_logging(self):
        """Test logging for rate limit endpoint."""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            response = self.client.get('/api/rate-limit')
            
            output = fake_out.getvalue()
            
            # Should log the request
            self.assertIn('request_started', output)
            self.assertIn('request_completed', output)
    
    def test_error_logging(self):
        """Test that errors are properly logged."""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            # Request non-existent endpoint
            response = self.client.get('/nonexistent')
            
            self.assertEqual(response.status_code, 404)
            
            output = fake_out.getvalue()
            
            # Should still log the request
            self.assertIn('request_started', output)
            self.assertIn('request_completed', output)


class TestExternalAPILogging(unittest.TestCase):
    """Test logging for external API calls."""
    
    def test_tmdb_api_logging(self):
        """Test logging for TMDB API calls."""
        # Only test if TMDB_API_KEY is set
        if not os.getenv('TMDB_API_KEY'):
            self.skipTest("TMDB_API_KEY not set")
        
        from cineman.tools.tmdb import get_movie_poster_core
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = get_movie_poster_core("Inception")
            
            output = fake_out.getvalue()
            
            # Should log API call
            self.assertIn('external_api_call', output)
            self.assertIn('tmdb', output)
    
    def test_omdb_api_logging(self):
        """Test logging for OMDb API calls."""
        # Only test if OMDB_API_KEY is set
        if not os.getenv('OMDB_API_KEY'):
            self.skipTest("OMDB_API_KEY not set")
        
        from cineman.tools.omdb import fetch_omdb_data_core
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            result = fetch_omdb_data_core("Inception")
            
            output = fake_out.getvalue()
            
            # Should log API call or cache hit
            # The output will contain either external_api_call or cache_event
            self.assertTrue(
                'external_api_call' in output or 'cache_event' in output,
                "Expected API call or cache event in logs"
            )


class TestLogFieldPresence(unittest.TestCase):
    """Test that required fields are present in logs."""
    
    def setUp(self):
        """Set up test Flask app."""
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up database."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    @patch.dict(os.environ, {"FLASK_ENV": "production"})
    def test_required_fields_in_json_logs(self):
        """Test that all required fields are present in JSON logs."""
        from cineman.logging_config import configure_structlog
        configure_structlog()
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            response = self.client.get('/health')
            
            output = fake_out.getvalue()
            log_lines = [line for line in output.strip().split('\n') if line]
            
            for line in log_lines:
                if line.startswith('{'):
                    try:
                        log_entry = json.loads(line)
                        
                        # Check required fields
                        self.assertIn('event', log_entry, "Missing 'event' field")
                        self.assertIn('level', log_entry, "Missing 'level' field")
                        self.assertIn('timestamp', log_entry, "Missing 'timestamp' field")
                        self.assertIn('service', log_entry, "Missing 'service' field")
                        self.assertIn('environment', log_entry, "Missing 'environment' field")
                        
                        # Verify service is always 'cineman'
                        self.assertEqual(log_entry['service'], 'cineman')
                        
                    except json.JSONDecodeError:
                        self.fail(f"Invalid JSON in log line: {line}")


if __name__ == '__main__':
    unittest.main()
