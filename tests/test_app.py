"""
Tests for the Flask application core functionality.
Tests Flask app startup, routes, and error handling.
"""

import sys
import os
import unittest

# Add parent directory to path so we can import cineman module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.app import app, db


class TestFlaskAppStartup(unittest.TestCase):
    """Test Flask application startup and configuration."""
    
    def setUp(self):
        """Set up test client before each test."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_app_exists(self):
        """Test that the Flask app object exists."""
        self.assertIsNotNone(app)
    
    def test_app_is_flask_instance(self):
        """Test that app is a Flask instance."""
        from flask import Flask
        self.assertIsInstance(app, Flask)
    
    def test_app_name(self):
        """Test that app has correct name."""
        self.assertEqual(app.name, 'cineman.app')


class TestHealthEndpoint(unittest.TestCase):
    """Test the health check endpoint."""
    
    def setUp(self):
        """Set up test client before each test."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_health_endpoint_exists(self):
        """Test that health endpoint exists and returns 200."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
    
    def test_health_endpoint_returns_json(self):
        """Test that health endpoint returns JSON."""
        response = self.client.get('/health')
        self.assertEqual(response.content_type, 'application/json')
    
    def test_health_endpoint_status_healthy(self):
        """Test that health endpoint reports healthy status."""
        response = self.client.get('/health')
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'cineman')


class TestIndexRoute(unittest.TestCase):
    """Test the main index route."""
    
    def setUp(self):
        """Set up test client before each test."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_index_returns_200(self):
        """Test that index route returns 200."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_index_returns_html(self):
        """Test that index route returns HTML content."""
        response = self.client.get('/')
        self.assertTrue(response.content_type.startswith('text/html'))


class TestChatEndpoint(unittest.TestCase):
    """Test the chat endpoint validation."""
    
    def setUp(self):
        """Set up test client before each test."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_chat_requires_post(self):
        """Test that chat endpoint requires POST method."""
        response = self.client.get('/chat')
        self.assertEqual(response.status_code, 405)
    
    def test_chat_requires_message(self):
        """Test that chat endpoint requires a message or handles missing AI gracefully."""
        response = self.client.post('/chat', json={})
        # May return 400 (missing message) or 503 (AI not initialized)
        self.assertIn(response.status_code, [400, 503])
        data = response.get_json()
        self.assertIn('response', data)
    
    def test_chat_empty_message(self):
        """Test that chat endpoint rejects empty message or handles missing AI."""
        response = self.client.post('/chat', json={'message': ''})
        # May return 400 (empty message) or 503 (AI not initialized)
        self.assertIn(response.status_code, [400, 503])


class TestSessionClearEndpoint(unittest.TestCase):
    """Test the session clear endpoint."""
    
    def setUp(self):
        """Set up test client before each test."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_session_clear_returns_success(self):
        """Test that session clear endpoint returns success."""
        response = self.client.post('/session/clear')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')


class TestAPIRoutes(unittest.TestCase):
    """Test API routes exist and respond correctly."""
    
    def setUp(self):
        """Set up test client before each test."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_rate_limit_endpoint_exists(self):
        """Test that rate limit status endpoint exists."""
        response = self.client.get('/api/rate-limit')
        self.assertEqual(response.status_code, 200)
    
    def test_metrics_endpoint_exists(self):
        """Test that metrics endpoint exists."""
        response = self.client.get('/api/metrics')
        self.assertEqual(response.status_code, 200)
    
    def test_api_status_endpoint_exists(self):
        """Test that API status endpoint exists."""
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
    
    def test_watchlist_endpoint_exists(self):
        """Test that watchlist endpoint exists."""
        with self.client as client:
            with client.session_transaction() as sess:
                sess['session_id'] = 'test-session-123'
            response = client.get('/api/watchlist')
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
