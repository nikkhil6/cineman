"""
Tests for OMDb API integration.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_omdb_response_success():
    """Mock successful OMDb API response."""
    return {
        "Title": "Interstellar",
        "Year": "2014",
        "Director": "Christopher Nolan",
        "IMDb_Rating": "8.7",
        "imdbID": "tt0816692",
        "Poster": "https://m.media-amazon.com/images/M/poster.jpg",
        "Response": "True",
    }


@pytest.fixture
def mock_omdb_response_not_found():
    """Mock OMDb API response for movie not found."""
    return {"Response": "False", "Error": "Movie not found!"}


class TestOMDbIntegration:
    """Test OMDb API integration."""

    @patch("cineman.tools.omdb.OMDB_API_KEY", "test-api-key")
    @patch("cineman.tools.omdb._make_session")
    def test_fetch_omdb_data_success(self, mock_session, mock_omdb_response_success):
        """Test successful movie data fetch from OMDb."""
        from cineman.tools.omdb import fetch_omdb_data_core

        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = mock_omdb_response_success
        mock_response.status_code = 200
        mock_get = MagicMock(return_value=mock_response)
        mock_session.return_value.get = mock_get

        # Execute
        result = fetch_omdb_data_core("Interstellar")

        # Verify
        assert result["status"] == "success"
        assert result.get("Title") == "Interstellar"
        mock_get.assert_called_once()

    @patch("cineman.tools.omdb.OMDB_API_KEY", "test-api-key")
    @patch("cineman.tools.omdb._make_session")
    def test_fetch_omdb_data_not_found(
        self, mock_session, mock_omdb_response_not_found
    ):
        """Test movie not found scenario."""
        from cineman.tools.omdb import fetch_omdb_data_core

        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = mock_omdb_response_not_found
        mock_response.status_code = 200
        mock_get = MagicMock(return_value=mock_response)
        mock_session.return_value.get = mock_get

        # Execute
        result = fetch_omdb_data_core("Nonexistent Movie 123456")

        # Verify
        assert result.get("status") == "not_found"

    @patch("cineman.tools.omdb.OMDB_API_KEY", "test-api-key")
    @patch("cineman.tools.omdb._make_session")
    def test_fetch_omdb_data_api_error(self, mock_session):
        """Test API error handling."""
        from cineman.tools.omdb import fetch_omdb_data_core
        import requests

        # Setup mock to raise exception
        mock_get = MagicMock(
            side_effect=requests.exceptions.RequestException("API connection failed")
        )
        mock_session.return_value.get = mock_get

        # Execute
        result = fetch_omdb_data_core("Test Movie")

        # Verify error handling
        assert result.get("status") == "error"
        assert "error" in result

    @patch("cineman.tools.omdb.OMDB_API_KEY", None)
    def test_fetch_omdb_data_no_api_key(self):
        """Test behavior when API key is not configured."""
        from cineman.tools.omdb import fetch_omdb_data_core

        # Execute
        result = fetch_omdb_data_core("Test Movie")

        # Verify
        assert result.get("status") == "error"
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
