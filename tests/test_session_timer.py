"""
Tests for Session Timer Feature

Tests the session timeout information endpoint and timer functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta


class TestSessionTimerEndpoint(unittest.TestCase):
    """Test cases for the session timeout endpoint."""
    
    def setUp(self):
        """Set up test Flask app."""
        from cineman.app import app
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
    
    def test_no_session(self):
        """Test /api/session/timeout with no active session."""
        response = self.client.get('/api/session/timeout')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data['status'], 'success')
        self.assertFalse(data['session_exists'])
        self.assertEqual(data['timeout_seconds'], 3600)
        self.assertEqual(data['remaining_seconds'], 3600)
    
    @patch('cineman.session_manager.get_session_manager')
    def test_active_session(self, mock_get_manager):
        """Test /api/session/timeout with an active session."""
        # Mock session manager and session data
        mock_manager = MagicMock()
        mock_session_data = MagicMock()
        mock_session_data.last_accessed = datetime.now() - timedelta(minutes=10)
        
        mock_manager.get_session.return_value = mock_session_data
        mock_manager.session_timeout = timedelta(minutes=60)
        mock_get_manager.return_value = mock_manager
        
        # Create a session
        with self.client.session_transaction() as sess:
            sess['session_id'] = 'test-session-id'
        
        response = self.client.get('/api/session/timeout')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['session_exists'])
        self.assertEqual(data['timeout_seconds'], 3600)
        # Should have ~50 minutes remaining (60 - 10)
        self.assertGreater(data['remaining_seconds'], 2900)
        self.assertLess(data['remaining_seconds'], 3100)
    
    @patch('cineman.session_manager.get_session_manager')
    def test_expired_session(self, mock_get_manager):
        """Test /api/session/timeout with an expired session."""
        # Mock session manager returning None (expired session)
        mock_manager = MagicMock()
        mock_manager.get_session.return_value = None
        mock_get_manager.return_value = mock_manager
        
        # Create a session
        with self.client.session_transaction() as sess:
            sess['session_id'] = 'expired-session-id'
        
        response = self.client.get('/api/session/timeout')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data['status'], 'success')
        self.assertFalse(data['session_exists'])
        self.assertEqual(data['timeout_seconds'], 3600)
    
    @patch('cineman.session_manager.get_session_manager')
    def test_session_near_expiry(self, mock_get_manager):
        """Test /api/session/timeout when session is about to expire."""
        # Mock session that's been active for 59 minutes
        mock_manager = MagicMock()
        mock_session_data = MagicMock()
        mock_session_data.last_accessed = datetime.now() - timedelta(minutes=59)
        
        mock_manager.get_session.return_value = mock_session_data
        mock_manager.session_timeout = timedelta(minutes=60)
        mock_get_manager.return_value = mock_manager
        
        with self.client.session_transaction() as sess:
            sess['session_id'] = 'test-session-id'
        
        response = self.client.get('/api/session/timeout')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertTrue(data['session_exists'])
        # Should have ~1 minute remaining
        self.assertGreater(data['remaining_seconds'], 0)
        self.assertLess(data['remaining_seconds'], 120)
    
    @patch('cineman.session_manager.get_session_manager')
    def test_multiple_requests_update_timer(self, mock_get_manager):
        """Test that timer reflects session activity."""
        # First request - session 30 minutes old
        mock_manager = MagicMock()
        mock_session_data = MagicMock()
        mock_session_data.last_accessed = datetime.now() - timedelta(minutes=30)
        
        mock_manager.get_session.return_value = mock_session_data
        mock_manager.session_timeout = timedelta(minutes=60)
        mock_get_manager.return_value = mock_manager
        
        with self.client.session_transaction() as sess:
            sess['session_id'] = 'test-session-id'
        
        response1 = self.client.get('/api/session/timeout')
        data1 = response1.get_json()
        
        # Simulate session activity - update last_accessed
        mock_session_data.last_accessed = datetime.now() - timedelta(minutes=5)
        
        response2 = self.client.get('/api/session/timeout')
        data2 = response2.get_json()
        
        # Second request should show more remaining time
        self.assertGreater(data2['remaining_seconds'], data1['remaining_seconds'])


class TestSessionTimerIntegration(unittest.TestCase):
    """Integration tests for session timer with real session manager."""
    
    def setUp(self):
        """Set up test Flask app with real session manager."""
        from cineman.app import app
        from cineman.session_manager import SessionManager
        
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        
        # Create a test session manager with short timeout
        self.test_manager = SessionManager(session_timeout_minutes=1)
    
    @patch('cineman.session_manager.get_session_manager')
    def test_real_session_timeout_calculation(self, mock_get_manager):
        """Test with real session manager and timeout calculation."""
        mock_get_manager.return_value = self.test_manager
        
        # Create a session through the manager
        session_id = self.test_manager.create_session()
        
        with self.client.session_transaction() as sess:
            sess['session_id'] = session_id
        
        response = self.client.get('/api/session/timeout')
        data = response.get_json()
        
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['session_exists'])
        self.assertEqual(data['timeout_seconds'], 60)  # 1 minute
        # Should have close to full time remaining
        self.assertGreater(data['remaining_seconds'], 55)
        self.assertLessEqual(data['remaining_seconds'], 60)


if __name__ == '__main__':
    unittest.main()
