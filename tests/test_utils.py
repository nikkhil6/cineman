"""
Tests for utility functions.
"""

import pytest
from cineman.utils import (
    extract_and_validate_manifest,
    format_movie_for_display,
    merge_movie_data,
)
from cineman.schemas import MovieManifest


class TestExtractAndValidateManifest:
    """Test manifest extraction and validation."""

    def test_extract_valid_manifest(self):
        """Test extracting valid manifest from LLM response."""
        llm_response = """
Here are some great movie recommendations for you:

{
  "movies": [
    {
      "title": "Inception",
      "year": "2010",
      "imdb_rating": "8.8",
      "anchor_id": "m1"
    },
    {
      "title": "The Matrix",
      "year": "1999",
      "imdb_rating": "8.7",
      "anchor_id": "m2"
    },
    {
      "title": "Primer",
      "year": "2004",
      "imdb_rating": "6.9",
      "anchor_id": "m3"
    }
  ]
}
"""
        manifest = extract_and_validate_manifest(llm_response)

        assert manifest is not None
        assert isinstance(manifest, MovieManifest)
        assert len(manifest.movies) == 3
        assert manifest.movies[0].title == "Inception"
        assert manifest.movies[1].title == "The Matrix"

    def test_extract_manifest_with_double_newline(self):
        """Test extracting manifest with double newline separator."""
        llm_response = """Some text before.

{
  "movies": [
    {"title": "Test Movie", "anchor_id": "m1"}
  ]
}"""
        manifest = extract_and_validate_manifest(llm_response)

        assert manifest is not None
        assert len(manifest.movies) == 1
        assert manifest.movies[0].title == "Test Movie"

    def test_extract_invalid_manifest(self):
        """Test extracting invalid manifest returns None."""
        llm_response = """
{
  "movies": []
}
"""
        manifest = extract_and_validate_manifest(llm_response)

        assert manifest is None

    def test_extract_malformed_json(self):
        """Test extracting malformed JSON returns None."""
        llm_response = """
{
  "movies": [
    {"title": "Test"
  ]
"""
        manifest = extract_and_validate_manifest(llm_response)

        assert manifest is None

    def test_extract_no_json(self):
        """Test extracting when no JSON present returns None."""
        llm_response = "Just some text without any JSON"

        manifest = extract_and_validate_manifest(llm_response)

        assert manifest is None

    def test_extract_empty_string(self):
        """Test extracting from empty string returns None."""
        manifest = extract_and_validate_manifest("")

        assert manifest is None

    def test_extract_none(self):
        """Test extracting from None returns None."""
        manifest = extract_and_validate_manifest(None)

        assert manifest is None


class TestFormatMovieForDisplay:
    """Test movie data formatting for display."""

    def test_format_complete_movie_data(self):
        """Test formatting complete movie data."""
        movie_data = {
            "title": "Inception",
            "year": "2010",
            "poster_url": "https://example.com/poster.jpg",
            "director": "Christopher Nolan",
            "rating": "8.8",
            "plot": "A thief who steals corporate secrets...",
        }

        formatted = format_movie_for_display(movie_data)

        assert formatted["title"] == "Inception"
        assert formatted["year"] == "2010"
        assert formatted["poster"] == "https://example.com/poster.jpg"
        assert formatted["director"] == "Christopher Nolan"
        assert formatted["rating"] == "8.8"
        assert formatted["plot"] == "A thief who steals corporate secrets..."

    def test_format_movie_with_alternate_keys(self):
        """Test formatting movie data with alternate key names."""
        movie_data = {
            "Title": "Interstellar",
            "Year": "2014",
            "Poster_URL": "https://example.com/poster.jpg",
            "Director": "Christopher Nolan",
            "IMDb_Rating": "8.7",
            "Plot": "A team of explorers...",
        }

        formatted = format_movie_for_display(movie_data)

        assert formatted["title"] == "Interstellar"
        assert formatted["year"] == "2014"
        assert formatted["poster"] == "https://example.com/poster.jpg"
        assert formatted["director"] == "Christopher Nolan"
        assert formatted["rating"] == "8.7"
        assert formatted["plot"] == "A team of explorers..."

    def test_format_movie_with_missing_fields(self):
        """Test formatting movie data with missing fields."""
        movie_data = {"title": "Test Movie"}

        formatted = format_movie_for_display(movie_data)

        assert formatted["title"] == "Test Movie"
        assert formatted["year"] is None
        assert formatted["poster"] is None
        assert formatted["director"] is None
        assert formatted["rating"] is None
        assert formatted["plot"] is None

    def test_format_movie_with_empty_data(self):
        """Test formatting with empty data."""
        movie_data = {}

        formatted = format_movie_for_display(movie_data)

        assert formatted["title"] == "Unknown"
        assert formatted["year"] is None


class TestMergeMovieData:
    """Test merging movie data from multiple sources."""

    def test_merge_complete_data(self):
        """Test merging complete data from both sources."""
        tmdb_data = {
            "title": "Inception",
            "year": "2010",
            "poster_url": "https://tmdb.org/poster.jpg",
            "vote_average": 8.2,
            "tmdb_id": 27205,
        }

        omdb_data = {
            "Title": "Inception",
            "Year": "2010",
            "Poster_URL": "https://omdb.com/poster.jpg",
            "IMDb_Rating": "8.8",
            "Director": "Christopher Nolan",
            "imdbID": "tt1375666",
        }

        merged = merge_movie_data(tmdb_data, omdb_data)

        assert merged["title"] == "Inception"
        assert merged["year"] == "2010"
        assert merged["poster_url"] == "https://tmdb.org/poster.jpg"  # TMDB preferred
        assert merged["imdb_rating"] == "8.8"  # OMDb preferred
        assert merged["director"] == "Christopher Nolan"
        assert merged["tmdb_id"] == 27205
        assert merged["imdb_id"] == "tt1375666"

    def test_merge_with_tmdb_only(self):
        """Test merging when only TMDB data is available."""
        tmdb_data = {
            "title": "Inception",
            "year": "2010",
            "poster_url": "https://tmdb.org/poster.jpg",
            "vote_average": 8.2,
            "tmdb_id": 27205,
        }

        omdb_data = {}

        merged = merge_movie_data(tmdb_data, omdb_data)

        assert merged["title"] == "Inception"
        assert merged["year"] == "2010"
        assert merged["poster_url"] == "https://tmdb.org/poster.jpg"
        assert merged["tmdb_rating"] == 8.2
        assert merged["tmdb_id"] == 27205

    def test_merge_with_omdb_only(self):
        """Test merging when only OMDb data is available."""
        tmdb_data = {}

        omdb_data = {
            "Title": "Inception",
            "Year": "2010",
            "Poster_URL": "https://omdb.com/poster.jpg",
            "IMDb_Rating": "8.8",
            "Director": "Christopher Nolan",
            "imdbID": "tt1375666",
        }

        merged = merge_movie_data(tmdb_data, omdb_data)

        assert merged["title"] == "Inception"
        assert merged["year"] == "2010"
        assert merged["poster_url"] == "https://omdb.com/poster.jpg"
        assert merged["imdb_rating"] == "8.8"
        assert merged["director"] == "Christopher Nolan"
        assert merged["imdb_id"] == "tt1375666"

    def test_merge_empty_data(self):
        """Test merging with empty data from both sources."""
        tmdb_data = {}
        omdb_data = {}

        merged = merge_movie_data(tmdb_data, omdb_data)

        assert merged["title"] == ""
        assert merged["year"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
