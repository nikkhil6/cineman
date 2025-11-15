"""
Tests for movie interaction API endpoints (like, dislike, watchlist).
"""

import sys
import os
import unittest

# Add parent directory to path so we can import cineman module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.app import app, db
from cineman.models import MovieInteraction


class TestMovieInteractions(unittest.TestCase):
    """Test cases for movie interaction API endpoints."""
    
    def setUp(self):
        """Set up test client and database before each test."""
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        self.client = app.test_client()
        
        # Create tables
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_like_movie(self):
        """Test liking a movie."""
        with self.client as client:
            # Establish session
            with client.session_transaction() as sess:
                sess['session_id'] = 'test-session-123'
            
            response = client.post('/api/interaction', json={
                'movie_title': 'Inception',
                'movie_year': '2010',
                'movie_poster_url': 'https://example.com/poster.jpg',
                'director': 'Christopher Nolan',
                'imdb_rating': '8.8',
                'action': 'like',
                'value': True
            })
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['status'], 'success')
            self.assertTrue(data['interaction']['liked'])
            self.assertFalse(data['interaction']['disliked'])
    
    def test_dislike_movie(self):
        """Test disliking a movie."""
        with self.client as client:
            with client.session_transaction() as sess:
                sess['session_id'] = 'test-session-123'
            
            response = client.post('/api/interaction', json={
                'movie_title': 'Inception',
                'action': 'dislike',
                'value': True
            })
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['status'], 'success')
            self.assertTrue(data['interaction']['disliked'])
            self.assertFalse(data['interaction']['liked'])
    
    def test_add_to_watchlist(self):
        """Test adding a movie to watchlist."""
        with self.client as client:
            with client.session_transaction() as sess:
                sess['session_id'] = 'test-session-123'
            
            response = client.post('/api/interaction', json={
                'movie_title': 'The Matrix',
                'movie_year': '1999',
                'action': 'watchlist',
                'value': True
            })
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['status'], 'success')
            self.assertTrue(data['interaction']['in_watchlist'])
    
    def test_get_watchlist(self):
        """Test getting user's watchlist."""
        with self.client as client:
            with client.session_transaction() as sess:
                sess['session_id'] = 'test-session-123'
            
            # Add movies to watchlist
            client.post('/api/interaction', json={
                'movie_title': 'Inception',
                'action': 'watchlist',
                'value': True
            })
            client.post('/api/interaction', json={
                'movie_title': 'The Matrix',
                'action': 'watchlist',
                'value': True
            })
            
            # Get watchlist
            response = client.get('/api/watchlist')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['status'], 'success')
            self.assertEqual(len(data['watchlist']), 2)
    
    def test_remove_from_watchlist(self):
        """Test removing a movie from watchlist."""
        with self.client as client:
            with client.session_transaction() as sess:
                sess['session_id'] = 'test-session-123'
            
            # Add to watchlist
            client.post('/api/interaction', json={
                'movie_title': 'Inception',
                'action': 'watchlist',
                'value': True
            })
            
            # Remove from watchlist
            response = client.post('/api/interaction', json={
                'movie_title': 'Inception',
                'action': 'watchlist',
                'value': False
            })
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['status'], 'success')
            self.assertFalse(data['interaction']['in_watchlist'])
    
    def test_like_removes_dislike(self):
        """Test that liking a movie removes a previous dislike."""
        with self.client as client:
            with client.session_transaction() as sess:
                sess['session_id'] = 'test-session-123'
            
            # First dislike the movie
            client.post('/api/interaction', json={
                'movie_title': 'Inception',
                'action': 'dislike',
                'value': True
            })
            
            # Then like it
            response = client.post('/api/interaction', json={
                'movie_title': 'Inception',
                'action': 'like',
                'value': True
            })
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['interaction']['liked'])
            self.assertFalse(data['interaction']['disliked'])
    
    def test_get_movie_interaction(self):
        """Test getting interaction status for a specific movie."""
        with self.client as client:
            with client.session_transaction() as sess:
                sess['session_id'] = 'test-session-123'
            
            # Like a movie
            client.post('/api/interaction', json={
                'movie_title': 'Inception',
                'action': 'like',
                'value': True
            })
            
            # Get interaction status
            response = client.get('/api/interaction/Inception')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['status'], 'success')
            self.assertIsNotNone(data['interaction'])
            self.assertTrue(data['interaction']['liked'])
    
    def test_invalid_action(self):
        """Test that invalid actions return an error."""
        with self.client as client:
            with client.session_transaction() as sess:
                sess['session_id'] = 'test-session-123'
            
            response = client.post('/api/interaction', json={
                'movie_title': 'Inception',
                'action': 'invalid_action',
                'value': True
            })
            
            self.assertEqual(response.status_code, 400)
            data = response.get_json()
            self.assertEqual(data['status'], 'error')
    
    def test_missing_required_fields(self):
        """Test that missing required fields return an error."""
        with self.client as client:
            with client.session_transaction() as sess:
                sess['session_id'] = 'test-session-123'
            
            response = client.post('/api/interaction', json={
                'action': 'like',
                'value': True
            })
            
            self.assertEqual(response.status_code, 400)
            data = response.get_json()
            self.assertEqual(data['status'], 'error')


if __name__ == '__main__':
    print("Running Movie Interaction API Tests...")
    print("=" * 60)
    unittest.main(verbosity=2)
