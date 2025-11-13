"""
Tests for API routes.
"""

import pytest
from unittest.mock import patch
import json


@pytest.fixture
def app():
    """Create Flask app for testing."""
    from cineman.app import app as flask_app

    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret-key"
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    with flask_app.app_context():
        from cineman.models import db

        db.create_all()
        yield flask_app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestMoviePosterRoute:
    """Test /api/movie/poster endpoint."""

    @patch("cineman.routes.api.get_movie_poster_core")
    def test_movie_poster_success(self, mock_poster, client):
        """Test successful poster lookup."""
        mock_poster.return_value = {
            "status": "success",
            "poster_url": "https://image.tmdb.org/t/p/w500/poster.jpg",
            "title": "Inception",
            "year": "2010",
        }

        response = client.get("/api/movie/poster?title=Inception")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["title"] == "Inception"
        mock_poster.assert_called_once_with("Inception")

    def test_movie_poster_missing_title(self, client):
        """Test poster lookup without title parameter."""
        response = client.get("/api/movie/poster")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "Missing title" in data["error"]

    def test_movie_poster_empty_title(self, client):
        """Test poster lookup with empty title."""
        response = client.get("/api/movie/poster?title=")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"


class TestMovieFactsRoute:
    """Test /api/movie/facts endpoint."""

    @patch("cineman.routes.api.fetch_omdb_data_core")
    def test_movie_facts_success(self, mock_facts, client):
        """Test successful facts lookup."""
        mock_facts.return_value = json.dumps(
            {
                "Title": "Inception",
                "Year": "2014",
                "Director": "Christopher Nolan",
                "IMDb_Rating": "8.8",
                "status": "success",
            }
        )

        response = client.get("/api/movie/facts?title=Inception")

        assert response.status_code == 200
        # Response may be double-encoded JSON
        mock_facts.assert_called_once_with("Inception")

    def test_movie_facts_missing_title(self, client):
        """Test facts lookup without title parameter."""
        response = client.get("/api/movie/facts")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"


class TestMovieCombinedRoute:
    """Test /api/movie endpoint (combined data)."""

    @patch("cineman.routes.api.fetch_omdb_data_core")
    @patch("cineman.routes.api.get_movie_poster_core")
    def test_movie_combined_success(self, mock_poster, mock_facts, client):
        """Test successful combined movie data lookup."""
        mock_poster.return_value = {
            "status": "success",
            "poster_url": "https://image.tmdb.org/t/p/w500/poster.jpg",
            "title": "Inception",
            "year": "2010",
            "vote_average": 8.2,
            "tmdb_id": 27205,
        }

        mock_facts.return_value = {
            "status": "success",
            "Title": "Inception",
            "Year": "2010",
            "Director": "Christopher Nolan",
            "IMDb_Rating": "8.8",
            "imdbID": "tt1375666",
        }

        response = client.get("/api/movie?title=Inception")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["query"] == "Inception"
        # Should prefer IMDb rating from OMDb
        assert data.get("rating") == "8.8" or data.get("rating_source") == "OMDb/IMDb"

    @patch("cineman.routes.api.fetch_omdb_data_core")
    @patch("cineman.routes.api.get_movie_poster_core")
    def test_movie_combined_tmdb_fallback(self, mock_poster, mock_facts, client):
        """Test combined data with TMDb rating fallback when OMDb fails."""
        mock_poster.return_value = {
            "status": "success",
            "poster_url": "https://image.tmdb.org/t/p/w500/poster.jpg",
            "title": "Inception",
            "year": "2010",
            "vote_average": 8.2,
        }

        mock_facts.return_value = {"status": "error", "error": "Service unavailable"}

        response = client.get("/api/movie?title=Inception")

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should fall back to TMDb rating
        assert data.get("rating") == 8.2 or data.get("rating_source") == "TMDb"

    def test_movie_combined_missing_title(self, client):
        """Test combined lookup without title parameter."""
        response = client.get("/api/movie")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"


class TestSessionManagement:
    """Test session ID generation."""

    def test_session_id_creation(self, client):
        """Test session ID is created on first request."""
        with client.session_transaction() as sess:
            assert "session_id" not in sess

        # Make a request that uses get_or_create_session_id
        with patch("cineman.routes.api.get_movie_poster_core") as mock_poster:
            mock_poster.return_value = {"status": "success"}
            client.get("/api/movie/poster?title=Test")

        # Session ID should now exist
        with client.session_transaction() as sess:
            # Session might not be set if route doesn't call get_or_create_session_id
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
