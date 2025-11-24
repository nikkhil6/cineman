"""
Tests for utility functions in cineman.utils module.
"""

import sys
import os
import unittest

# Add parent directory to path so we can import cineman module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cineman.utils import (
    extract_and_validate_manifest,
    format_movie_for_display,
    merge_movie_data
)


class TestExtractAndValidateManifest(unittest.TestCase):
    """Test manifest extraction from LLM responses."""
    
    def test_extract_valid_manifest(self):
        """Test extraction of valid JSON manifest from response."""
        response = """Here are some movie recommendations for you!

I suggest watching these classics:

{"movies": [{"title": "Inception", "year": "2010", "director": "Christopher Nolan"}]}"""
        result = extract_and_validate_manifest(response)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.movies), 1)
        self.assertEqual(result.movies[0].title, "Inception")
    
    def test_extract_manifest_no_json(self):
        """Test extraction when no JSON is present."""
        response = "Just talking about movies, no recommendations."
        result = extract_and_validate_manifest(response)
        self.assertIsNone(result)
    
    def test_extract_manifest_empty_string(self):
        """Test extraction with empty string."""
        result = extract_and_validate_manifest("")
        self.assertIsNone(result)
    
    def test_extract_manifest_none(self):
        """Test extraction with None input."""
        result = extract_and_validate_manifest(None)
        self.assertIsNone(result)
    
    def test_extract_manifest_invalid_json(self):
        """Test extraction with invalid JSON."""
        response = """Here are movies:
        
{not valid json}"""
        result = extract_and_validate_manifest(response)
        self.assertIsNone(result)


class TestFormatMovieForDisplay(unittest.TestCase):
    """Test movie formatting for frontend display."""
    
    def test_format_tmdb_style_data(self):
        """Test formatting TMDB-style data."""
        movie_data = {
            "title": "The Matrix",
            "year": "1999",
            "poster_url": "https://example.com/matrix.jpg",
            "director": None,
            "rating": "8.7"
        }
        result = format_movie_for_display(movie_data)
        self.assertEqual(result["title"], "The Matrix")
        self.assertEqual(result["year"], "1999")
        self.assertEqual(result["poster"], "https://example.com/matrix.jpg")
        self.assertEqual(result["rating"], "8.7")
    
    def test_format_omdb_style_data(self):
        """Test formatting OMDb-style data."""
        movie_data = {
            "Title": "Inception",
            "Year": "2010",
            "Poster_URL": "https://example.com/inception.jpg",
            "Director": "Christopher Nolan",
            "IMDb_Rating": "8.8"
        }
        result = format_movie_for_display(movie_data)
        self.assertEqual(result["title"], "Inception")
        self.assertEqual(result["year"], "2010")
        self.assertEqual(result["poster"], "https://example.com/inception.jpg")
        self.assertEqual(result["director"], "Christopher Nolan")
        self.assertEqual(result["rating"], "8.8")
    
    def test_format_empty_data(self):
        """Test formatting empty data."""
        movie_data = {}
        result = format_movie_for_display(movie_data)
        self.assertEqual(result["title"], "Unknown")
        self.assertIsNone(result["year"])
    
    def test_format_mixed_case_keys(self):
        """Test formatting with mixed key styles."""
        movie_data = {
            "title": "Test Movie",
            "Year": "2020",
            "imdb_rating": "7.5"
        }
        result = format_movie_for_display(movie_data)
        self.assertEqual(result["title"], "Test Movie")
        self.assertEqual(result["year"], "2020")
        self.assertEqual(result["rating"], "7.5")


class TestMergeMovieData(unittest.TestCase):
    """Test merging data from TMDB and OMDb sources."""
    
    def test_merge_both_sources(self):
        """Test merging complete data from both sources."""
        tmdb_data = {
            "title": "Inception",
            "year": "2010",
            "poster_url": "https://tmdb.com/inception.jpg",
            "tmdb_id": 12345,
            "vote_average": 8.3
        }
        omdb_data = {
            "Title": "Inception",
            "Year": "2010",
            "Poster_URL": "https://omdb.com/inception.jpg",
            "Director": "Christopher Nolan",
            "IMDb_Rating": "8.8",
            "imdbID": "tt1375666"
        }
        result = merge_movie_data(tmdb_data, omdb_data)
        
        # Should prefer TMDB for title
        self.assertEqual(result["title"], "Inception")
        # Should prefer TMDB for poster
        self.assertEqual(result["poster_url"], "https://tmdb.com/inception.jpg")
        # Should use OMDb for director
        self.assertEqual(result["director"], "Christopher Nolan")
        # Should use IMDb rating from OMDb
        self.assertEqual(result["imdb_rating"], "8.8")
        # Should include IDs from both
        self.assertEqual(result["tmdb_id"], 12345)
        self.assertEqual(result["imdb_id"], "tt1375666")
    
    def test_merge_tmdb_only(self):
        """Test merging when only TMDB data is available."""
        tmdb_data = {
            "title": "Movie",
            "year": "2020",
            "poster_url": "https://example.com/poster.jpg",
            "tmdb_id": 99999,
            "vote_average": 7.0
        }
        omdb_data = {}
        result = merge_movie_data(tmdb_data, omdb_data)
        
        self.assertEqual(result["title"], "Movie")
        self.assertEqual(result["year"], "2020")
        self.assertEqual(result["tmdb_rating"], 7.0)
        self.assertNotIn("director", result)
    
    def test_merge_omdb_only(self):
        """Test merging when only OMDb data is available."""
        tmdb_data = {}
        omdb_data = {
            "Title": "Movie",
            "Year": "2020",
            "Poster_URL": "https://example.com/poster.jpg",
            "Director": "John Doe",
            "IMDb_Rating": "6.5",
            "imdbID": "tt9999999"
        }
        result = merge_movie_data(tmdb_data, omdb_data)
        
        self.assertEqual(result["title"], "Movie")
        self.assertEqual(result["year"], "2020")
        self.assertEqual(result["director"], "John Doe")
        self.assertEqual(result["imdb_id"], "tt9999999")
    
    def test_merge_empty_sources(self):
        """Test merging empty data from both sources."""
        result = merge_movie_data({}, {})
        self.assertEqual(result["title"], "")
        self.assertIsNone(result["year"])


if __name__ == '__main__':
    unittest.main()
