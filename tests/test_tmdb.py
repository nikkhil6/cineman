"""
Tests for TMDB API integration.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_tmdb_response_success():
    """Mock successful TMDB API response."""
    return {
        "results": [
            {
                "id": 157336,
                "title": "Interstellar",
                "release_date": "2014-11-05",
                "poster_path": "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
                "vote_average": 8.4,
                "vote_count": 35000,
            }
        ]
    }


@pytest.fixture
def mock_tmdb_response_not_found():
    """Mock TMDB API response for movie not found."""
    return {"results": []}


class TestTMDBIntegration:
    """Test TMDB API integration."""

    @patch("cineman.tools.tmdb.TMDB_API_KEY", "test-api-key")
    @patch("cineman.tools.tmdb.requests.get")
    def test_get_movie_poster_success(self, mock_get, mock_tmdb_response_success):
        """Test successful movie poster fetch from TMDB."""
        from cineman.tools.tmdb import get_movie_poster_core

        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = mock_tmdb_response_success
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Execute
        result = get_movie_poster_core("Interstellar")

        # Verify
        assert result["status"] == "success"
        assert result["title"] == "Interstellar"
        assert result["year"] == "2014"
        assert "image.tmdb.org" in result["poster_url"]
        assert result["tmdb_id"] == 157336
        assert result["vote_average"] == 8.4
        mock_get.assert_called_once()

    @patch("cineman.tools.tmdb.TMDB_API_KEY", "test-api-key")
    @patch("cineman.tools.tmdb.requests.get")
    def test_get_movie_poster_not_found(self, mock_get, mock_tmdb_response_not_found):
        """Test movie not found scenario."""
        from cineman.tools.tmdb import get_movie_poster_core

        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = mock_tmdb_response_not_found
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Execute
        result = get_movie_poster_core("Nonexistent Movie 123456")

        # Verify
        assert result["status"] == "not_found"
        assert result["poster_url"] == ""

    @patch("cineman.tools.tmdb.requests.get")
    def test_get_movie_poster_api_error(self, mock_get):
        """Test API error handling."""
        from cineman.tools.tmdb import get_movie_poster_core

        # Setup mock to raise exception
        mock_get.side_effect = Exception("API connection failed")

        # Execute
        result = get_movie_poster_core("Test Movie")

        # Verify error handling
        assert result["status"] == "error"
        assert "error" in result

    @patch("cineman.tools.tmdb.TMDB_API_KEY", None)
    def test_get_movie_poster_no_api_key(self):
        """Test behavior when API key is not configured."""
        from cineman.tools.tmdb import get_movie_poster_core

        # Execute
        result = get_movie_poster_core("Test Movie")

        # Verify
        assert result["status"] == "error"
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
