"""
Tests for API schema consistency.

This module tests that the /api/movie endpoint returns a consistent schema
with top-level fields for easier frontend consumption.
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import cineman
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.app import app, db


class TestAPISchema(unittest.TestCase):
    """Test cases for API schema consistency."""
    
    def setUp(self):
        """Set up test client and database."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    @patch('cineman.routes.api.get_movie_poster_core')
    @patch('cineman.routes.api.fetch_omdb_data_core')
    def test_movie_api_returns_consistent_schema(self, mock_omdb, mock_tmdb):
        """Test that /api/movie returns consistent top-level schema."""
        # Mock TMDB response
        mock_tmdb.return_value = {
            'status': 'success',
            'poster_url': 'https://image.tmdb.org/t/p/w500/test.jpg',
            'title': 'Inception',
            'year': '2010',
            'vote_average': 8.3,
            'vote_count': 30000
        }
        
        # Mock OMDB response with ratings array
        mock_omdb.return_value = {
            'status': 'success',
            'Title': 'Inception',
            'Year': '2010',
            'Director': 'Christopher Nolan',
            'IMDb_Rating': '8.8',
            'Poster_URL': 'https://example.com/poster.jpg',
            'raw': {
                'Ratings': [
                    {'Source': 'Internet Movie Database', 'Value': '8.8/10'},
                    {'Source': 'Rotten Tomatoes', 'Value': '87%'},
                ]
            }
        }
        
        # Make request
        response = self.client.get('/api/movie?title=Inception')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        
        # Verify top-level schema fields exist
        self.assertIn('poster', data)
        self.assertIn('imdb_rating', data)
        self.assertIn('rt_tomatometer', data)
        self.assertIn('rt_audience', data)
        self.assertIn('director', data)
        
        # Verify values are extracted correctly
        self.assertEqual(data['poster'], 'https://image.tmdb.org/t/p/w500/test.jpg')
        self.assertEqual(data['imdb_rating'], '8.8')
        self.assertEqual(data['rt_tomatometer'], '87%')
        self.assertEqual(data['director'], 'Christopher Nolan')
        
        # Verify nested objects still exist for backward compatibility
        self.assertIn('tmdb', data)
        self.assertIn('omdb', data)
    
    @patch('cineman.routes.api.get_movie_poster_core')
    @patch('cineman.routes.api.fetch_omdb_data_core')
    def test_movie_api_handles_missing_omdb_data(self, mock_omdb, mock_tmdb):
        """Test that API handles missing OMDb data gracefully."""
        # Mock TMDB response
        mock_tmdb.return_value = {
            'status': 'success',
            'poster_url': 'https://image.tmdb.org/t/p/w500/test.jpg',
            'title': 'Test Movie',
            'year': '2023',
            'vote_average': 7.5,
            'vote_count': 1000
        }
        
        # Mock OMDB error response
        mock_omdb.return_value = {
            'status': 'error',
            'error': 'Movie not found'
        }
        
        # Make request
        response = self.client.get('/api/movie?title=TestMovie')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        
        # Verify top-level fields exist but may be None
        self.assertIn('poster', data)
        self.assertIn('imdb_rating', data)
        self.assertIn('rt_tomatometer', data)
        self.assertIn('rt_audience', data)
        self.assertIn('director', data)
        
        # Verify poster comes from TMDB
        self.assertEqual(data['poster'], 'https://image.tmdb.org/t/p/w500/test.jpg')
        
        # Verify OMDb-specific fields are None
        self.assertIsNone(data['imdb_rating'])
        self.assertIsNone(data['rt_tomatometer'])
        self.assertIsNone(data['director'])
    
    @patch('cineman.routes.api.get_movie_poster_core')
    @patch('cineman.routes.api.fetch_omdb_data_core')
    def test_movie_api_prefers_omdb_poster_as_fallback(self, mock_omdb, mock_tmdb):
        """Test that API uses OMDb poster as fallback if TMDB fails."""
        # Mock TMDB response without poster
        mock_tmdb.return_value = {
            'status': 'success',
            'poster_url': None,
            'title': 'Test Movie',
            'year': '2023',
            'vote_average': None,
            'vote_count': 0
        }
        
        # Mock OMDB response with poster
        mock_omdb.return_value = {
            'status': 'success',
            'Title': 'Test Movie',
            'Year': '2023',
            'Director': 'Test Director',
            'IMDb_Rating': '7.0',
            'Poster_URL': 'https://example.com/omdb-poster.jpg',
            'raw': {
                'Ratings': []
            }
        }
        
        # Make request
        response = self.client.get('/api/movie?title=TestMovie')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        
        # Verify poster comes from OMDb as fallback
        self.assertEqual(data['poster'], 'https://example.com/omdb-poster.jpg')


if __name__ == '__main__':
    unittest.main()
