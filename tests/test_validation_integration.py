"""
Integration tests for validation logic.
Tests the validate_movie_list function with various scenarios.
"""

import pytest
from unittest.mock import patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.validation import validate_movie_list


class TestValidationIntegration:
    """Test validation logic."""
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_validate_valid_movies(self, mock_omdb, mock_tmdb):
        """Test validation with all valid movies."""
        
        # Mock responses for valid movies
        def tmdb_side_effect(title, year=None):
            if "Inception" in title:
                return {
                    "status": "success",
                    "title": "Inception",
                    "year": "2010",
                    "tmdb_id": 27205
                }
            elif "Matrix" in title:
                return {
                    "status": "success",
                    "title": "The Matrix",
                    "year": "1999",
                    "tmdb_id": 603
                }
            return {"status": "not_found"}
        
        def omdb_side_effect(title, year=None):
            if "Inception" in title:
                return {
                    "status": "success",
                    "Title": "Inception",
                    "Year": "2010",
                    "Director": "Christopher Nolan"
                }
            elif "Matrix" in title:
                return {
                    "status": "success",
                    "Title": "The Matrix",
                    "Year": "1999",
                    "Director": "Lana Wachowski, Lilly Wachowski"
                }
            return {"status": "not_found"}
        
        mock_tmdb.side_effect = tmdb_side_effect
        mock_omdb.side_effect = omdb_side_effect
        
        # Simulate structured input (list of dicts)
        movies_input = [
            {
                "title": "Inception",
                "year": "2010",
                "director": "Christopher Nolan",
                "anchor_id": "m1"
            },
            {
                "title": "The Matrix",
                "year": "1999",
                "director": "The Wachowskis",
                "anchor_id": "m2"
            }
        ]
        
        valid_movies, dropped_movies, summary = validate_movie_list(
            movies_input, 
            session_id="test_123"
        )
        
        # Verify results
        assert len(valid_movies) == 2
        assert len(dropped_movies) == 0
        movie_titles = [m['title'] for m in valid_movies]
        assert "Inception" in movie_titles
        assert "The Matrix" in movie_titles
        
        assert summary is not None
        assert summary["total_checked"] == 2
        assert summary["valid_count"] == 2
        assert summary["dropped_count"] == 0
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_validate_with_fake_movie(self, mock_omdb, mock_tmdb):
        """Test validation drops hallucinated movie."""
        
        # Mock responses
        def tmdb_side_effect(title, year=None):
            if "Inception" in title:
                return {
                    "status": "success",
                    "title": "Inception",
                    "year": "2010",
                    "tmdb_id": 27205
                }
            return {"status": "not_found"}
        
        def omdb_side_effect(title, year=None):
            if "Inception" in title:
                return {
                    "status": "success",
                    "Title": "Inception",
                    "Year": "2010",
                    "Director": "Christopher Nolan"
                }
            return {"status": "not_found"}
        
        mock_tmdb.side_effect = tmdb_side_effect
        mock_omdb.side_effect = omdb_side_effect
        
        movies_input = [
            {
                "title": "Inception",
                "year": "2010",
                "director": "Christopher Nolan",
                "anchor_id": "m1"
            },
            {
                "title": "The Totally Fake Movie 12345",
                "year": "2025",
                "director": "Nobody Real",
                "anchor_id": "m2"
            }
        ]
        
        valid_movies, dropped_movies, summary = validate_movie_list(
            movies_input,
            session_id="test_456"
        )
        
        # Verify fake movie was dropped
        assert len(valid_movies) == 1
        assert len(dropped_movies) == 1
        assert valid_movies[0]['title'] == "Inception"
        
        # Check dropped reason
        assert dropped_movies[0]['title'] == "The Totally Fake Movie 12345"
        assert "drop_reason" in dropped_movies[0]
        
        assert summary["total_checked"] == 2
        assert summary["valid_count"] == 1
        assert summary["dropped_count"] == 1
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_validate_with_typo(self, mock_omdb, mock_tmdb):
        """Test validation corrects typos in movie titles."""
        
        # Mock responses with correct spelling
        mock_tmdb.return_value = {
            "status": "success",
            "title": "The Shawshank Redemption",
            "year": "1994",
            "tmdb_id": 278
        }
        
        mock_omdb.return_value = {
            "status": "success",
            "Title": "The Shawshank Redemption",
            "Year": "1994",
            "Director": "Frank Darabont"
        }
        
        movies_input = [
            {
                "title": "The Shawshank Redemtion",  # Typo
                "year": "1994",
                "director": "Frank Darabont",
                "anchor_id": "m1"
            }
        ]
        
        valid_movies, dropped_movies, summary = validate_movie_list(
            movies_input,
            session_id="test_789"
        )
        
        # Verify title was corrected
        assert len(valid_movies) == 1
        assert valid_movies[0]['title'] == "The Shawshank Redemption"
        assert valid_movies[0]['original_title'] == "The Shawshank Redemtion"
        
        assert summary["valid_count"] == 1
        assert summary["dropped_count"] == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
