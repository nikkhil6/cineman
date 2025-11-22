"""
Tests for Rate Limiter

Tests the rate limiting functionality for Gemini API calls.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.rate_limiter import RateLimiter, APIUsageTracker, get_gemini_rate_limiter
from cineman.models import db


class TestRateLimiter(unittest.TestCase):
    """Test cases for rate limiter functionality."""
    
    def setUp(self):
        """Set up test Flask app and database."""
        from cineman.app import app
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
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        with self.app.app_context():
            limiter = RateLimiter(api_name="test_api", daily_limit=10)
            
            self.assertEqual(limiter.api_name, "test_api")
            self.assertEqual(limiter.daily_limit, 10)
    
    def test_check_limit_initial_state(self):
        """Test rate limit check in initial state."""
        with self.app.app_context():
            limiter = RateLimiter(api_name="test_api", daily_limit=5)
            
            allowed, remaining, error_msg = limiter.check_limit()
            
            self.assertTrue(allowed)
            self.assertEqual(remaining, 5)
            self.assertIsNone(error_msg)
    
    def test_increment_counter(self):
        """Test incrementing the API call counter."""
        with self.app.app_context():
            limiter = RateLimiter(api_name="test_api", daily_limit=5)
            
            # Initial check
            allowed, remaining, _ = limiter.check_limit()
            self.assertEqual(remaining, 5)
            
            # Increment once
            limiter.increment()
            
            # Check again
            allowed, remaining, _ = limiter.check_limit()
            self.assertEqual(remaining, 4)
    
    def test_limit_enforcement(self):
        """Test that limit is enforced correctly."""
        with self.app.app_context():
            limiter = RateLimiter(api_name="test_api", daily_limit=3)
            
            # Make 3 calls (at limit)
            for i in range(3):
                allowed, remaining, error_msg = limiter.check_limit()
                self.assertTrue(allowed)
                self.assertEqual(remaining, 3 - i)
                self.assertIsNone(error_msg)
                limiter.increment()
            
            # 4th call should be blocked
            allowed, remaining, error_msg = limiter.check_limit()
            self.assertFalse(allowed)
            self.assertEqual(remaining, 0)
            self.assertIsNotNone(error_msg)
            self.assertIn("Daily API limit reached", error_msg)
    
    def test_usage_stats(self):
        """Test getting usage statistics."""
        with self.app.app_context():
            limiter = RateLimiter(api_name="test_api", daily_limit=10)
            
            # Make some calls
            limiter.increment()
            limiter.increment()
            
            stats = limiter.get_usage_stats()
            
            self.assertEqual(stats['call_count'], 2)
            self.assertEqual(stats['daily_limit'], 10)
            self.assertEqual(stats['remaining'], 8)
            self.assertIn('reset_date', stats)
            self.assertEqual(stats['status'], 'active')
    
    def test_manual_reset(self):
        """Test manual reset of counter."""
        with self.app.app_context():
            limiter = RateLimiter(api_name="test_api", daily_limit=5)
            
            # Make some calls
            limiter.increment()
            limiter.increment()
            limiter.increment()
            
            # Check counter
            stats = limiter.get_usage_stats()
            self.assertEqual(stats['call_count'], 3)
            
            # Reset
            limiter.reset()
            
            # Check counter again
            stats = limiter.get_usage_stats()
            self.assertEqual(stats['call_count'], 0)
            self.assertEqual(stats['remaining'], 5)
    
    def test_auto_reset_at_midnight(self):
        """Test automatic reset at midnight."""
        with self.app.app_context():
            limiter = RateLimiter(api_name="test_api", daily_limit=5)
            
            # Make some calls
            limiter.increment()
            limiter.increment()
            
            # Get tracker and manually set reset_date to past
            tracker = APIUsageTracker.query.filter_by(api_name="test_api").first()
            tracker.reset_date = datetime.utcnow() - timedelta(days=1)
            db.session.commit()
            
            # Next check should trigger reset
            allowed, remaining, _ = limiter.check_limit()
            
            self.assertTrue(allowed)
            self.assertEqual(remaining, 5)  # Counter should be reset
            
            # Verify in database
            stats = limiter.get_usage_stats()
            self.assertEqual(stats['call_count'], 0)
    
    def test_multiple_apis_separate_limits(self):
        """Test that different APIs have separate limits."""
        with self.app.app_context():
            limiter1 = RateLimiter(api_name="api1", daily_limit=5)
            limiter2 = RateLimiter(api_name="api2", daily_limit=10)
            
            # Increment first API
            limiter1.increment()
            limiter1.increment()
            
            # Increment second API
            limiter2.increment()
            
            # Check stats
            stats1 = limiter1.get_usage_stats()
            stats2 = limiter2.get_usage_stats()
            
            self.assertEqual(stats1['call_count'], 2)
            self.assertEqual(stats1['remaining'], 3)
            
            self.assertEqual(stats2['call_count'], 1)
            self.assertEqual(stats2['remaining'], 9)
    
    def test_get_gemini_rate_limiter(self):
        """Test getting the global Gemini rate limiter."""
        with self.app.app_context():
            # Clear global instance to ensure clean state
            import cineman.rate_limiter as rl_module
            rl_module.gemini_rate_limiter = None
            
            # Clear any environment override
            if 'GEMINI_DAILY_LIMIT' in os.environ:
                del os.environ['GEMINI_DAILY_LIMIT']
            
            limiter = get_gemini_rate_limiter()
            
            self.assertIsNotNone(limiter)
            self.assertEqual(limiter.api_name, "gemini")
            self.assertEqual(limiter.daily_limit, 50)  # Default limit
    
    @patch.dict(os.environ, {'GEMINI_DAILY_LIMIT': '100'})
    def test_gemini_rate_limiter_custom_limit(self):
        """Test custom limit via environment variable."""
        with self.app.app_context():
            # Clear global instance to force re-creation
            import cineman.rate_limiter as rl_module
            rl_module.gemini_rate_limiter = None
            
            limiter = get_gemini_rate_limiter()
            
            self.assertEqual(limiter.daily_limit, 100)


class TestRateLimitEndpoint(unittest.TestCase):
    """Test cases for rate limit API endpoint."""
    
    def setUp(self):
        """Set up test Flask app."""
        from cineman.app import app
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
    
    def test_rate_limit_status_endpoint(self):
        """Test /api/rate-limit endpoint."""
        with self.app.app_context():
            response = self.client.get('/api/rate-limit')
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            
            self.assertEqual(data['status'], 'success')
            self.assertIn('usage', data)
            self.assertIn('call_count', data['usage'])
            self.assertIn('daily_limit', data['usage'])
            self.assertIn('remaining', data['usage'])
            self.assertIn('reset_date', data['usage'])
    
    def test_chat_endpoint_with_rate_limit(self):
        """Test /chat endpoint respects rate limiting."""
        with self.app.app_context():
            # First check if chain is initialized
            # If not, we can't test rate limiting as it's checked after chain initialization
            test_response = self.client.post('/chat', json={'message': 'Test'})
            if test_response.status_code == 503:
                # Chain not initialized - skip this test
                self.skipTest("Chain not initialized - cannot test rate limiting integration")
            
            # Set a very low limit for testing
            from cineman.rate_limiter import get_gemini_rate_limiter
            limiter = get_gemini_rate_limiter()
            
            # Manually set the limit to 1 for testing
            tracker = APIUsageTracker.query.filter_by(api_name="gemini").first()
            if not tracker:
                tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                tracker = APIUsageTracker(
                    api_name="gemini",
                    call_count=0,
                    reset_date=tomorrow
                )
                db.session.add(tracker)
                db.session.commit()
            
            # Set to limit (50 calls made)
            tracker.call_count = 50
            db.session.commit()
            
            # Call should be rate limited
            response = self.client.post('/chat', json={'message': 'Test message'})
            self.assertEqual(response.status_code, 429)
            
            data = response.get_json()
            self.assertIn('rate_limit_exceeded', data)
            self.assertTrue(data['rate_limit_exceeded'])
            self.assertEqual(data['remaining_calls'], 0)


if __name__ == '__main__':
    unittest.main()
