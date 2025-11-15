"""
Tests for API Status Checker

Tests the health check functionality for external APIs:
- Gemini AI
- TMDB
- OMDB
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.api_status import (
    check_gemini_status,
    check_tmdb_status,
    check_omdb_status,
    check_all_apis
)


class TestAPIStatusChecker(unittest.TestCase):
    """Test cases for API status checker functions."""
    
    @patch('cineman.api_status.requests.get')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'})
    def test_gemini_operational(self, mock_get):
        """Test Gemini API status when operational."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = check_gemini_status()
        
        self.assertEqual(result['status'], 'operational')
        self.assertEqual(result['message'], 'API is operational')
        self.assertIn('response_time', result)
        self.assertGreaterEqual(result['response_time'], 0)
    
    @patch('cineman.api_status.requests.get')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'invalid-key'})
    def test_gemini_invalid_key(self, mock_get):
        """Test Gemini API status with invalid key."""
        # Mock 403 Forbidden response
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response
        
        result = check_gemini_status()
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Invalid API key')
    
    @patch.dict(os.environ, {}, clear=True)
    def test_gemini_no_key(self):
        """Test Gemini API status when key is not configured."""
        result = check_gemini_status()
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'API key not configured')
        self.assertEqual(result['response_time'], 0)
    
    @patch('cineman.api_status.requests.get')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'})
    def test_gemini_timeout(self, mock_get):
        """Test Gemini API status with timeout."""
        # Mock timeout
        mock_get.side_effect = Exception('Timeout')
        
        result = check_gemini_status()
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Connection failed')
    
    @patch('cineman.api_status.requests.get')
    @patch.dict(os.environ, {'TMDB_API_KEY': 'test-key'})
    def test_tmdb_operational(self, mock_get):
        """Test TMDB API status when operational."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = check_tmdb_status()
        
        self.assertEqual(result['status'], 'operational')
        self.assertEqual(result['message'], 'API is operational')
        self.assertIn('response_time', result)
    
    @patch('cineman.api_status.requests.get')
    @patch.dict(os.environ, {'TMDB_API_KEY': 'invalid-key'})
    def test_tmdb_invalid_key(self, mock_get):
        """Test TMDB API status with invalid key."""
        # Mock 401 Unauthorized response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        result = check_tmdb_status()
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Invalid API key')
    
    @patch.dict(os.environ, {}, clear=True)
    def test_tmdb_no_key(self):
        """Test TMDB API status when key is not configured."""
        result = check_tmdb_status()
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'API key not configured')
    
    @patch('cineman.api_status.requests.get')
    @patch.dict(os.environ, {'OMDB_API_KEY': 'test-key'})
    def test_omdb_operational(self, mock_get):
        """Test OMDB API status when operational."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'Response': 'True'}
        mock_get.return_value = mock_response
        
        result = check_omdb_status()
        
        self.assertEqual(result['status'], 'operational')
        self.assertEqual(result['message'], 'API is operational')
        self.assertIn('response_time', result)
    
    @patch('cineman.api_status.requests.get')
    @patch.dict(os.environ, {'OMDB_API_KEY': 'invalid-key'})
    def test_omdb_invalid_key(self, mock_get):
        """Test OMDB API status with invalid key."""
        # Mock invalid key response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Response': 'False',
            'Error': 'Invalid API key!'
        }
        mock_get.return_value = mock_response
        
        result = check_omdb_status()
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Invalid API key')
    
    @patch.dict(os.environ, {}, clear=True)
    def test_omdb_no_key(self):
        """Test OMDB API status when key is not configured."""
        result = check_omdb_status()
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'API key not configured')
    
    @patch('cineman.api_status.check_gemini_status')
    @patch('cineman.api_status.check_tmdb_status')
    @patch('cineman.api_status.check_omdb_status')
    def test_check_all_apis(self, mock_omdb, mock_tmdb, mock_gemini):
        """Test checking all APIs at once."""
        # Mock responses
        mock_gemini.return_value = {
            'status': 'operational',
            'message': 'API is operational',
            'response_time': 100
        }
        mock_tmdb.return_value = {
            'status': 'operational',
            'message': 'API is operational',
            'response_time': 150
        }
        mock_omdb.return_value = {
            'status': 'operational',
            'message': 'API is operational',
            'response_time': 200
        }
        
        result = check_all_apis()
        
        self.assertIn('gemini', result)
        self.assertIn('tmdb', result)
        self.assertIn('omdb', result)
        self.assertEqual(result['gemini']['status'], 'operational')
        self.assertEqual(result['tmdb']['status'], 'operational')
        self.assertEqual(result['omdb']['status'], 'operational')
    
    @patch('cineman.api_status.check_gemini_status')
    @patch('cineman.api_status.check_tmdb_status')
    @patch('cineman.api_status.check_omdb_status')
    def test_check_all_apis_mixed_status(self, mock_omdb, mock_tmdb, mock_gemini):
        """Test checking all APIs with mixed statuses."""
        # Mock mixed responses
        mock_gemini.return_value = {
            'status': 'operational',
            'message': 'API is operational',
            'response_time': 100
        }
        mock_tmdb.return_value = {
            'status': 'degraded',
            'message': 'Slow response',
            'response_time': 3000
        }
        mock_omdb.return_value = {
            'status': 'error',
            'message': 'Connection failed',
            'response_time': 0
        }
        
        result = check_all_apis()
        
        self.assertEqual(result['gemini']['status'], 'operational')
        self.assertEqual(result['tmdb']['status'], 'degraded')
        self.assertEqual(result['omdb']['status'], 'error')


class TestAPIStatusEndpoint(unittest.TestCase):
    """Test cases for the API status endpoint."""
    
    def setUp(self):
        """Set up test Flask app."""
        from cineman.app import app
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
    
    @patch('cineman.routes.api.check_all_apis')
    def test_status_endpoint_success(self, mock_check):
        """Test /api/status endpoint with successful check."""
        # Mock successful status check
        mock_check.return_value = {
            'gemini': {
                'status': 'operational',
                'message': 'API is operational',
                'response_time': 100
            },
            'tmdb': {
                'status': 'operational',
                'message': 'API is operational',
                'response_time': 150
            },
            'omdb': {
                'status': 'operational',
                'message': 'API is operational',
                'response_time': 200
            }
        }
        
        response = self.client.get('/api/status')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('services', data)
        self.assertIn('timestamp', data)
        self.assertIn('gemini', data['services'])
        self.assertIn('tmdb', data['services'])
        self.assertIn('omdb', data['services'])
    
    @patch('cineman.routes.api.check_all_apis')
    def test_status_endpoint_error(self, mock_check):
        """Test /api/status endpoint when check fails."""
        # Mock error
        mock_check.side_effect = Exception('Test error')
        
        response = self.client.get('/api/status')
        
        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertEqual(data['status'], 'error')


if __name__ == '__main__':
    unittest.main()
