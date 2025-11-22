"""
Integration tests for validation in the app workflow.
Tests the extract_and_validate_movies function with various scenarios.
"""

import pytest
import json
from unittest.mock import patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.app import extract_and_validate_movies


class TestValidationIntegration:
    """Test validation integration in the app."""
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_extract_and_validate_valid_movies(self, mock_omdb, mock_tmdb):
        """Test extraction and validation with all valid movies."""
        
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
        
        # Simulate LLM response with movie manifest
        llm_response = """Here are my recommendations for you:

{
  "movies": [
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
}"""
        
        validated_response, movie_titles, summary = extract_and_validate_movies(
            llm_response, 
            session_id="test_123"
        )
        
        # Verify results
        assert movie_titles == ["Inception", "The Matrix"]
        assert summary is not None
        assert summary["total_checked"] == 2
        assert summary["valid_count"] == 2
        assert summary["dropped_count"] == 0
        
        # Verify the response contains the movies
        assert "Inception" in validated_response
        assert "The Matrix" in validated_response
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_extract_and_validate_with_fake_movie(self, mock_omdb, mock_tmdb):
        """Test validation drops hallucinated movie."""
        
        # Mock responses - Inception is real, Fake Movie is not
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
        
        # LLM response with one real and one fake movie
        llm_response = """Here are my recommendations:

{
  "movies": [
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
}"""
        
        validated_response, movie_titles, summary = extract_and_validate_movies(
            llm_response,
            session_id="test_456"
        )
        
        # Verify fake movie was dropped
        assert movie_titles == ["Inception"]
        assert summary["total_checked"] == 2
        assert summary["valid_count"] == 1
        assert summary["dropped_count"] == 1
        
        # Verify validation note is present
        assert "filtered out" in validated_response or "Note" in validated_response
        assert "Totally Fake Movie" in validated_response
    
    @patch('cineman.validation.get_movie_poster_core')
    @patch('cineman.validation.fetch_omdb_data_core')
    def test_extract_and_validate_with_typo(self, mock_omdb, mock_tmdb):
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
        
        # LLM response with typo in title
        llm_response = """Here's a great movie:

{
  "movies": [
    {
      "title": "The Shawshank Redemtion",
      "year": "1994",
      "director": "Frank Darabont",
      "anchor_id": "m1"
    }
  ]
}"""
        
        validated_response, movie_titles, summary = extract_and_validate_movies(
            llm_response,
            session_id="test_789"
        )
        
        # Verify title was corrected
        assert movie_titles == ["The Shawshank Redemption"]
        assert summary["valid_count"] == 1
        assert summary["dropped_count"] == 0
        
        # Verify correction note is present
        assert "corrected" in validated_response.lower() or "note" in validated_response.lower()
    
    def test_extract_conversational_response(self):
        """Test that conversational responses (no movies) pass through unchanged."""
        
        # Pure conversational response with no JSON
        llm_response = "I'd be happy to help you find movies! What genres do you enjoy?"
        
        validated_response, movie_titles, summary = extract_and_validate_movies(
            llm_response,
            session_id="test_conv"
        )
        
        # Should pass through unchanged
        assert validated_response == llm_response
        assert movie_titles == []
        assert summary is None
    
    def test_extract_malformed_json(self):
        """Test handling of malformed JSON in response."""
        
        # Response with malformed JSON
        llm_response = """Here are some movies:

{
  "movies": [
    {"title": "Inception"
  ]
}"""
        
        # Should handle gracefully and return original response
        validated_response, movie_titles, summary = extract_and_validate_movies(
            llm_response,
            session_id="test_malformed"
        )
        
        # Should fall back to original response
        assert validated_response == llm_response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
