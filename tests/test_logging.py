"""
Tests for Structured Logging

Tests the structured logging functionality including:
- Log output format
- Sensitive data scrubbing
- Request/session ID propagation
- Context management
"""

import unittest
import json
import os
import sys
from io import StringIO
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.logging_config import (
    scrub_sensitive_data,
    get_logger,
    configure_structlog,
)
from cineman.logging_context import (
    set_request_id,
    get_request_id,
    set_session_id,
    get_session_id,
    clear_context,
    bind_context,
)


class TestSensitiveDataScrubbing(unittest.TestCase):
    """Test cases for sensitive data scrubbing."""
    
    def test_scrub_api_key_field(self):
        """Test that api_key fields are redacted."""
        data = {"api_key": "secret123456789012345", "user": "john"}
        scrubbed = scrub_sensitive_data(data)
        
        self.assertEqual(scrubbed["api_key"], "[REDACTED]")
        self.assertEqual(scrubbed["user"], "john")
    
    def test_scrub_multiple_sensitive_fields(self):
        """Test scrubbing multiple sensitive fields."""
        data = {
            "api_key": "secret1",
            "password": "secret2",
            "token": "secret3",
            "safe_field": "visible"
        }
        scrubbed = scrub_sensitive_data(data)
        
        self.assertEqual(scrubbed["api_key"], "[REDACTED]")
        self.assertEqual(scrubbed["password"], "[REDACTED]")
        self.assertEqual(scrubbed["token"], "[REDACTED]")
        self.assertEqual(scrubbed["safe_field"], "visible")
    
    def test_scrub_nested_dict(self):
        """Test scrubbing in nested dictionaries."""
        data = {
            "outer": {
                "inner": {
                    "api_key": "secret123",
                    "public": "visible"
                }
            }
        }
        scrubbed = scrub_sensitive_data(data)
        
        self.assertEqual(scrubbed["outer"]["inner"]["api_key"], "[REDACTED]")
        self.assertEqual(scrubbed["outer"]["inner"]["public"], "visible")
    
    def test_scrub_list_of_dicts(self):
        """Test scrubbing in lists of dictionaries."""
        data = {
            "items": [
                {"api_key": "secret1", "name": "item1"},
                {"api_key": "secret2", "name": "item2"}
            ]
        }
        scrubbed = scrub_sensitive_data(data)
        
        self.assertEqual(scrubbed["items"][0]["api_key"], "[REDACTED]")
        self.assertEqual(scrubbed["items"][1]["api_key"], "[REDACTED]")
        self.assertEqual(scrubbed["items"][0]["name"], "item1")
    
    def test_scrub_email_in_string(self):
        """Test email scrubbing in string values."""
        data = {
            "message": "Contact user@example.com for details",
            "info": "No email here"
        }
        scrubbed = scrub_sensitive_data(data)
        
        self.assertIn("[EMAIL_REDACTED]", scrubbed["message"])
        self.assertNotIn("user@example.com", scrubbed["message"])
        self.assertEqual(scrubbed["info"], "No email here")
    
    def test_scrub_api_key_in_string(self):
        """Test API key pattern scrubbing in strings."""
        data = {
            "message": "api_key=AIzaSyABC123456789012345678901234567890"
        }
        scrubbed = scrub_sensitive_data(data)
        
        self.assertIn("[REDACTED]", scrubbed["message"])
        self.assertNotIn("AIzaSyABC", scrubbed["message"])
    
    def test_scrub_non_string_values(self):
        """Test scrubbing with non-string values."""
        data = {
            "count": 123,
            "active": True,
            "api_key": 999,  # Even numeric api_key should be redacted
            "items": [1, 2, 3]
        }
        scrubbed = scrub_sensitive_data(data)
        
        self.assertEqual(scrubbed["count"], 123)
        self.assertEqual(scrubbed["active"], True)
        self.assertEqual(scrubbed["api_key"], "[REDACTED]")
        self.assertEqual(scrubbed["items"], [1, 2, 3])


class TestContextManagement(unittest.TestCase):
    """Test cases for context management."""
    
    def setUp(self):
        """Clear context before each test."""
        clear_context()
    
    def tearDown(self):
        """Clear context after each test."""
        clear_context()
    
    def test_set_and_get_request_id(self):
        """Test setting and getting request ID."""
        request_id = set_request_id("test-request-123")
        
        self.assertEqual(request_id, "test-request-123")
        self.assertEqual(get_request_id(), "test-request-123")
    
    def test_generate_request_id(self):
        """Test automatic request ID generation."""
        request_id = set_request_id()
        
        self.assertIsNotNone(request_id)
        self.assertGreater(len(request_id), 0)
        self.assertEqual(get_request_id(), request_id)
    
    def test_set_and_get_session_id(self):
        """Test setting and getting session ID."""
        session_id = set_session_id("test-session-456")
        
        self.assertEqual(session_id, "test-session-456")
        self.assertEqual(get_session_id(), "test-session-456")
    
    def test_clear_context(self):
        """Test clearing context."""
        set_request_id("test-request")
        set_session_id("test-session")
        
        self.assertIsNotNone(get_request_id())
        self.assertIsNotNone(get_session_id())
        
        clear_context()
        
        self.assertIsNone(get_request_id())
        self.assertIsNone(get_session_id())
    
    def test_bind_additional_context(self):
        """Test binding additional context variables."""
        bind_context(user_id="user123", feature="premium")
        
        # Context should be available in subsequent logs
        # We can't directly test structlog context, but we verify no errors
        logger = get_logger(__name__)
        logger.info("test_event")  # Should not raise


class TestLoggingConfiguration(unittest.TestCase):
    """Test cases for logging configuration."""
    
    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger(__name__)
        
        self.assertIsNotNone(logger)
        # Verify it has logging methods
        self.assertTrue(hasattr(logger, 'info'))
        self.assertTrue(hasattr(logger, 'error'))
        self.assertTrue(hasattr(logger, 'debug'))
        self.assertTrue(hasattr(logger, 'warning'))
    
    def test_configure_structlog(self):
        """Test structlog configuration."""
        # Should not raise
        configure_structlog()
        
        logger = get_logger(__name__)
        self.assertIsNotNone(logger)
    
    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"})
    def test_log_level_configuration(self):
        """Test log level configuration via environment."""
        # Reconfigure with new environment
        configure_structlog()
        
        logger = get_logger(__name__)
        # Should be able to log at DEBUG level
        logger.debug("debug_message")  # Should not raise


class TestLoggingOutput(unittest.TestCase):
    """Test cases for logging output format."""
    
    @patch.dict(os.environ, {"FLASK_ENV": "production"})
    def test_json_output_format(self):
        """Test JSON output format in production mode."""
        # Reconfigure for production
        configure_structlog()
        
        # Capture output
        with patch('sys.stdout', new=StringIO()) as fake_out:
            logger = get_logger(__name__)
            logger.info("test_event", field1="value1", field2=123)
            
            output = fake_out.getvalue()
            
            # Should be valid JSON
            try:
                log_entry = json.loads(output.strip())
                self.assertEqual(log_entry["event"], "test_event")
                self.assertEqual(log_entry["field1"], "value1")
                self.assertEqual(log_entry["field2"], 123)
                self.assertEqual(log_entry["level"], "info")
                self.assertIn("timestamp", log_entry)
                self.assertEqual(log_entry["service"], "cineman")
            except json.JSONDecodeError:
                self.fail("Output is not valid JSON")
    
    def test_log_includes_service_name(self):
        """Test that all logs include service name."""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            logger = get_logger(__name__)
            logger.info("test_event")
            
            output = fake_out.getvalue()
            
            # Parse as JSON (production mode) or check string (dev mode)
            if output.startswith('{'):
                log_entry = json.loads(output.strip())
                self.assertEqual(log_entry["service"], "cineman")
            else:
                self.assertIn("service=cineman", output)
    
    def test_log_includes_environment(self):
        """Test that logs include environment field."""
        with patch('sys.stdout', new=StringIO()) as fake_out:
            logger = get_logger(__name__)
            logger.info("test_event")
            
            output = fake_out.getvalue()
            
            # Should include environment field
            if output.startswith('{'):
                log_entry = json.loads(output.strip())
                self.assertIn("environment", log_entry)
            else:
                self.assertIn("environment=", output)


class TestRequestTracePropagation(unittest.TestCase):
    """Test cases for request trace propagation."""
    
    def setUp(self):
        """Clear context before each test."""
        clear_context()
    
    def tearDown(self):
        """Clear context after each test."""
        clear_context()
    
    def test_request_id_in_logs(self):
        """Test that request ID appears in logs."""
        set_request_id("trace-123")
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            logger = get_logger(__name__)
            logger.info("test_event")
            
            output = fake_out.getvalue()
            
            # Check for request ID in output
            if output.startswith('{'):
                log_entry = json.loads(output.strip())
                self.assertEqual(log_entry.get("request_id"), "trace-123")
            else:
                self.assertIn("request_id=trace-123", output)
    
    def test_session_id_in_logs(self):
        """Test that session ID appears in logs."""
        set_session_id("session-456")
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            logger = get_logger(__name__)
            logger.info("test_event")
            
            output = fake_out.getvalue()
            
            # Check for session ID in output
            if output.startswith('{'):
                log_entry = json.loads(output.strip())
                self.assertEqual(log_entry.get("session_id"), "session-456")
            else:
                self.assertIn("session_id=session-456", output)
    
    def test_multiple_logs_same_context(self):
        """Test that multiple logs share the same context."""
        request_id = set_request_id("trace-789")
        
        with patch('sys.stdout', new=StringIO()) as fake_out:
            logger = get_logger(__name__)
            logger.info("event1")
            logger.info("event2")
            
            output = fake_out.getvalue()
            lines = output.strip().split('\n')
            
            # Both logs should have the same request_id
            for line in lines:
                if line.startswith('{'):
                    log_entry = json.loads(line)
                    self.assertEqual(log_entry.get("request_id"), "trace-789")
                else:
                    self.assertIn("request_id=trace-789", line)


if __name__ == '__main__':
    unittest.main()
